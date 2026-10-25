"""
Conexiones a bases de datos con una misma interfaz (polimorfismo).

``ConexionBD`` define las operaciones que usa el resto de la app
(consultar, ejecutar, insertar, transacciones). Sus dos subclases las
implementan para cada motor:

- ``ConexionSQLite``: archivo local (teléfono o servidor de demostración).
- ``ConexionMySQL``: servidor MySQL/MariaDB, el que se ve en phpMyAdmin.

Todas las consultas se escriben con ``?`` como marcador de parámetros; la
conexión MySQL lo traduce a ``%s``. Nunca se arma SQL pegando textos del
usuario: los valores siempre viajan como parámetros (evita inyección SQL).
"""

from __future__ import annotations

import sqlite3
import threading
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal


class ErrorConexion(Exception):
    """No se pudo conectar o se perdió la conexión con la base de datos."""


class ConexionBD(ABC):
    """Interfaz común para cualquier base de datos."""

    motor = ""

    def __init__(self) -> None:
        # Un candado evita que dos hilos usen la conexión al mismo tiempo.
        self._candado = threading.RLock()
        self._profundidad = 0   # permite transacciones anidadas

    # --- Lo que cada motor debe implementar --------------------------------
    @abstractmethod
    def _ejecutar(self, sql: str, parametros: tuple, traer_filas: bool) -> tuple[list[dict], int, int]:
        """Ejecuta SQL y devuelve (filas, id insertado, filas afectadas)."""

    @abstractmethod
    def _iniciar(self) -> None: ...

    @abstractmethod
    def _confirmar(self) -> None: ...

    @abstractmethod
    def _deshacer(self) -> None: ...

    def cerrar(self) -> None:
        """Cierra la conexión (opcional según el motor)."""

    # --- Operaciones comunes ------------------------------------------------
    def consultar(self, sql: str, parametros=()) -> list[dict]:
        return self._ejecutar(sql, tuple(parametros), True)[0]

    def consultar_uno(self, sql: str, parametros=()) -> dict | None:
        filas = self.consultar(sql, parametros)
        return filas[0] if filas else None

    def valor(self, sql: str, parametros=(), defecto=None):
        """Primer valor de la primera fila (útil para COUNT, MAX, etc.)."""
        fila = self.consultar_uno(sql, parametros)
        if not fila:
            return defecto
        valor = next(iter(fila.values()))
        return defecto if valor is None else valor

    def ejecutar(self, sql: str, parametros=()) -> int:
        """Ejecuta INSERT/UPDATE/DELETE y devuelve el id insertado (si aplica)."""
        return self._ejecutar(sql, tuple(parametros), False)[1]

    def insertar(self, tabla: str, fila: dict, reemplazar: bool = False) -> int:
        """Inserta un diccionario como fila. ``reemplazar`` usa REPLACE INTO."""
        columnas = list(fila)
        verbo = "REPLACE" if reemplazar else "INSERT"
        marcadores = ", ".join("?" * len(columnas))
        sql = f"{verbo} INTO {tabla} ({', '.join(columnas)}) VALUES ({marcadores})"
        return self.ejecutar(sql, [fila[c] for c in columnas])

    def insertar_varios(self, tabla: str, filas: list[dict], reemplazar: bool = False) -> None:
        if not filas:
            return
        with self.transaccion():
            for fila in filas:
                self.insertar(tabla, fila, reemplazar)

    def insertar_tablas(self, datos: dict[str, list[dict]]) -> None:
        """Carga varias tablas de una vez (se usa para los datos iniciales)."""
        with self.transaccion():
            for tabla, filas in datos.items():
                self.insertar_varios(tabla, filas)

    @contextmanager
    def transaccion(self):
        """
        Agrupa varias operaciones: o se guardan todas, o ninguna.

            with conexion.transaccion():
                conexion.ejecutar(...)
                conexion.ejecutar(...)
        """
        with self._candado:
            if self._profundidad == 0:
                self._iniciar()
            self._profundidad += 1
            try:
                yield self
            except BaseException:
                self._profundidad -= 1
                if self._profundidad == 0:
                    self._deshacer()
                raise
            self._profundidad -= 1
            if self._profundidad == 0:
                self._confirmar()


class ConexionSQLite(ConexionBD):
    """Base de datos en un archivo. Viene incluida en Python y en Android."""

    motor = "sqlite"

    def __init__(self, ruta, claves_foraneas: bool = False):
        super().__init__()
        self.ruta = str(ruta)
        # check_same_thread=False: la usamos desde el hilo de la interfaz y
        # desde el hilo de sincronización (el candado evita choques).
        self._con = sqlite3.connect(self.ruta, check_same_thread=False, isolation_level=None, timeout=15)
        self._con.row_factory = sqlite3.Row
        self._con.execute(f"PRAGMA foreign_keys = {'ON' if claves_foraneas else 'OFF'}")

    def _ejecutar(self, sql, parametros, traer_filas):
        with self._candado:
            try:
                cursor = self._con.execute(sql, parametros)
                filas = [dict(f) for f in cursor.fetchall()] if traer_filas else []
                return filas, cursor.lastrowid, cursor.rowcount
            except sqlite3.OperationalError as error:
                if "locked" in str(error):
                    raise ErrorConexion("La base de datos está ocupada, intenta de nuevo.") from error
                raise

    def _iniciar(self):
        self._con.execute("BEGIN")

    def _confirmar(self):
        self._con.execute("COMMIT")

    def _deshacer(self):
        self._con.execute("ROLLBACK")

    def cerrar(self):
        with self._candado:
            self._con.close()


class ConexionMySQL(ConexionBD):
    """Conexión a MySQL/MariaDB (XAMPP, phpMyAdmin) usando PyMySQL."""

    motor = "mysql"

    # Códigos de error de MySQL traducidos a mensajes entendibles.
    MENSAJES = {
        1045: "Usuario o contraseña de MySQL incorrectos (revisa config.local.json).",
        1049: "La base de datos no existe: importa database/tutor_educa_mysql.sql en phpMyAdmin.",
        2003: "No se pudo llegar al servidor MySQL. ¿Está encendido XAMPP?",
        2005: "No se encontró el servidor MySQL indicado en config.json.",
        2006: "Se perdió la conexión con MySQL.",
        2013: "Se perdió la conexión con MySQL.",
    }

    def __init__(self, host: str, puerto: int, usuario: str, clave: str, base_datos: str,
                 tiempo_espera: int = 3):
        super().__init__()
        try:
            import pymysql  # se importa aquí para que la app funcione aunque no esté instalado
        except ImportError as error:
            raise ErrorConexion("Falta instalar PyMySQL (pip install pymysql).") from error
        self._pymysql = pymysql
        self._parametros = dict(host=host, port=int(puerto), user=usuario, password=clave,
                                database=base_datos, charset="utf8mb4", autocommit=True,
                                cursorclass=pymysql.cursors.DictCursor,
                                connect_timeout=tiempo_espera, read_timeout=15, write_timeout=15)
        self._con = None
        self._conectar()

    def _conectar(self):
        try:
            self._con = self._pymysql.connect(**self._parametros)
        except self._pymysql.MySQLError as error:
            self._con = None
            raise ErrorConexion(self._traducir(error)) from error

    def _traducir(self, error) -> str:
        codigo = error.args[0] if error.args and isinstance(error.args[0], int) else 0
        return self.MENSAJES.get(codigo, f"Error de MySQL: {error}")

    @staticmethod
    def _normalizar(fila: dict) -> dict:
        """Convierte tipos de MySQL (Decimal, datetime) a los mismos que entrega SQLite."""
        for clave, valor in fila.items():
            if isinstance(valor, Decimal):
                fila[clave] = float(valor)
            elif isinstance(valor, datetime):
                fila[clave] = valor.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(valor, date):
                fila[clave] = valor.strftime("%Y-%m-%d")
            elif isinstance(valor, bytes):
                fila[clave] = valor.decode("utf-8", errors="replace")
        return fila

    def _ejecutar(self, sql, parametros, traer_filas):
        sql = sql.replace("?", "%s")
        with self._candado:
            for intento in (1, 2):
                try:
                    if self._con is None:
                        self._conectar()
                    with self._con.cursor() as cursor:
                        cursor.execute(sql, parametros or None)
                        filas = [self._normalizar(f) for f in cursor.fetchall()] if traer_filas else []
                        return filas, cursor.lastrowid, cursor.rowcount
                except (self._pymysql.err.OperationalError, self._pymysql.err.InterfaceError) as error:
                    self._con = None
                    # Se reintenta una vez (por ejemplo si MySQL cerró la conexión
                    # por inactividad), pero nunca en medio de una transacción.
                    if intento == 2 or self._profundidad > 0:
                        raise ErrorConexion(self._traducir(error)) from error
        return [], 0, 0

    def _iniciar(self):
        if self._con is None:
            self._conectar()
        self._con.begin()

    def _confirmar(self):
        self._con.commit()

    def _deshacer(self):
        if self._con is not None:
            try:
                self._con.rollback()
            except self._pymysql.MySQLError:
                self._con = None

    def cerrar(self):
        with self._candado:
            if self._con is not None:
                try:
                    self._con.close()
                except self._pymysql.MySQLError:
                    pass
                self._con = None

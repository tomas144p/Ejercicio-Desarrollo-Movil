"""
Base de datos interna del dispositivo (SQLite).

Guarda una copia de lo que el usuario necesita para trabajar sin internet:
la materia, sus notas, los temas desbloqueados, sus intentos y los avisos.
Además tiene tres tablas propias del teléfono:

- ``credenciales``: usuarios que marcaron «Recordarme» (con su contraseña
  cifrada) para poder ingresar sin conexión.
- ``cola_sincronizacion``: cambios hechos sin conexión que faltan por enviar.
- ``preferencias``: ajustes del dispositivo.

Los registros creados sin conexión usan ids NEGATIVOS, así nunca chocan con
los ids que entrega el servidor (que son positivos).
"""

from __future__ import annotations

import json
from pathlib import Path

from ..contenido.datos_iniciales import DatosIniciales
from ..modelos import Usuario, ahora_iso
from .conexiones import ConexionSQLite
from .esquema import crear_esquema
from .repositorio import RepositorioTutor
from .servidor import PaqueteDatos


class BaseDatosLocal(RepositorioTutor):
    """Copia local de los datos + credenciales recordadas + cola de envío."""

    def __init__(self, ruta: Path):
        super().__init__(ConexionSQLite(ruta, claves_foraneas=False))
        crear_esquema(self.bd, incluir_locales=True, claves_foraneas=False)
        # La materia viene incluida en la app: se puede leer incluso antes del primer ingreso.
        if not self.bd.valor("SELECT COUNT(*) FROM temas", defecto=0):
            self.bd.insertar_tablas(DatosIniciales().contenido())

    # ------------------------------------------------------------------
    # Credenciales recordadas (ingreso sin conexión)
    # ------------------------------------------------------------------
    def guardar_credencial(self, usuario: Usuario, clave_hash: str) -> None:
        self.bd.insertar("credenciales", {
            "correo": usuario.correo, "usuario_id": usuario.id, "nombre": usuario.nombre,
            "rol": usuario.rol, "clave_hash": clave_hash, "ultimo_ingreso": ahora_iso()},
            reemplazar=True)

    def credencial(self, correo: str) -> dict | None:
        return self.bd.consultar_uno("SELECT * FROM credenciales WHERE correo = ?", (correo,))

    def credenciales_recordadas(self) -> list[dict]:
        return self.bd.consultar("SELECT correo, usuario_id, nombre, rol, ultimo_ingreso FROM credenciales "
                                 "ORDER BY ultimo_ingreso DESC")

    def registrar_ingreso(self, correo: str) -> None:
        self.bd.ejecutar("UPDATE credenciales SET ultimo_ingreso = ? WHERE correo = ?", (ahora_iso(), correo))

    def olvidar_credencial(self, correo: str) -> None:
        self.bd.ejecutar("DELETE FROM credenciales WHERE correo = ?", (correo,))

    # ------------------------------------------------------------------
    # Cola de sincronización
    # ------------------------------------------------------------------
    def encolar(self, tipo: str, datos: dict) -> None:
        self.bd.insertar("cola_sincronizacion", {"tipo": tipo, "datos": json.dumps(datos, ensure_ascii=False),
                                                 "creado_en": ahora_iso(), "intentos": 0})

    def pendientes(self) -> list[dict]:
        return self.bd.consultar("SELECT * FROM cola_sincronizacion ORDER BY id")

    def cantidad_pendientes(self) -> int:
        return int(self.bd.valor("SELECT COUNT(*) FROM cola_sincronizacion", defecto=0))

    def ultimo_id_cola(self) -> int:
        return int(self.bd.valor("SELECT MAX(id) FROM cola_sincronizacion", defecto=0))

    def quitar_de_cola(self, item_id: int) -> None:
        self.bd.ejecutar("DELETE FROM cola_sincronizacion WHERE id = ?", (item_id,))

    def registrar_error_cola(self, item_id: int, error: str) -> None:
        self.bd.ejecutar("UPDATE cola_sincronizacion SET intentos = intentos + 1, ultimo_error = ? WHERE id = ?",
                         (error[:500], item_id))

    # ------------------------------------------------------------------
    # Preferencias y utilidades
    # ------------------------------------------------------------------
    def preferencia(self, clave: str, defecto: str | None = None) -> str | None:
        return self.bd.valor("SELECT valor FROM preferencias WHERE clave = ?", (clave,), defecto)

    def guardar_preferencia(self, clave: str, valor: str) -> None:
        self.bd.insertar("preferencias", {"clave": clave, "valor": valor}, reemplazar=True)

    def id_local(self, tabla: str) -> int:
        """Id negativo para registros creados en el teléfono (no chocan con los del servidor)."""
        minimo = int(self.bd.valor(f"SELECT MIN(id) FROM {tabla}", defecto=0))
        return min(minimo, 0) - 1

    def _borrar_donde(self, tabla: str, columna: str, valores: list) -> None:
        if valores:
            marcadores = ", ".join("?" * len(valores))
            self.bd.ejecutar(f"DELETE FROM {tabla} WHERE {columna} IN ({marcadores})", list(valores))

    # ------------------------------------------------------------------
    # Descarga desde el servidor
    # ------------------------------------------------------------------
    def aplicar_paquete(self, paquete: PaqueteDatos, ultimo_id_cola: int = 0) -> bool:
        """
        Reemplaza la copia local con lo que llegó del servidor.

        Si mientras se sincronizaba el usuario hizo cambios nuevos (quedaron en
        la cola después de ``ultimo_id_cola``), no se aplica para no taparlos:
        se volverá a sincronizar en unos segundos.
        """
        with self.bd.transaccion():
            if self.bd.valor("SELECT COUNT(*) FROM cola_sincronizacion WHERE id > ?", (ultimo_id_cola,), 0):
                return False
            if paquete.temas:
                for tabla in ("preguntas", "ejemplos", "temas", "asignaturas"):
                    self.bd.ejecutar(f"DELETE FROM {tabla}")
                for tabla in ("asignaturas", "temas", "ejemplos", "preguntas"):
                    self.bd.insertar_varios(tabla, getattr(paquete, tabla))
            self.bd.insertar_varios("usuarios", [dict(f, clave_hash="") for f in paquete.usuarios], reemplazar=True)
            self.bd.insertar_varios("cursos", paquete.cursos, reemplazar=True)
            self.bd.insertar_varios("estudiantes", paquete.estudiantes, reemplazar=True)
            for tabla in ("calificaciones", "refuerzos", "intentos"):
                self._borrar_donde(tabla, "estudiante_id", paquete.estudiante_ids)
                self.bd.insertar_varios(tabla, getattr(paquete, tabla), reemplazar=True)
            self._borrar_donde("avisos", "curso_id", paquete.curso_ids)
            self.bd.insertar_varios("avisos", paquete.avisos, reemplazar=True)
            self._borrar_donde("avisos_leidos", "aviso_id", [a["id"] for a in paquete.avisos])
            self.bd.ejecutar("DELETE FROM avisos_leidos WHERE usuario_id = ?", (paquete.usuario_id,))
            self.bd.insertar_varios("avisos_leidos", paquete.lecturas, reemplazar=True)
        return True

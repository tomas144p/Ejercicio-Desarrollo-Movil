"""
El "servidor" del colegio: la base de datos central.

En la versión final debería ser MySQL (administrado con phpMyAdmin). Para
que el prototipo funcione en cualquier computador, si MySQL no responde se
usa un "servidor de demostración" (un archivo SQLite con los mismos datos).
Desde el punto de vista de la app ambos se comportan igual.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..configuracion import ConfigServidor
from ..contenido.datos_iniciales import DatosIniciales
from ..modelos import Rol, Usuario
from .conexiones import ConexionBD, ConexionMySQL, ConexionSQLite, ErrorConexion
from .esquema import crear_esquema
from .repositorio import RepositorioTutor


@dataclass
class PaqueteDatos:
    """Todo lo que un usuario necesita tener guardado en su teléfono."""

    usuario_id: int
    estudiante_ids: list[int] = field(default_factory=list)
    curso_ids: list[int] = field(default_factory=list)
    usuarios: list[dict] = field(default_factory=list)
    cursos: list[dict] = field(default_factory=list)
    estudiantes: list[dict] = field(default_factory=list)
    calificaciones: list[dict] = field(default_factory=list)
    refuerzos: list[dict] = field(default_factory=list)
    intentos: list[dict] = field(default_factory=list)
    avisos: list[dict] = field(default_factory=list)
    lecturas: list[dict] = field(default_factory=list)
    asignaturas: list[dict] = field(default_factory=list)
    temas: list[dict] = field(default_factory=list)
    ejemplos: list[dict] = field(default_factory=list)
    preguntas: list[dict] = field(default_factory=list)


class ServidorRemoto(RepositorioTutor):
    """Base de datos central (MySQL o demostración) con operaciones de sincronización."""

    def __init__(self, conexion: ConexionBD, nombre: str, es_demo: bool = False):
        super().__init__(conexion)
        self.nombre = nombre
        self.es_demo = es_demo

    def probar(self) -> bool:
        """True si el servidor responde."""
        try:
            self.bd.valor("SELECT 1")
            return True
        except ErrorConexion:
            return False
        except Exception:  # cualquier otro problema también cuenta como "sin conexión"
            return False

    def paquete_para(self, usuario: Usuario) -> PaqueteDatos:
        """Reúne solo los datos que le corresponden a ese usuario según su rol."""
        bd = self.bd
        if usuario.rol == Rol.ESTUDIANTE:
            fila = bd.consultar_uno("SELECT * FROM estudiantes WHERE usuario_id = ?", (usuario.id,))
            estudiante_ids = [usuario.id] if fila else []
            curso_ids = [int(fila["curso_id"])] if fila else []
        elif usuario.rol == Rol.DOCENTE:
            curso_ids = [int(f["id"]) for f in bd.consultar("SELECT id FROM cursos WHERE docente_id = ?",
                                                             (usuario.id,))]
            estudiante_ids = [int(f["usuario_id"]) for f in
                              self._en("SELECT usuario_id FROM estudiantes WHERE curso_id IN ({})", curso_ids)]
        else:
            filas = bd.consultar("SELECT usuario_id, curso_id FROM estudiantes WHERE apoderado_id = ?",
                                 (usuario.id,))
            estudiante_ids = [int(f["usuario_id"]) for f in filas]
            curso_ids = sorted({int(f["curso_id"]) for f in filas})

        paquete = PaqueteDatos(usuario_id=usuario.id, estudiante_ids=estudiante_ids, curso_ids=curso_ids)
        paquete.cursos = self._en("SELECT * FROM cursos WHERE id IN ({})", curso_ids)
        paquete.estudiantes = self._en("SELECT * FROM estudiantes WHERE usuario_id IN ({})", estudiante_ids)
        ids = {usuario.id, *estudiante_ids}
        ids |= {int(c["docente_id"]) for c in paquete.cursos}
        ids |= {int(e["apoderado_id"]) for e in paquete.estudiantes if e["apoderado_id"]}
        # Nunca se envían las contraseñas de otras personas al teléfono.
        paquete.usuarios = self._en("SELECT id, correo, nombre, rol, activo, creado_en FROM usuarios "
                                    "WHERE id IN ({})", sorted(ids))
        paquete.calificaciones = self._en("SELECT * FROM calificaciones WHERE estudiante_id IN ({})", estudiante_ids)
        paquete.refuerzos = self._en("SELECT * FROM refuerzos WHERE estudiante_id IN ({})", estudiante_ids)
        paquete.intentos = self._en("SELECT * FROM intentos WHERE estudiante_id IN ({})", estudiante_ids)
        if usuario.rol == Rol.DOCENTE:
            paquete.avisos = self.avisos(curso_ids)
            paquete.lecturas = self.lecturas([int(a["id"]) for a in paquete.avisos])
        else:
            paquete.avisos = self.avisos(curso_ids, estudiante_ids)
            paquete.lecturas = bd.consultar("SELECT * FROM avisos_leidos WHERE usuario_id = ?", (usuario.id,))
        for tabla in ("asignaturas", "temas", "ejemplos", "preguntas"):
            setattr(paquete, tabla, bd.consultar(f"SELECT * FROM {tabla}"))
        return paquete

    def aplicar_cambio(self, tipo: str, datos: dict) -> None:
        """Aplica en el servidor un cambio que se hizo en el teléfono (cola de sincronización)."""
        if tipo == "intento":
            self.registrar_intento(datos)
        elif tipo == "estado_refuerzo":
            self.avanzar_estado_refuerzo(datos["estudiante_id"], datos["tema_id"], datos["estado"], datos["fecha"])
        elif tipo == "desbloqueo":
            self.guardar_refuerzo(datos["estudiante_id"], datos["tema_id"], datos["activo"], datos.get("mensaje"),
                                  datos.get("docente_id"), datos["fecha"])
        elif tipo == "aviso":
            self.publicar_aviso(datos)
        elif tipo == "aviso_leido":
            aviso = self.aviso_por_codigo(datos["aviso_codigo"])
            if aviso:
                self.marcar_aviso_leido(int(aviso["id"]), datos["usuario_id"], datos["fecha"])
        else:
            raise ValueError(f"Tipo de cambio desconocido: {tipo}")


class GestorServidor:
    """
    Decide qué servidor usar según config.json:

    - "mysql": solo MySQL. Si no responde, la app trabaja sin conexión.
    - "demo": siempre el servidor de demostración (SQLite).
    - "auto": intenta MySQL y, si no está disponible, usa el de demostración.
    """

    def __init__(self, config: ConfigServidor, carpeta_datos: Path):
        self.config = config
        self.carpeta = Path(carpeta_datos)
        self.servidor: ServidorRemoto | None = None
        self.descripcion = "Conectando…"
        self.diagnostico = "Buscando el servidor del colegio…"
        self._candado = threading.Lock()
        self._ultimo_intento = 0.0

    @property
    def es_demo(self) -> bool:
        return bool(self.servidor and self.servidor.es_demo)

    def inicializar(self) -> "GestorServidor":
        """Conecta con el servidor que corresponda. Puede tardar unos segundos (usar en segundo plano)."""
        with self._candado:
            self._ultimo_intento = time.monotonic()
            motor = (self.config.motor or "auto").lower()
            motivo = ""
            if motor in ("auto", "mysql"):
                try:
                    self.servidor = self._conectar_mysql()
                    self.descripcion = f"MySQL en {self.config.host}"
                    self.diagnostico = "Conectado a la base de datos MySQL del colegio (phpMyAdmin)."
                    return self
                except ErrorConexion as error:
                    motivo = str(error)
                    if motor == "mysql":
                        self.servidor = None
                        self.descripcion = "MySQL no disponible"
                        self.diagnostico = (f"{motivo} Mientras tanto se puede ingresar con las cuentas "
                                            "recordadas en este dispositivo.")
                        return self
            self.servidor = self._abrir_demo()
            self.descripcion = "Servidor de demostración"
            detalle = f" MySQL no respondió: {motivo}" if motivo else ""
            self.diagnostico = ("Se usa el servidor de demostración (SQLite) con las cuentas de prueba."
                                f"{detalle} Para trabajar con phpMyAdmin, importa "
                                "database/tutor_educa_mysql.sql y vuelve a abrir la app.")
        return self

    def _conectar_mysql(self) -> ServidorRemoto:
        c = self.config
        conexion = ConexionMySQL(c.host, c.puerto, c.usuario, c.clave, c.base_datos, c.tiempo_espera)
        existe = conexion.valor("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = ? "
                                "AND table_name = 'usuarios'", (c.base_datos,), 0)
        if not existe:
            conexion.cerrar()
            raise ErrorConexion(f"La base '{c.base_datos}' no tiene tablas: importa "
                                "database/tutor_educa_mysql.sql en phpMyAdmin.")
        return ServidorRemoto(conexion, "MySQL", es_demo=False)

    def _abrir_demo(self) -> ServidorRemoto:
        conexion = ConexionSQLite(self.carpeta / "servidor_demo.db", claves_foraneas=True)
        crear_esquema(conexion, incluir_locales=False, claves_foraneas=True)
        if not conexion.valor("SELECT COUNT(*) FROM usuarios", defecto=0):
            conexion.insertar_tablas(DatosIniciales().todo())
        return ServidorRemoto(conexion, "Demostración", es_demo=True)

    def disponible(self) -> bool:
        """Comprueba si el servidor responde (reintenta MySQL cada 20 s si estaba caído)."""
        if self.servidor is None:
            if (self.config.motor or "").lower() == "mysql" and time.monotonic() - self._ultimo_intento > 20:
                self.inicializar()
            if self.servidor is None:
                return False
        return self.servidor.probar()

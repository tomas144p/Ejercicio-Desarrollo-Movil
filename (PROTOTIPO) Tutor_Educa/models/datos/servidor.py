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

from services.configuracion import ConfigServidor
from services.seguridad import GestorClaves
from models.contenido.datos_iniciales import DatosIniciales
from models.modelos import Rol, Usuario
from models.datos.conexiones import ConexionBD, ConexionMySQL, ConexionSQLite, ErrorConexion
from models.datos.esquema import crear_esquema
from models.datos.repositorio import RepositorioTutor


@dataclass
class PaqueteDatos:
    """Todo lo que un usuario necesita tener guardado en su teléfono."""

    usuario_id: int
    estudiante_ids: list[int] = field(default_factory=list)
    curso_ids: list[int] = field(default_factory=list)
    colegios: list[dict] = field(default_factory=list)
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

    def verificar_ingreso(self, correo: str, clave: str) -> tuple[dict | None, str]:
        """(fila de la persona, "") si la contraseña es correcta; (None, mensaje) si no. Mismo contrato que ServidorHTTP."""
        fila = self.usuario_por_correo(correo)
        if fila is None:
            return None, "No encontramos una cuenta con ese correo."
        if not int(fila.get("activo", 1)):
            return None, "Esta cuenta está desactivada. Habla con tu colegio."
        if not GestorClaves.verificar(clave, fila["clave_hash"]):
            return None, "La contraseña no es correcta."
        return fila, ""

    def paquete_para(self, usuario: Usuario) -> PaqueteDatos:
        """
        Reúne solo los datos que le corresponden a ese usuario según su rol Y su colegio.

        Cada consulta lleva el colegio de la persona: aunque alguien dejara un dato mal enlazado en la base
        (un estudiante de un colegio apuntando al curso de otro, por ejemplo), no se mezcla ni se envía.
        Una cuenta sin colegio no recibe datos de personas (solo la materia).
        """
        bd = self.bd
        colegio_id = usuario.colegio_id
        paquete = PaqueteDatos(usuario_id=usuario.id)
        if colegio_id is not None:
            self._datos_del_colegio(paquete, usuario, int(colegio_id))
        for tabla in ("asignaturas", "temas", "ejemplos", "preguntas"):
            setattr(paquete, tabla, bd.consultar(f"SELECT * FROM {tabla}"))
        return paquete

    def _datos_del_colegio(self, paquete: PaqueteDatos, usuario: Usuario, colegio_id: int) -> None:
        bd = self.bd
        if usuario.rol == Rol.ESTUDIANTE:
            fila = bd.consultar_uno("SELECT e.usuario_id, e.curso_id FROM estudiantes e "
                                    "JOIN cursos c ON c.id = e.curso_id "
                                    "WHERE e.usuario_id = ? AND c.colegio_id = ?", (usuario.id, colegio_id))
            estudiante_ids = [usuario.id] if fila else []
            curso_ids = [int(fila["curso_id"])] if fila else []
        elif usuario.rol == Rol.DOCENTE:
            curso_ids = [int(f["id"]) for f in bd.consultar(
                "SELECT id FROM cursos WHERE docente_id = ? AND colegio_id = ?", (usuario.id, colegio_id))]
            estudiante_ids = [int(f["usuario_id"]) for f in self._en(
                "SELECT e.usuario_id FROM estudiantes e JOIN usuarios u ON u.id = e.usuario_id "
                "WHERE e.curso_id IN ({}) AND u.colegio_id = ? AND u.activo = 1", curso_ids, (colegio_id,))]
        else:
            filas = bd.consultar(
                "SELECT e.usuario_id, e.curso_id FROM estudiantes e "
                "JOIN cursos c ON c.id = e.curso_id JOIN usuarios u ON u.id = e.usuario_id "
                "WHERE e.apoderado_id = ? AND c.colegio_id = ? AND u.colegio_id = ? AND u.activo = 1",
                (usuario.id, colegio_id, colegio_id))
            estudiante_ids = [int(f["usuario_id"]) for f in filas]
            curso_ids = sorted({int(f["curso_id"]) for f in filas})

        paquete.estudiante_ids, paquete.curso_ids = estudiante_ids, curso_ids
        paquete.colegios = bd.consultar("SELECT * FROM colegios WHERE id = ?", (colegio_id,))
        paquete.cursos = self._en("SELECT * FROM cursos WHERE id IN ({}) AND colegio_id = ?", curso_ids, (colegio_id,))
        paquete.estudiantes = self._en("SELECT * FROM estudiantes WHERE usuario_id IN ({})", estudiante_ids)
        ids = {usuario.id, *estudiante_ids}
        ids |= {int(c["docente_id"]) for c in paquete.cursos}
        ids |= {int(e["apoderado_id"]) for e in paquete.estudiantes if e["apoderado_id"]}
        # Nunca se envían las contraseñas de otras personas al teléfono, ni personas de otro colegio.
        paquete.usuarios = self._en("SELECT id, correo, nombre, rol, activo, creado_en, colegio_id FROM usuarios "
                                    "WHERE id IN ({}) AND colegio_id = ?", sorted(ids), (colegio_id,))
        paquete.calificaciones = self._en("SELECT * FROM calificaciones WHERE estudiante_id IN ({})", estudiante_ids)
        paquete.refuerzos = self._en("SELECT * FROM refuerzos WHERE estudiante_id IN ({})", estudiante_ids)
        paquete.intentos = self._en("SELECT * FROM intentos WHERE estudiante_id IN ({})", estudiante_ids)
        if usuario.rol == Rol.DOCENTE:
            paquete.avisos = self.avisos(curso_ids)
            paquete.lecturas = self.lecturas([int(a["id"]) for a in paquete.avisos])
        else:
            paquete.avisos = self.avisos(curso_ids, estudiante_ids)
            paquete.lecturas = bd.consultar("SELECT * FROM avisos_leidos WHERE usuario_id = ?", (usuario.id,))

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
        elif tipo == "error_app":
            self.registrar_error_app(datos)
        else:
            raise ValueError(f"Tipo de cambio desconocido: {tipo}")


class GestorServidor:
    """
    Decide qué servidor usar según config.json:

    - "mysql": solo MySQL. Si no responde, la app trabaja sin conexión.
    - "demo": siempre el servidor de demostración (SQLite).
    - "auto": intenta MySQL y, si no está disponible, usa el de demostración.
    - "http": la API del backend (versión real: la app no lleva claves de base de datos).
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

    @property
    def usa_backend(self) -> bool:
        """True si la app habla con la API (en ese caso la IA también se pide al servidor)."""
        return (self.config.motor or "").lower() == "http"

    def cerrar_sesion(self) -> None:
        """Olvida la sesión de la persona que salió (solo aplica al modo API)."""
        if self.servidor is not None and hasattr(self.servidor, "cerrar_sesion"):
            self.servidor.cerrar_sesion()

    def inicializar(self) -> "GestorServidor":
        """Conecta con el servidor que corresponda. Puede tardar unos segundos (usar en segundo plano)."""
        with self._candado:
            self._ultimo_intento = time.monotonic()
            motor = (self.config.motor or "auto").lower()
            motivo = ""
            if motor == "http":
                return self._conectar_http()
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

    def _conectar_http(self) -> "GestorServidor":
        from models.datos.servidor_http import ServidorHTTP   # import tardío: servidor_http importa PaqueteDatos de aquí
        try:
            self.servidor = ServidorHTTP(self.config.url, self.config.tiempo_http)
        except ValueError as error:
            self.servidor = None
            self.descripcion = "Servidor mal configurado"
            self.diagnostico = str(error)
            return self
        self.descripcion = "Servidor del colegio"
        self.diagnostico = f"La app usa la API del colegio en {self.servidor.url}."
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
        tiene_colegios = conexion.valor("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = ? "
                                        "AND table_name = 'colegios'", (c.base_datos,), 0)
        if not tiene_colegios:
            conexion.cerrar()
            raise ErrorConexion(f"La base '{c.base_datos}' es de una versión anterior (sin colegios): vuelve a "
                                "importar database/tutor_educa_mysql.sql o aplica database/migracion_colegios.sql.")
        return ServidorRemoto(conexion, "MySQL", es_demo=False)

    def _abrir_demo(self) -> ServidorRemoto:
        archivo = self.carpeta / "servidor_demo.db"
        conexion = ConexionSQLite(archivo, claves_foraneas=True)
        if self._demo_sin_perfiles_nuevos(conexion):
            # SQLite no permite cambiar la restricción de la columna «rol»: la base de demostración (que solo trae
            # datos de ejemplo) se aparta con otro nombre y se crea de nuevo con el esquema actual.
            conexion.cerrar()
            archivo.replace(archivo.with_name("servidor_demo.antigua.db"))
            conexion = ConexionSQLite(archivo, claves_foraneas=True)
        crear_esquema(conexion, incluir_locales=False, claves_foraneas=True)
        if not conexion.valor("SELECT COUNT(*) FROM usuarios", defecto=0):
            conexion.insertar_tablas(DatosIniciales().todo())
        self._asignar_colegio_demo(conexion)
        return ServidorRemoto(conexion, "Demostración", es_demo=True)

    @staticmethod
    def _demo_sin_perfiles_nuevos(conexion) -> bool:
        """True si la tabla usuarios ya existe pero su restricción de «rol» no admite administradores."""
        fila = conexion.consultar_uno("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'usuarios'")
        return bool(fila) and "'superadmin'" not in (fila["sql"] or "")

    @staticmethod
    def _asignar_colegio_demo(conexion) -> None:
        """Una base de demostración creada antes de que existieran los colegios queda en «Colegio Demo»."""
        huerfanos = (conexion.valor("SELECT COUNT(*) FROM usuarios WHERE colegio_id IS NULL", defecto=0)
                     + conexion.valor("SELECT COUNT(*) FROM cursos WHERE colegio_id IS NULL", defecto=0))
        if not huerfanos:
            return
        if not conexion.valor("SELECT COUNT(*) FROM colegios", defecto=0):
            conexion.insertar("colegios", {"id": 1, "nombre": "Colegio Demo", "activo": 1,
                                           "creado_en": DatosIniciales().fecha_hora_actual()})
        primero = conexion.valor("SELECT MIN(id) FROM colegios", defecto=1)
        conexion.ejecutar("UPDATE usuarios SET colegio_id = ? WHERE colegio_id IS NULL", (primero,))
        conexion.ejecutar("UPDATE cursos SET colegio_id = ? WHERE colegio_id IS NULL", (primero,))

    def disponible(self) -> bool:
        """Comprueba si el servidor responde (reintenta MySQL cada 20 s si estaba caído)."""
        if self.servidor is None:
            if (self.config.motor or "").lower() == "mysql" and time.monotonic() - self._ultimo_intento > 20:
                self.inicializar()
            if self.servidor is None:
                return False
        return self.servidor.probar()

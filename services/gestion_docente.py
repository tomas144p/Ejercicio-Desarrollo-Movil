"""
Lo que una docente puede hacer con sus estudiantes y apoderados: agregar, dar de baja, cambiar de curso o de apoderado
y generar un código nuevo para entrar.

Todo esto necesita estar conectada al servidor del colegio (las cuentas y los códigos los crea el servidor, no la app),
así que NO se guarda en la cola de cambios sin conexión. Si no hay conexión, se dice con claridad.

Después de cada cambio se vuelven a descargar los datos para que las listas del teléfono se actualicen.
Sin Kivy: se prueba directamente. Operaciones bloqueantes: usar en segundo plano.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from models.datos.conexiones import ErrorConexion
from models.datos.servidor_http import ErrorGestion
from models.modelos import FORMATO_FECHA
from services.validaciones import validar_correo

MENSAJE_SIN_SERVIDOR = ("Esta función necesita el servidor del colegio. Pide a quien administra la app que la conecte "
                        "(ver backend/README.md).")
MENSAJE_SIN_CONEXION = "Necesitas conexión con el servidor del colegio para hacer esto. Intenta de nuevo cuando tengas internet."


@dataclass
class Codigo:
    """Un código de invitación recién generado: se muestra una sola vez."""
    para: str                 # nombre de la persona
    correo: str
    codigo: str
    vence_en: str
    rol: str                  # "estudiante" o "apoderado"
    mensaje: str = ""         # texto listo para copiar y enviar


@dataclass
class ResultadoGestion:
    exito: bool
    mensaje: str = ""
    codigos: list[Codigo] = field(default_factory=list)
    datos: list = field(default_factory=list)
    apoderado_existente: str = ""        # nombre del apoderado que ya existía y solo se vinculó


def mensaje_invitacion(nombre: str, correo: str, codigo: str, vence_en: str, colegio: str = "",
                       docente: str = "") -> str:
    """El texto que la docente copia y pega en WhatsApp o un correo."""
    primero = (nombre or "").split()[0] if nombre else ""
    de_parte = f" de parte de {docente}" if docente else ""
    en_colegio = f" ({colegio})" if colegio else ""
    try:
        vence = datetime.strptime(vence_en, FORMATO_FECHA).strftime("%d-%m-%Y")
    except (ValueError, TypeError):
        vence = vence_en
    return (f"Hola {primero}, te invitan{de_parte} a Tutor Educa{en_colegio}.\n"
            f"1) Abre la app y toca «Tengo un código».\n"
            f"2) Escribe tu correo: {correo}\n"
            f"3) Escribe este código: {codigo} (sirve una sola vez y vence el {vence}).\n"
            f"4) Elige tu propia contraseña. Nadie más la conoce.").strip()


class ServicioGestion:
    def __init__(self, gestor_servidor, sincronizacion, monitor=None, local=None):
        self.gestor_servidor = gestor_servidor
        self.sincronizacion = sincronizacion
        self.monitor = monitor
        self.local = local

    # ------------------------------------------------------------------
    @property
    def servidor(self):
        servidor = self.gestor_servidor.servidor
        return servidor if servidor is not None and hasattr(servidor, "crear_estudiante") else None

    @property
    def disponible(self) -> bool:
        """¿La app está configurada para hablar con el servidor del colegio (modo API)?"""
        return self.gestor_servidor.usa_backend

    def _nombre_colegio(self, usuario) -> str:
        if self.local is None or usuario.colegio_id is None:
            return ""
        fila = self.local.colegio(int(usuario.colegio_id))
        return fila["nombre"] if fila else ""

    def _ejecutar(self, usuario, accion, refrescar: bool = True) -> ResultadoGestion:
        servidor = self.servidor
        if servidor is None:
            return ResultadoGestion(False, MENSAJE_SIN_SERVIDOR)
        if self.monitor is not None and self.monitor.forzado_sin_conexion:
            return ResultadoGestion(False, MENSAJE_SIN_CONEXION)
        try:
            resultado = accion(servidor)
        except ErrorGestion as error:
            return ResultadoGestion(False, str(error))
        except ErrorConexion:
            return ResultadoGestion(False, MENSAJE_SIN_CONEXION)
        if refrescar:
            self.sincronizacion.sincronizar(usuario)         # actualiza las listas del teléfono
        return resultado

    def _codigo(self, usuario, detalle: dict, rol: str) -> Codigo | None:
        """Convierte la respuesta del servidor en un ``Codigo`` (o None si la cuenta ya existía y no hay código)."""
        if not detalle or not detalle.get("codigo"):
            return None
        cuenta = detalle["usuario"]
        return Codigo(cuenta["nombre"], cuenta["correo"], detalle["codigo"], detalle.get("vence_en", ""), rol,
                      mensaje_invitacion(cuenta["nombre"], cuenta["correo"], detalle["codigo"],
                                         detalle.get("vence_en", ""), self._nombre_colegio(usuario), usuario.nombre))

    # ------------------------------------------------------------------
    def agregar_estudiante(self, usuario, curso_id: int, nombre: str, correo: str, apoderado_correo: str = "",
                           apoderado_nombre: str = "") -> ResultadoGestion:
        nombre, apoderado_nombre = " ".join(nombre.split()), " ".join((apoderado_nombre or "").split())
        try:
            correo = validar_correo(correo)
            apoderado_correo = validar_correo(apoderado_correo) if (apoderado_correo or "").strip() else ""
        except ValueError as error:
            return ResultadoGestion(False, str(error))
        if len(nombre) < 3:
            return ResultadoGestion(False, "Escribe el nombre completo del estudiante.")

        def accion(servidor) -> ResultadoGestion:
            r = servidor.crear_estudiante(correo, nombre, curso_id, apoderado_correo, apoderado_nombre)
            codigos = [c for c in (self._codigo(usuario, r, "estudiante"),
                                   self._codigo(usuario, r.get("apoderado") or {}, "apoderado")) if c]
            existente = r.get("apoderado") or {}
            return ResultadoGestion(True, f"{nombre} fue agregado/a al curso.", codigos,
                                    apoderado_existente=existente["usuario"]["nombre"] if existente.get("existente") else "")

        return self._ejecutar(usuario, accion)

    def dar_de_baja(self, usuario, estudiante_id: int) -> ResultadoGestion:
        def accion(servidor) -> ResultadoGestion:
            servidor.cambiar_estudiante(estudiante_id, activo=False)
            return ResultadoGestion(True, "Listo. Ya no aparece en tus listas; sus datos se conservan y puedes reactivarlo.")
        return self._ejecutar(usuario, accion)

    def reactivar(self, usuario, estudiante_id: int) -> ResultadoGestion:
        def accion(servidor) -> ResultadoGestion:
            servidor.cambiar_estudiante(estudiante_id, activo=True)
            return ResultadoGestion(True, "Estudiante reactivado/a.")
        return self._ejecutar(usuario, accion)

    def cambiar_curso(self, usuario, estudiante_id: int, curso_id: int) -> ResultadoGestion:
        def accion(servidor) -> ResultadoGestion:
            servidor.cambiar_estudiante(estudiante_id, curso_id=curso_id)
            return ResultadoGestion(True, "Estudiante cambiado/a de curso.")
        return self._ejecutar(usuario, accion)

    def cambiar_apoderado(self, usuario, estudiante_id: int, correo: str, nombre: str = "") -> ResultadoGestion:
        try:
            correo = validar_correo(correo)
        except ValueError as error:
            return ResultadoGestion(False, str(error))
        nombre = " ".join((nombre or "").split())

        def accion(servidor) -> ResultadoGestion:
            r = servidor.cambiar_estudiante(estudiante_id, apoderado_correo=correo, apoderado_nombre=nombre or None)
            detalle = r.get("apoderado") or {}
            codigo = self._codigo(usuario, detalle, "apoderado")
            return ResultadoGestion(True, "Apoderado actualizado.", [codigo] if codigo else [],
                                    apoderado_existente=detalle["usuario"]["nombre"] if detalle.get("existente") else "")
        return self._ejecutar(usuario, accion)

    def quitar_apoderado(self, usuario, estudiante_id: int) -> ResultadoGestion:
        def accion(servidor) -> ResultadoGestion:
            servidor.cambiar_estudiante(estudiante_id, quitar_apoderado=True)
            return ResultadoGestion(True, "El estudiante quedó sin apoderado.")
        return self._ejecutar(usuario, accion)

    def codigo_nuevo(self, usuario, usuario_id: int, rol: str) -> ResultadoGestion:
        """Código nuevo para una cuenta: la contraseña anterior deja de servir (olvidó su contraseña o nunca activó)."""
        def accion(servidor) -> ResultadoGestion:
            r = servidor.codigo_nuevo(usuario_id)
            codigo = self._codigo(usuario, r, rol)
            return ResultadoGestion(bool(codigo), "Código nuevo generado." if codigo else "No se pudo generar el código.",
                                    [codigo] if codigo else [])
        return self._ejecutar(usuario, accion, refrescar=False)

    def dados_de_baja(self, usuario) -> ResultadoGestion:
        def accion(servidor) -> ResultadoGestion:
            return ResultadoGestion(True, datos=servidor.estudiantes_dados_de_baja())
        return self._ejecutar(usuario, accion, refrescar=False)

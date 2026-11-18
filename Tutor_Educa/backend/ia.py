"""
Intermediario con la IA (Claude).

La clave de la IA vive solo aquí, en el servidor. La app envía las instrucciones y el historial; el servidor
agrega sus propias reglas, limita cuánto se puede usar y llama a la IA.

Pendiente (ver PENDIENTES.md): hoy el celular arma las instrucciones con los datos del estudiante. Lo ideal
es que el servidor las arme él mismo con lo que tiene en la base de datos.
"""

from __future__ import annotations

from backend.ajustes import Ajustes
from backend.seguridad_api import LimitadorVentana
from models.modelos import Rol, Usuario
from services.ia.proveedores import ErrorIA, ProveedorAnthropic, ProveedorIA

REGLAS_SERVIDOR = (
    "Eres el tutor de Tutor Educa, una app de refuerzo de matemáticas para estudiantes de 5° a 8° básico en Chile "
    "y para sus familias. Habla en español simple y con cariño. Responde solo sobre estudio, matemáticas y cómo "
    "acompañar a un estudiante. Si te piden otra cosa, explica amablemente que no puedes ayudar con eso y vuelve "
    "al tema. Nunca pidas ni repitas datos personales como direcciones, teléfonos o contraseñas.\n\n")

MAX_SISTEMA = 12_000
MAX_MENSAJES = 20
MAX_LARGO_MENSAJE = 2_000


class ErrorUsoIA(Exception):
    """La petición no se puede atender. ``codigo`` es el estado HTTP sugerido."""

    def __init__(self, mensaje: str, codigo: int = 400, espera: int = 0):
        super().__init__(mensaje)
        self.codigo, self.espera = codigo, espera


class ServicioIAServidor:
    def __init__(self, ajustes: Ajustes, proveedor: ProveedorIA | None = None):
        self.proveedor = proveedor
        if self.proveedor is None and ajustes.ia_api_key:
            self.proveedor = ProveedorAnthropic(ajustes.ia_api_key, ajustes.ia_modelo, ajustes.ia_max_tokens, 40)
        self._por_minuto = LimitadorVentana(ajustes.ia_por_minuto, 60)
        self._por_dia = LimitadorVentana(ajustes.ia_cuota_diaria, 86_400)

    @property
    def disponible(self) -> bool:
        return self.proveedor is not None

    def responder(self, usuario: Usuario, sistema: str, mensajes: list[dict]) -> str:
        if usuario.rol not in (Rol.ESTUDIANTE, Rol.APODERADO):
            raise ErrorUsoIA("El tutor IA es para estudiantes y apoderados.", 403)
        if self.proveedor is None:
            raise ErrorUsoIA("El tutor IA no está activado en este servidor.", 503)
        self._validar(sistema, mensajes)
        clave = str(usuario.id)
        espera = self._por_minuto.intentar(clave)
        if espera:
            raise ErrorUsoIA("Estás escribiendo muy rápido. Espera un momento.", 429, espera)
        espera = self._por_dia.intentar(clave)
        if espera:
            raise ErrorUsoIA("Llegaste al límite de mensajes de hoy. Vuelve mañana.", 429, espera)
        try:
            return self.proveedor.responder(REGLAS_SERVIDOR + sistema, mensajes)
        except ErrorIA as error:
            raise ErrorUsoIA(str(error), 502) from error

    @staticmethod
    def _validar(sistema: str, mensajes: list[dict]) -> None:
        if not sistema or len(sistema) > MAX_SISTEMA:
            raise ErrorUsoIA("Las instrucciones del tutor no son válidas.", 422)
        if not mensajes or len(mensajes) > MAX_MENSAJES:
            raise ErrorUsoIA("El historial de la conversación no es válido.", 422)
        esperado = "user"
        for mensaje in mensajes:
            texto = mensaje.get("content")
            if mensaje.get("role") != esperado or not isinstance(texto, str) or not texto.strip() \
                    or len(texto) > MAX_LARGO_MENSAJE * 2:
                raise ErrorUsoIA("El historial de la conversación no es válido.", 422)
            esperado = "assistant" if esperado == "user" else "user"
        if mensajes[-1]["role"] != "user":
            raise ErrorUsoIA("El último mensaje debe ser del usuario.", 422)

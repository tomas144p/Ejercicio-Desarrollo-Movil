"""
Conversación del chat y servicio que elige qué tutor responde.

``ServicioTutorIA`` crea el proveedor según config.json:
- con clave de Anthropic → Claude;
- con ``url_base`` y proveedor "openai_compatible" → ese servicio;
- sin clave → el tutor de demostración (``TutorLocal``).

Si la IA real falla (sin saldo, sin internet...), la conversación no se
corta: responde el tutor de demostración y se muestra una nota explicando qué pasó.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ...modelos import FichaEstudiante, Tema, Usuario
from .instrucciones import Instrucciones
from .proveedores import ErrorIA, ProveedorAnthropic, ProveedorCompatibleOpenAI, ProveedorIA
from .tutor_local import EstadoTutorLocal, TutorLocal


@dataclass
class MensajeChat:
    rol: str            # "tutor" | "usuario"
    texto: str
    nota: str = ""      # aviso pequeño bajo el mensaje (por ejemplo, si respondió el respaldo)


@dataclass
class ContextoConversacion:
    """Lo que el tutor necesita saber de quién habla y sobre qué."""

    modo: str                                   # "estudiante" | "apoderado"
    usuario: Usuario
    tema: Tema | None = None
    ficha: FichaEstudiante | None = None        # del estudiante (o del hijo, en modo apoderado)
    avisos: list = field(default_factory=list)
    nombres_asignaturas: dict = field(default_factory=dict)

    @property
    def clave(self) -> str:
        tema = self.tema.id if self.tema else "-"
        estudiante = self.ficha.estudiante.id if self.ficha else "-"
        return f"{self.usuario.id}:{self.modo}:{tema}:{estudiante}"


class Conversacion:
    MAX_MENSAJES_API = 20

    def __init__(self, contexto: ContextoConversacion, proveedor: ProveedorIA | None,
                 tutor_local: TutorLocal, datos):
        self.contexto = contexto
        self.proveedor = proveedor
        self.tutor_local = tutor_local
        self.datos = datos
        self.estado_local = EstadoTutorLocal(tema_id=contexto.tema.id if contexto.tema else None)
        self.mensajes: list[MensajeChat] = [MensajeChat("tutor", tutor_local.saludo(contexto))]

    @property
    def usa_ia(self) -> bool:
        return self.proveedor is not None

    def agregar_usuario(self, texto: str) -> MensajeChat:
        mensaje = MensajeChat("usuario", texto.strip())
        self.mensajes.append(mensaje)
        return mensaje

    def generar_respuesta(self) -> MensajeChat:
        """Responde al último mensaje del usuario. Bloqueante: usar en segundo plano."""
        ultimo = next((m.texto for m in reversed(self.mensajes) if m.rol == "usuario"), "")
        if self.proveedor is not None:
            try:
                texto = self.proveedor.responder(self._instrucciones(), self._historial_api())
                mensaje = MensajeChat("tutor", texto)
            except ErrorIA as error:
                texto = self.tutor_local.responder(self.contexto, self.estado_local, ultimo)
                mensaje = MensajeChat("tutor", texto, nota=f"{error} Respondió el tutor sin conexión.")
        else:
            mensaje = MensajeChat("tutor", self.tutor_local.responder(self.contexto, self.estado_local, ultimo))
        self.mensajes.append(mensaje)
        return mensaje

    def _instrucciones(self) -> str:
        if self.contexto.modo == "apoderado":
            return Instrucciones.para_apoderado(self.contexto)
        ejemplos = self.datos.ejemplos(self.contexto.tema.id) if self.contexto.tema else []
        return Instrucciones.para_estudiante(self.contexto, ejemplos)

    def _historial_api(self) -> list[dict]:
        """Historial en el formato de la API: empieza con "user" y alterna roles."""
        historial: list[dict] = []
        for mensaje in self.mensajes[1:]:            # el saludo inicial es local
            rol = "user" if mensaje.rol == "usuario" else "assistant"
            if historial and historial[-1]["role"] == rol:
                historial[-1]["content"] += "\n\n" + mensaje.texto
            else:
                historial.append({"role": rol, "content": mensaje.texto})
        historial = historial[-self.MAX_MENSAJES_API:]
        while historial and historial[0]["role"] != "user":
            historial.pop(0)
        return historial


class ServicioTutorIA:
    """Crea y guarda las conversaciones (una por usuario, modo y tema)."""

    def __init__(self, config_ia, datos):
        self.config = config_ia
        self.datos = datos
        self.proveedor = self._crear_proveedor(config_ia)
        self.tutor_local = TutorLocal(datos)
        self._conversaciones: dict[str, Conversacion] = {}

    @staticmethod
    def _crear_proveedor(c) -> ProveedorIA | None:
        tipo = (c.proveedor or "").lower()
        if tipo == "anthropic" and c.api_key:
            return ProveedorAnthropic(c.api_key, c.modelo, c.max_tokens, c.tiempo_espera)
        if tipo == "openai_compatible" and c.url_base:
            return ProveedorCompatibleOpenAI(c.url_base, c.api_key, c.modelo, c.max_tokens, c.tiempo_espera)
        return None

    @property
    def usa_ia_real(self) -> bool:
        return self.proveedor is not None

    @property
    def descripcion(self) -> str:
        return self.proveedor.nombre if self.proveedor else "Tutor de demostración"

    def conversacion(self, contexto: ContextoConversacion) -> Conversacion:
        if contexto.clave not in self._conversaciones:
            self._conversaciones[contexto.clave] = Conversacion(contexto, self.proveedor, self.tutor_local, self.datos)
        conversacion = self._conversaciones[contexto.clave]
        conversacion.contexto = contexto   # datos frescos (notas, avisos) en cada apertura
        return conversacion

    def olvidar_conversaciones(self) -> None:
        self._conversaciones.clear()

"""
Proveedores de inteligencia artificial para el chat.

``ProveedorIA`` es una clase abstracta: define que todo proveedor debe saber
``responder(sistema, mensajes)``. Hay dos implementaciones:

- ``ProveedorAnthropic``: usa Claude mediante la API oficial de Anthropic.
- ``ProveedorCompatibleOpenAI``: cualquier servicio con la API "estilo
  OpenAI" (Ollama en el mismo PC, LM Studio, Groq, OpenRouter...).

Se usa solo ``urllib`` (incluido en Python), así no hay que instalar
librerías extra para compilar en Android.
"""

from __future__ import annotations

import json
import socket
import ssl
import urllib.error
import urllib.request
from abc import ABC, abstractmethod


class ErrorIA(Exception):
    """Algo falló al hablar con la IA. El mensaje ya viene en español simple."""


def _contextos_ssl() -> list[ssl.SSLContext]:
    """
    Certificados para HTTPS: primero los del sistema y, si fallan (pasa en
    Android), los del paquete "certifi".
    """
    contextos = [ssl.create_default_context()]
    try:
        import certifi
        contextos.append(ssl.create_default_context(cafile=certifi.where()))
    except Exception:
        pass
    return contextos


class ProveedorIA(ABC):
    nombre = "IA"

    def __init__(self, modelo: str, max_tokens: int = 700, tiempo_espera: int = 40):
        self.modelo = modelo
        self.max_tokens = max_tokens
        self.tiempo_espera = tiempo_espera

    @abstractmethod
    def responder(self, sistema: str, mensajes: list[dict]) -> str:
        """Recibe las instrucciones y el historial [{"role", "content"}] y devuelve el texto."""

    def _post_json(self, url: str, cuerpo: dict, cabeceras: dict) -> dict:
        datos = json.dumps(cuerpo).encode("utf-8")
        solicitud = urllib.request.Request(url, data=datos, method="POST",
                                           headers={"content-type": "application/json", **cabeceras})
        contextos = _contextos_ssl()
        for numero, contexto in enumerate(contextos, start=1):
            try:
                return self._enviar(solicitud, contexto)
            except urllib.error.URLError as error:
                certificado = isinstance(getattr(error, "reason", None), ssl.SSLError)
                if certificado and numero < len(contextos) and not isinstance(error, urllib.error.HTTPError):
                    continue   # se prueba con los otros certificados
                raise ErrorIA(self._mensaje_error(error)) from error
            except (socket.timeout, TimeoutError) as error:
                raise ErrorIA("La IA tardó demasiado en responder.") from error
            except (OSError, ValueError) as error:
                raise ErrorIA("No hay conexión con el servicio de IA.") from error
        raise ErrorIA("No hay conexión con el servicio de IA.")

    def _enviar(self, solicitud, contexto) -> dict:
        with urllib.request.urlopen(solicitud, timeout=self.tiempo_espera, context=contexto) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))

    def _mensaje_error(self, error) -> str:
        if isinstance(error, urllib.error.HTTPError):
            detalle = error.read().decode("utf-8", errors="ignore")[:300]
            print(f"[IA] HTTP {error.code}: {detalle}")
            return self._mensaje_http(error.code)
        if isinstance(getattr(error, "reason", None), (socket.timeout, TimeoutError)):
            return "La IA tardó demasiado en responder."
        return "No hay conexión con el servicio de IA."

    @staticmethod
    def _mensaje_http(codigo: int) -> str:
        if codigo in (401, 403):
            return "La clave de la IA no es válida o no tiene permisos."
        if codigo == 404:
            return "El modelo de IA indicado en la configuración no existe."
        if codigo == 429:
            return "Se alcanzó el límite de uso de la IA. Intenta en unos minutos."
        if codigo >= 500:
            return "El servicio de IA está con problemas. Intenta de nuevo."
        return f"La IA rechazó la solicitud (código {codigo})."


class ProveedorAnthropic(ProveedorIA):
    """Claude, de Anthropic."""

    nombre = "Claude (Anthropic)"
    URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str, modelo: str, max_tokens: int = 700, tiempo_espera: int = 40):
        super().__init__(modelo, max_tokens, tiempo_espera)
        self.api_key = api_key

    def responder(self, sistema: str, mensajes: list[dict]) -> str:
        cuerpo = {"model": self.modelo, "max_tokens": self.max_tokens, "system": sistema, "messages": mensajes}
        datos = self._post_json(self.URL, cuerpo, {"x-api-key": self.api_key,
                                                   "anthropic-version": "2023-06-01"})
        texto = "".join(b.get("text", "") for b in datos.get("content", []) if b.get("type") == "text").strip()
        if not texto:
            raise ErrorIA("La IA respondió vacío.")
        return texto


class ProveedorCompatibleOpenAI(ProveedorIA):
    """Servicios con la API /chat/completions (Ollama, LM Studio, Groq, OpenRouter...)."""

    nombre = "IA compatible"

    def __init__(self, url_base: str, api_key: str, modelo: str, max_tokens: int = 700,
                 tiempo_espera: int = 40):
        super().__init__(modelo, max_tokens, tiempo_espera)
        self.url_base = url_base.rstrip("/")
        self.api_key = api_key

    def responder(self, sistema: str, mensajes: list[dict]) -> str:
        cuerpo = {"model": self.modelo, "max_tokens": self.max_tokens,
                  "messages": [{"role": "system", "content": sistema}] + mensajes}
        cabeceras = {"authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        datos = self._post_json(f"{self.url_base}/chat/completions", cuerpo, cabeceras)
        try:
            texto = (datos["choices"][0]["message"]["content"] or "").strip()
        except (KeyError, IndexError, TypeError) as error:
            raise ErrorIA("La respuesta de la IA llegó con un formato inesperado.") from error
        if not texto:
            raise ErrorIA("La IA respondió vacío.")
        return texto

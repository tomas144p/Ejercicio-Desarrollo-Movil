"""
Proveedor de IA que pasa por el servidor del colegio.

En la versión real la app NO lleva la clave de la IA: le pide la respuesta a la API (``POST /ia/chat``) y es el
servidor el que habla con Claude. Cualquier falla se convierte en ``ErrorIA``, así la conversación sigue con el
tutor de respaldo y muestra una nota (igual que antes).
"""

from __future__ import annotations

from models.datos.conexiones import ErrorConexion
from models.datos.servidor_http import ErrorHTTP
from services.ia.proveedores import ErrorIA, ProveedorIA


class ProveedorServidor(ProveedorIA):
    nombre = "Tutor IA del colegio"

    def __init__(self, gestor_servidor):
        super().__init__("servidor")
        self.gestor = gestor_servidor

    def responder(self, sistema: str, mensajes: list[dict]) -> str:
        servidor = self.gestor.servidor
        if servidor is None:
            raise ErrorIA("No hay conexión con el servidor del colegio.")
        try:
            return servidor.chat_ia(sistema, mensajes)
        except ErrorHTTP as error:
            raise ErrorIA(error.mensaje) from error
        except ErrorConexion as error:
            raise ErrorIA(str(error)) from error

"""
Cliente de la API de Tutor Educa.

``ServidorHTTP`` tiene la misma interfaz que ``ServidorRemoto`` (probar, paquete_para, aplicar_cambio), así el resto
de la app no nota la diferencia. La gran diferencia: ya no hay usuario ni clave de MySQL dentro de la app. La app
solo guarda su sesión (tokens) y le habla a la API por HTTPS.

Usa solo ``urllib`` (incluido en Python), igual que el resto de la app, para no sumar dependencias en Android.
"""

from __future__ import annotations

import ipaddress
import json
import socket
import ssl
import threading
import time
import urllib.error
import urllib.request
from dataclasses import fields
from urllib.parse import urlparse

from models.datos.conexiones import ErrorConexion
from models.datos.servidor import PaqueteDatos
from models.modelos import Usuario
from services.ia.proveedores import contextos_ssl

MARGEN_RENOVACION = 60     # segundos antes de que venza el token en que se pide uno nuevo
HOSTS_LOCALES = {"localhost", "127.0.0.1", "10.0.2.2"}    # 10.0.2.2 = el PC visto desde el emulador de Android


class ErrorHTTP(Exception):
    """La API respondió con un error. ``codigo`` es el estado HTTP; ``mensaje`` ya viene en español."""

    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo, self.mensaje = codigo, mensaje


class ErrorSesion(ErrorConexion):
    """La sesión venció o no existe: hay que volver a ingresar con la contraseña (con conexión)."""


class ErrorCambio(Exception):
    """El servidor rechazó un cambio (no tiene permiso o viene mal formado). Reintentar no sirve."""


def validar_url(url: str) -> str:
    """Solo https. Se acepta http únicamente hacia el propio computador o la red local (desarrollo)."""
    url = (url or "").strip().rstrip("/")
    partes = urlparse(url)
    if partes.scheme not in ("http", "https") or not partes.hostname:
        raise ValueError("La dirección del servidor no es válida. Debe verse así: https://mi-servidor.cl")
    if partes.scheme == "http" and not _es_red_local(partes.hostname):
        raise ValueError("La dirección del servidor debe empezar con https:// (conexión cifrada).")
    return url


def _es_red_local(host: str) -> bool:
    if host in HOSTS_LOCALES:
        return True
    try:
        direccion = ipaddress.ip_address(host)
    except ValueError:
        return False
    return direccion.is_private or direccion.is_loopback


class ServidorHTTP:
    es_demo = False
    requiere_sesion = True      # la sincronización necesita haber ingresado (hay un token)

    def __init__(self, url: str, tiempo_espera: int = 10, nombre: str = "Servidor del colegio"):
        self.url = validar_url(url)
        self.tiempo_espera = tiempo_espera
        self.nombre = nombre
        self._candado = threading.RLock()
        self.usuario_id: int | None = None
        self.token_renovacion = ""
        self._acceso = ""
        self._vence = 0.0

    # --- Sesión -----------------------------------------------------------------------------------
    @property
    def sesion_activa(self) -> bool:
        return bool(self.token_renovacion or self._acceso)

    def cerrar_sesion(self) -> None:
        with self._candado:
            self.usuario_id, self.token_renovacion, self._acceso, self._vence = None, "", "", 0.0

    def restaurar_sesion(self, token_renovacion: str, usuario_id: int) -> None:
        """Retoma una sesión guardada (por ejemplo después de ingresar sin conexión)."""
        with self._candado:
            self.cerrar_sesion()
            self.usuario_id, self.token_renovacion = int(usuario_id), token_renovacion

    def verificar_ingreso(self, correo: str, clave: str) -> tuple[dict | None, str]:
        """(datos de la persona, "") si la contraseña es correcta; (None, mensaje) si no. Sin red: ErrorConexion."""
        try:
            datos = self._pedir("POST", "/login", {"correo": correo, "clave": clave}, con_sesion=False)
        except ErrorHTTP as error:
            if error.codigo in (401, 403, 429):
                return None, error.mensaje
            raise ErrorConexion(error.mensaje) from error
        with self._candado:
            self._acceso, self.token_renovacion = datos["token_acceso"], datos["token_renovacion"]
            self._vence = time.monotonic() + int(datos.get("expira_en", 1800))
            self.usuario_id = int(datos["usuario"]["id"])
        return datos["usuario"], ""

    def _token_vigente(self) -> str:
        with self._candado:
            if self._acceso and time.monotonic() < self._vence - MARGEN_RENOVACION:
                return self._acceso
            if not self.token_renovacion:
                raise ErrorSesion("No has ingresado: inicia sesión con conexión.")
            try:
                datos = self._pedir("POST", "/renovar", {"token_renovacion": self.token_renovacion}, con_sesion=False)
            except ErrorHTTP as error:
                if error.codigo == 401:
                    self.cerrar_sesion()
                    raise ErrorSesion("Tu sesión venció. Vuelve a ingresar con tu contraseña.") from error
                raise ErrorConexion(error.mensaje) from error
            self._acceso = datos["token_acceso"]
            self._vence = time.monotonic() + int(datos.get("expira_en", 1800))
            return self._acceso

    # --- Operaciones del servidor ---------------------------------------------------------------------
    def probar(self) -> bool:
        try:
            self._pedir("GET", "/salud", con_sesion=False, tiempo=4)
            return True
        except (ErrorHTTP, ErrorConexion):
            return False

    def paquete_para(self, usuario: Usuario) -> PaqueteDatos:
        """El servidor decide qué datos le tocan según el token (el parámetro se mantiene por compatibilidad)."""
        try:
            datos = self._pedir("GET", "/paquete")
        except ErrorHTTP as error:
            raise ErrorConexion(error.mensaje) from error
        conocidos = {campo.name for campo in fields(PaqueteDatos)}
        return PaqueteDatos(**{clave: valor for clave, valor in datos.items() if clave in conocidos})

    def aplicar_cambio(self, tipo: str, datos: dict) -> None:
        try:
            self._pedir("POST", "/cambios", {"tipo": tipo, "datos": datos})
        except ErrorHTTP as error:
            if error.codigo >= 500 or error.codigo in (408, 429):
                raise ErrorConexion(error.mensaje) from error      # algo temporal: el cambio sigue en la cola
            raise ErrorCambio(error.mensaje) from error             # rechazado: reintentar no sirve

    def chat_ia(self, sistema: str, mensajes: list[dict]) -> str:
        datos = self._pedir("POST", "/ia/chat", {"sistema": sistema, "mensajes": mensajes}, tiempo=50)
        return datos["texto"]

    # --- HTTP ------------------------------------------------------------------------------------------
    def _pedir(self, metodo: str, ruta: str, cuerpo: dict | None = None, con_sesion: bool = True,
               tiempo: int | None = None) -> dict:
        reintento = True
        while True:
            cabeceras = {"accept": "application/json"}
            if cuerpo is not None:
                cabeceras["content-type"] = "application/json"
            if con_sesion:
                cabeceras["authorization"] = f"Bearer {self._token_vigente()}"
            try:
                return self._enviar(metodo, ruta, cuerpo, cabeceras, tiempo or self.tiempo_espera)
            except ErrorHTTP as error:
                if error.codigo == 401 and con_sesion and reintento:
                    reintento = False
                    with self._candado:
                        self._acceso = ""        # el token ya no sirve: se pide otro con la renovación
                    continue
                if error.codigo == 401 and con_sesion:
                    raise ErrorSesion("Tu sesión venció. Vuelve a ingresar con tu contraseña.") from error
                raise

    def _enviar(self, metodo, ruta, cuerpo, cabeceras, tiempo) -> dict:
        datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
        solicitud = urllib.request.Request(self.url + ruta, data=datos, method=metodo, headers=cabeceras)
        contextos = contextos_ssl() if self.url.startswith("https") else [None]
        for numero, contexto in enumerate(contextos, start=1):
            try:
                with urllib.request.urlopen(solicitud, timeout=tiempo, context=contexto) as respuesta:
                    return json.loads(respuesta.read().decode("utf-8") or "{}")
            except urllib.error.HTTPError as error:
                raise ErrorHTTP(error.code, self._detalle(error)) from error
            except urllib.error.URLError as error:
                if isinstance(getattr(error, "reason", None), ssl.SSLError) and numero < len(contextos):
                    continue        # se prueba con los certificados de "certifi" (pasa en Android)
                raise ErrorConexion("No hay conexión con el servidor del colegio.") from error
            except (socket.timeout, TimeoutError, OSError, ValueError) as error:
                raise ErrorConexion("No hay conexión con el servidor del colegio.") from error
        raise ErrorConexion("No hay conexión con el servidor del colegio.")

    @staticmethod
    def _detalle(error: urllib.error.HTTPError) -> str:
        try:
            detalle = json.loads(error.read().decode("utf-8")).get("detail")
        except (ValueError, OSError):
            detalle = None
        if isinstance(detalle, list):          # error de validación del servidor
            return "El servidor no entendió la solicitud."
        return str(detalle) if detalle else f"El servidor respondió con el error {error.code}."

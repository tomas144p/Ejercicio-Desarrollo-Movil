"""
Registro de errores de la app («crasheos») y su causa. Python puro: no necesita Kivy.

Qué guarda por cada error: fecha y hora, versión de la app, plataforma, pantalla, tipo de error, un mensaje y una traza
resumida (solo archivo, línea y función, sin el código). NO guarda nombres, correos, contraseñas, tokens ni el texto de
los chats: todo se limpia antes de guardarse (``limpiar``), y el servidor lo vuelve a limpiar al recibirlo.

Cómo viaja: se guarda en la cola de sincronización del teléfono (tipo ``error_app``) y se envía al servidor cuando
hay conexión, igual que una prueba o un aviso. Si el error ocurre antes de ingresar, espera en la cola.

Cierres inesperados: al abrir la app se mira cómo terminó la vez anterior. Si quedó «activa» (no se pausó ni se
cerró bien) se registra un «CierreInesperado». Así se detectan también los cierres que el sistema o un fallo nativo
provocan sin que Python alcance a avisar. Es una señal, no una certeza: puede ser también que se la haya forzado a cerrar.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
import threading
import time
import traceback
import uuid
from datetime import datetime

from services.version import VERSION_APP

MAX_MENSAJE = 300
MAX_TRAZA = 1500
MAX_PENDIENTES = 50            # errores esperando en el teléfono; si hay más, se descartan los más antiguos
SEGUNDOS_ENTRE_IGUALES = 60    # el mismo error no se vuelve a guardar durante este tiempo
MAX_ERRORES_EN_BUCLE = 5       # más de estos en la ventana de abajo: la app está en bucle de errores
VENTANA_BUCLE = 30             # segundos
CARPETAS_PROPIAS = ("views", "services", "models", "controladores", "backend", "herramientas")

TIPO_CIERRE = "CierreInesperado"
CLAVE_ESTADO = "sesion_estado"
CLAVE_PANTALLA = "ultima_pantalla"

_PATRONES = (
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "<correo>"),
    (re.compile(r"\beyJ[\w-]{6,}\.[\w-]{6,}\.[\w-]*"), "<token>"),
    (re.compile(r"(?i)\bBearer\s+[\w.~+/=-]+"), "Bearer <token>"),
    (re.compile(r"(?i)\b(clave|contrase[ñn]a|password|passwd|secret|secreto|token|api[_-]?key)\b(\s*[=:]\s*)\S+"),
     r"\1\2<oculto>"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"), "<clave>"),
    (re.compile(r"(?i)(?:[a-z]:\\users\\|/users/|/home/)[^\\/\s'\"]+"), "<inicio>"),
    (re.compile(r"\d[\d.\-]{6,}[\dkK]\b"), "<número>"),          # RUT, teléfonos y otros números largos
    (re.compile(r"\b\d{7,}\b"), "<número>"),
)
_ENTRE_COMILLAS = re.compile(r"""(['"])(.{1,200}?)\1""")
_IDENTIFICADOR = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]{0,40}$")


def limpiar(texto, maximo: int = MAX_MENSAJE) -> str:
    """Quita de un texto lo que podría identificar a una persona o dar acceso, y lo recorta."""
    texto = str(texto or "")
    for patron, reemplazo in _PATRONES:
        texto = patron.sub(reemplazo, texto)
    # Los textos entre comillas que no parecen nombres de campo («curso_id») se ocultan: podrían ser un nombre.
    texto = _ENTRE_COMILLAS.sub(lambda m: m.group(0) if _IDENTIFICADOR.match(m.group(2)) or m.group(2).startswith("<")
                                else f"{m.group(1)}<texto>{m.group(1)}", texto)
    texto = " ".join(texto.split())
    return texto[:maximo]


def _ruta_corta(ruta: str) -> str:
    """«/algo/proyecto/views/docente_screen.py» a «views/docente_screen.py»; otras rutas, solo el nombre del archivo."""
    partes = re.split(r"[\\/]+", ruta)
    for i, parte in enumerate(partes):
        if parte in CARPETAS_PROPIAS:
            return "/".join(partes[i:])
    return partes[-1] if partes else ruta


def resumir_traza(tb) -> tuple[list[str], str]:
    """(líneas «archivo:línea en función», archivo-y-función propios más profundo)."""
    marcos = traceback.extract_tb(tb) if tb is not None else []
    lineas = [f"{_ruta_corta(m.filename)}:{m.lineno} en {m.name}" for m in marcos]
    propios = [m for m in marcos if any(p in re.split(r"[\\/]+", m.filename) for p in CARPETAS_PROPIAS)
               or m.filename.endswith("main.py")]
    ref = (propios or marcos)[-1] if (propios or marcos) else None
    clave = f"{_ruta_corta(ref.filename)} en {ref.name}" if ref else ""
    return lineas, clave


def huella(tipo: str, ubicacion: str) -> str:
    """Identifica una causa: el mismo tipo de error en el mismo lugar da siempre la misma huella (sin el número de línea)."""
    return hashlib.sha1(f"{tipo}|{ubicacion}".encode("utf-8")).hexdigest()[:12]


def ahora_texto() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def construir_registro(exc_type, exc, tb, pantalla: str = "", version: str = VERSION_APP, plataforma: str = "",
                       creado_en: str | None = None) -> dict:
    """El registro listo para guardar y enviar. No incluye nada de la persona."""
    tipo = getattr(exc_type, "__name__", str(exc_type))[:80]
    lineas, ubicacion = resumir_traza(tb)
    return {"codigo": uuid.uuid4().hex[:32], "creado_en": creado_en or ahora_texto(), "version": limpiar(version, 20),
            "plataforma": limpiar(plataforma, 20), "pantalla": limpiar(pantalla, 40), "tipo": tipo,
            "mensaje": limpiar(exc), "traza": "\n".join(lineas[-12:])[:MAX_TRAZA],
            "huella": huella(tipo, ubicacion)}


def registro_cierre_inesperado(ultima_pantalla: str, version: str = VERSION_APP, plataforma: str = "") -> dict:
    mensaje = ("La app se cerró sin registrar un error (puede ser el sistema, falta de memoria, un fallo nativo "
               "o que se la forzó a cerrar).")
    return {"codigo": uuid.uuid4().hex[:32], "creado_en": ahora_texto(), "version": limpiar(version, 20),
            "plataforma": limpiar(plataforma, 20), "pantalla": limpiar(ultima_pantalla, 40), "tipo": TIPO_CIERRE,
            "mensaje": mensaje, "traza": "", "huella": huella(TIPO_CIERRE, ultima_pantalla or "")}


class RegistroErrores:
    """Guarda los errores en el teléfono. Nunca lanza una excepción: registrar un error no debe causar otro."""

    def __init__(self, local, version: str = VERSION_APP, plataforma: str = "", pantalla=lambda: "",
                 reloj=time.monotonic):
        self.local = local
        self.version = version
        self.plataforma = plataforma
        self._pantalla = pantalla
        self._reloj = reloj
        self._recientes: dict[str, float] = {}
        self.repetidos = 0                  # errores que no se guardaron por ser iguales a uno reciente
        self._momentos: list[float] = []   # cuándo ocurrió cada error (para detectar un bucle)
        self._previos = (sys.excepthook, getattr(threading, "excepthook", None))

    # --- errores de Python -----------------------------------------------------------------------------------
    def registrar(self, exc_type, exc, tb) -> dict | None:
        try:
            pantalla = ""
            try:
                pantalla = self._pantalla() or ""
            except Exception:
                pass
            registro = construir_registro(exc_type, exc, tb, pantalla, self.version, self.plataforma)
            ahora = self._reloj()
            self._momentos = [t for t in self._momentos if ahora - t < VENTANA_BUCLE] + [ahora]
            ultimo = self._recientes.get(registro["huella"])
            if ultimo is not None and ahora - ultimo < SEGUNDOS_ENTRE_IGUALES:
                self.repetidos += 1
                return None
            self._recientes[registro["huella"]] = ahora
            self.local.encolar_error(registro, MAX_PENDIENTES)
            return registro
        except Exception:                   # nada de errores al registrar errores
            return None

    def en_bucle(self) -> bool:
        """True si la app está fallando una y otra vez (más de MAX_ERRORES_EN_BUCLE en poco tiempo): conviene cerrarla."""
        ahora = self._reloj()
        return len([t for t in self._momentos if ahora - t < VENTANA_BUCLE]) > MAX_ERRORES_EN_BUCLE

    def instalar_ganchos(self) -> None:
        """Registra también los errores que escapan de cualquier hilo (no solo los de la interfaz)."""
        anterior = sys.excepthook

        def gancho(tipo, valor, tb):
            self.registrar(tipo, valor, tb)
            anterior(tipo, valor, tb)

        sys.excepthook = gancho
        if hasattr(threading, "excepthook"):
            anterior_hilo = threading.excepthook

            def gancho_hilo(args):
                if args.exc_type is not SystemExit:
                    self.registrar(args.exc_type, args.exc_value, args.exc_traceback)
                anterior_hilo(args)

            threading.excepthook = gancho_hilo

    def desinstalar_ganchos(self) -> None:
        sys.excepthook, hilo = self._previos
        if hilo is not None:
            threading.excepthook = hilo

    # --- cierres inesperados ---------------------------------------------------------------------------------
    def recordar_pantalla(self, nombre: str) -> None:
        try:
            self.local.guardar_preferencia(CLAVE_PANTALLA, str(nombre or "")[:40])
        except Exception:
            pass

    def revisar_cierre_anterior(self) -> dict | None:
        """Al abrir la app: si la vez anterior quedó «activa», fue un cierre inesperado."""
        try:
            registro = None
            if self.local.preferencia(CLAVE_ESTADO) == "activa":
                registro = registro_cierre_inesperado(self.local.preferencia(CLAVE_PANTALLA, "") or "",
                                                      self.version, self.plataforma)
                self.local.encolar_error(registro, MAX_PENDIENTES)
            self.local.guardar_preferencia(CLAVE_ESTADO, "activa")
            return registro
        except Exception:
            return None

    def marcar_estado(self, estado: str) -> None:
        """«activa» al usarla, «pausa» al enviarla a segundo plano, «cerrada» al cerrarla bien."""
        try:
            self.local.guardar_preferencia(CLAVE_ESTADO, estado)
        except Exception:
            pass

"""
El panel web de administración (superadmin y admin de colegio).

Es una página estática (HTML + CSS + JavaScript sin librerías externas) que la propia API sirve en ``/panel`` y que
habla con las rutas ``/login``, ``/activar`` y ``/admin/...``. Al ser del mismo origen no necesita CORS y la política
de seguridad (CSP) puede ser muy estricta: solo scripts y estilos propios, sin código ``inline`` y sin conexiones a otros sitios.

Solo se sirven los tres archivos de la lista blanca: no hay forma de pedir otro archivo del servidor.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

CARPETA = Path(__file__).resolve().parent / "panel_web"

ARCHIVOS = {
    "index.html": "text/html; charset=utf-8",
    "panel.css": "text/css; charset=utf-8",
    "panel.js": "text/javascript; charset=utf-8",
}

CABECERAS_SEGURIDAD = {
    "Content-Security-Policy": ("default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
                                "img-src 'self' data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"),
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


def _enviar(nombre: str):
    ruta = CARPETA / nombre
    if nombre not in ARCHIVOS or not ruta.is_file():
        return JSONResponse({"detail": "No encontrado."}, status_code=404)
    return FileResponse(ruta, media_type=ARCHIVOS[nombre], headers=CABECERAS_SEGURIDAD)


def montar_panel(app: FastAPI) -> None:
    @app.get("/panel", include_in_schema=False)
    @app.get("/panel/", include_in_schema=False)
    def panel_inicio():
        return _enviar("index.html")

    @app.get("/panel/{archivo}", include_in_schema=False)
    def panel_archivo(archivo: str):
        return _enviar(archivo)

"""Inicia el servidor:  python -m backend   (variables de entorno: ver backend/.env.ejemplo)."""

import os

import uvicorn

from backend.ajustes import Ajustes, AjustesInvalidos
from backend.app import crear_app


def main() -> None:
    try:
        ajustes = Ajustes.desde_entorno()
    except AjustesInvalidos as error:
        raise SystemExit(f"[backend] Configuración inválida: {error}")
    if not ajustes.es_produccion:
        print("[backend] MODO DESARROLLO: base de demostración y secreto temporal. No usar con datos reales.")
    uvicorn.run(crear_app(ajustes), host=os.environ.get("TUTOR_HOST", "127.0.0.1"),
                port=int(os.environ.get("TUTOR_PUERTO", "8000")), proxy_headers=ajustes.confiar_proxy,
                log_level="info")


if __name__ == "__main__":
    main()

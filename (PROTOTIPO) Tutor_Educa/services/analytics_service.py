
"""
Servicio de analítica local para Tutor Educa.
Registra eventos de uso en formato JSON.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from threading import Lock
from uuid import uuid4

logger = logging.getLogger(__name__)


class AnalyticsService:

    def __init__(self, ruta_archivo):
        self.ruta = Path(ruta_archivo)
        self.lock = Lock()

    def leer_eventos(self):
        """Lee los eventos almacenados."""
        try:
            if not self.ruta.exists():
                return []

            with self.ruta.open("r", encoding="utf-8") as archivo:
                datos = json.load(archivo)

            if not isinstance(datos, list):
                logger.error("Formato incorrecto del archivo de analítica")
                return []

            return datos

        except (OSError, json.JSONDecodeError, UnicodeError):
            logger.exception("Error al leer los eventos")
            return []

    def registrar_evento(self, nombre, propiedades=None):
        """Registra un nuevo evento de uso."""

        evento = {
            "event_id": str(uuid4()),
            "event_name": nombre,
            "timestamp": datetime.now().isoformat(),
            "properties": propiedades or {}
        }

        with self.lock:
            try:
                self.ruta.parent.mkdir(parents=True, exist_ok=True)

                eventos = self.leer_eventos()
                eventos.append(evento)

                temporal = self.ruta.with_suffix(".tmp")

                with temporal.open("w", encoding="utf-8") as archivo:
                    json.dump(
                        eventos,
                        archivo,
                        ensure_ascii=False,
                        indent=4
                    )

                temporal.replace(self.ruta)

                return True

            except (OSError, TypeError, ValueError):
                logger.exception("Error al guardar el evento")
                return False

    def contar_eventos(self):
        """Cuenta cuántas veces ocurrió cada evento."""

        conteo = {}

        for evento in self.leer_eventos():
            nombre = evento.get("event_name", "desconocido")
            conteo[nombre] = conteo.get(nombre, 0) + 1

        return conteo

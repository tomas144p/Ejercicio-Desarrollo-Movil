"""
Monitor del estado de conexión.

La app distingue dos cosas:
- ``en_linea``: el servidor del colegio responde (se puede ingresar en línea
  y sincronizar notas, avances y avisos).
- ``internet_disponible``: hay internet para el chat con IA.

También permite "simular sin conexión" para mostrar el modo offline en una
presentación sin tener que desconectar el computador.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Callable


class MonitorConexion:
    """Revisa periódicamente el servidor e internet y avisa a quien se suscriba."""

    def __init__(self, gestor_servidor, ejecutor, url_internet: str = "https://api.anthropic.com",
                 tiempo_espera: int = 4):
        self.gestor_servidor = gestor_servidor
        self.ejecutor = ejecutor
        self.url_internet = url_internet
        self.tiempo_espera = tiempo_espera
        self.servidor_ok = False
        self.internet_ok = False
        self.forzado_sin_conexion = False
        self.comprobado = False          # True después de la primera revisión
        self._comprobando = False
        self._observadores: list[Callable] = []

    # --- Estado -------------------------------------------------------------
    @property
    def en_linea(self) -> bool:
        return self.servidor_ok and not self.forzado_sin_conexion

    @property
    def internet_disponible(self) -> bool:
        return self.internet_ok and not self.forzado_sin_conexion

    def suscribir(self, funcion: Callable) -> None:
        self._observadores.append(funcion)

    def _notificar(self) -> None:
        for funcion in list(self._observadores):
            funcion(self)

    # --- Acciones -----------------------------------------------------------
    def forzar_sin_conexion(self, valor: bool) -> None:
        """Activa o desactiva la simulación de "sin conexión" (no se guarda)."""
        self.forzado_sin_conexion = valor
        self._notificar()

    def comprobar(self, al_terminar: Callable | None = None) -> None:
        """Revisa el estado en segundo plano; al terminar notifica a los observadores."""
        if self._comprobando:
            return
        self._comprobando = True

        def terminar(resultado):
            self._comprobando = False
            self.servidor_ok, self.internet_ok = resultado
            self.comprobado = True
            self._notificar()
            if al_terminar:
                al_terminar(self)

        def fallar(_error):
            self._comprobando = False

        self.ejecutor.enviar(self._revisar, terminar, fallar)

    def _revisar(self) -> tuple[bool, bool]:
        return self.gestor_servidor.disponible(), self._hay_internet()

    def _hay_internet(self) -> bool:
        """Intenta contactar al servicio de IA. Cualquier respuesta HTTP significa que hay internet."""
        try:
            solicitud = urllib.request.Request(self.url_internet, method="HEAD")
            with urllib.request.urlopen(solicitud, timeout=self.tiempo_espera):
                return True
        except urllib.error.HTTPError:
            return True          # respondió (aunque sea con un error): hay internet
        except (urllib.error.URLError, OSError, ValueError):
            return False

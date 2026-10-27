"""
Cronómetro para medir cuánto tarda una acción (por ejemplo, rendir una prueba).

Usa ``time.perf_counter()``, el reloj de mayor precisión de Python para medir
duraciones. Python puro: no importa Kivy.
"""

import time


class Cronometro:
    """Mide un intervalo: ``iniciar()`` al comenzar y ``detener()`` al terminar."""

    def __init__(self):
        self._inicio = None

    def iniciar(self) -> None:
        self._inicio = time.perf_counter()

    def detener(self) -> float:
        """Devuelve los segundos transcurridos desde ``iniciar()`` (0 si nunca se inició)."""
        if self._inicio is None:
            return 0.0
        segundos = time.perf_counter() - self._inicio
        self._inicio = None
        return segundos

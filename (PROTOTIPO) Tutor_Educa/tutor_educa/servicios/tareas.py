"""
Ejecución de tareas lentas en segundo plano.

Conectarse a MySQL o esperar la respuesta de la IA puede tardar varios
segundos. Si eso se hiciera en el hilo de la interfaz, la app se "congelaría".
``EjecutorEnSegundoPlano`` hace el trabajo en otro hilo y entrega el
resultado de vuelta al hilo de Kivy (con ``Clock``), que es el único que
puede modificar la pantalla.
"""

from __future__ import annotations

import queue
import threading
import traceback
from functools import partial
from typing import Callable


def programador_kivy(funcion: Callable[[], None]) -> None:
    """Ejecuta ``funcion`` en el hilo principal de Kivy en el próximo cuadro."""
    from kivy.clock import Clock
    Clock.schedule_once(lambda _dt: funcion(), 0)


class EjecutorEnSegundoPlano:
    """Cola de trabajos que se ejecutan de a uno en un hilo propio."""

    def __init__(self, nombre: str = "tareas", programador: Callable | None = None):
        self.nombre = nombre
        # Sin programador (por ejemplo en las pruebas) el resultado se entrega en el mismo hilo.
        self._programador = programador or (lambda funcion: funcion())
        self._cola: queue.Queue = queue.Queue()
        self._hilo = threading.Thread(target=self._trabajar, name=nombre, daemon=True)
        self._hilo.start()

    def enviar(self, funcion: Callable, al_terminar: Callable | None = None,
               al_fallar: Callable | None = None) -> None:
        """Agrega un trabajo. ``al_terminar(resultado)`` o ``al_fallar(error)`` se llaman al final."""
        self._cola.put((funcion, al_terminar, al_fallar))

    def _trabajar(self) -> None:
        while True:
            funcion, al_terminar, al_fallar = self._cola.get()
            if funcion is None:
                break
            try:
                resultado = funcion()
            except Exception as error:  # se informa, pero el hilo sigue vivo
                traceback.print_exc()
                if al_fallar:
                    self._programador(partial(al_fallar, error))
                continue
            if al_terminar:
                self._programador(partial(al_terminar, resultado))

    def detener(self) -> None:
        self._cola.put((None, None, None))


class EjecutorInmediato:
    """Misma interfaz, pero ejecuta todo al instante. Útil en pruebas y scripts."""

    def enviar(self, funcion, al_terminar=None, al_fallar=None):
        try:
            resultado = funcion()
        except Exception as error:
            if al_fallar:
                al_fallar(error)
                return
            raise
        if al_terminar:
            al_terminar(resultado)

    def detener(self):
        pass

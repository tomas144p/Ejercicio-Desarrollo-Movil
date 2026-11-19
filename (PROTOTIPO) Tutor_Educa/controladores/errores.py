"""
Errores de la interfaz: se registran (ver services/registro_errores.py) y la app sigue funcionando.

Un error dentro de un botón o de una pantalla, por defecto, cierra la app sin explicación. Aquí se guarda qué
lo causó, se avisa a la persona con un mensaje amable y se sigue. Si la app falla en bucle, se deja que se
cierre: seguir solo empeoraría las cosas.
"""

from __future__ import annotations

from kivy.base import ExceptionHandler, ExceptionManager

MENSAJE = "Algo salió mal. Ya quedó registrado y puedes seguir usando la app."


class ManejadorErrores(ExceptionHandler):
    def __init__(self, app):
        super().__init__()
        self.app = app

    def handle_exception(self, inst):
        registro = self.app.registro_errores
        try:
            registro.registrar(type(inst), inst, inst.__traceback__)
            if registro.en_bucle():
                return ExceptionManager.RAISE          # falla una y otra vez: que se cierre
            notificador = getattr(self.app, "notificador", None)
            if notificador is not None:
                notificador.mostrar(MENSAJE, "error")
        except Exception:                              # el manejador nunca debe provocar otro error
            return ExceptionManager.RAISE
        return ExceptionManager.PASS

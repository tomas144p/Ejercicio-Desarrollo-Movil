"""Opciones de la ventana de Kivy."""

from kivy.config import Config


def configurar_ventana() -> None:
    """Debe llamarse ANTES de crear la ventana (antes de importar kivy.core.window)."""
    Config.set("input", "mouse", "mouse,multitouch_on_demand")  # sin puntos rojos al hacer clic derecho
    Config.set("kivy", "exit_on_escape", "0")                    # Esc / botón atrás lo maneja la app
    Config.set("graphics", "width", "412")                        # tamaño de celular Android típico
    Config.set("graphics", "height", "760")

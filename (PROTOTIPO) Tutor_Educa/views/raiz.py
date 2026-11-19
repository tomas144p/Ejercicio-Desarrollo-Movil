"""Contenedor raíz de la app: las pantallas abajo y una capa encima para los avisos."""

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import ScreenManager


class RaizApp(FloatLayout):
    """Contenedor raíz: las pantallas abajo y una capa encima para las notificaciones."""

    def __init__(self, gestor: ScreenManager, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(gestor)
        self.capa_avisos = FloatLayout()
        self.add_widget(self.capa_avisos)

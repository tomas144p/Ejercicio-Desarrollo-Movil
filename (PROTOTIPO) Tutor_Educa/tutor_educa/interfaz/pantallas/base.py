"""
Clases base de las pantallas.

- ``PantallaBase``: toda pantalla conoce a la app (servicios, usuario, navegación).
- ``PantallaConPestanas``: pantallas de inicio de cada perfil, con barra
  superior, contenido desplazable y barra de pestañas inferior. Cada pestaña
  es un método ``pestana_<clave>(columna)`` que llena la columna.
"""

from __future__ import annotations

from kivy.clock import Clock
from kivy.effects.scroll import ScrollEffect
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from ..componentes import Columna
from ..estilo import Paleta, color
from ..navegacion import BarraInferior, BarraSuperior


def crear_desplazable(padding=None, spacing=None) -> tuple[ScrollView, Columna]:
    """Crea un ScrollView vertical con una columna adentro que crece con su contenido."""
    scroll = ScrollView(do_scroll_x=False, bar_width=dp(4), bar_color=color(Paleta.TINTA_TENUE, 0.5),
                        bar_inactive_color=color(Paleta.TINTA_TENUE, 0.15), effect_cls=ScrollEffect,
                        scroll_type=["bars", "content"])
    columna = Columna(padding=padding if padding is not None else (dp(16), dp(16), dp(16), dp(28)),
                      spacing=spacing if spacing is not None else dp(14))
    scroll.add_widget(columna)
    return scroll, columna


class FondoPapel(BoxLayout):
    """Contenedor vertical con el color de fondo "papel"."""

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(rgba=color(Paleta.PAPEL))
            self._fondo = Rectangle()
        self.bind(pos=self._dibujar, size=self._dibujar)

    def _dibujar(self, *_):
        self._fondo.pos, self._fondo.size = self.pos, self.size


class PantallaBase(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app

    @property
    def usuario(self):
        return self.app.usuario

    @property
    def acento(self) -> str:
        if self.app.usuario is None:
            return Paleta.AZUL
        return Paleta.POR_ROL[self.app.usuario.rol][0]

    def preparar(self, **parametros) -> None:
        """Recibe los datos con que se abre la pantalla (por ejemplo, qué tema mostrar)."""

    def on_pre_enter(self, *args):
        self.actualizar()

    def actualizar(self) -> None:
        """Vuelve a dibujar la pantalla con datos frescos."""

    def al_cambiar_datos(self) -> None:
        """La app avisa que hubo sincronización o cambió la conexión."""
        self.actualizar()


class PantallaConPestanas(PantallaBase):
    PESTANAS: list[tuple[str, str, str]] = []
    ACENTO = Paleta.AZUL

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.pestana = self.PESTANAS[0][0]
        self._posiciones: dict[str, float] = {}
        self._scroll = None
        self._pestana_dibujada = None
        raiz = FondoPapel()
        self._zona_superior = BoxLayout(size_hint_y=None, height=dp(64))
        self._zona_contenido = BoxLayout()
        self.barra_inferior = BarraInferior(self.PESTANAS, self.ACENTO, self.cambiar_pestana)
        for widget in (self._zona_superior, self._zona_contenido, self.barra_inferior):
            raiz.add_widget(widget)
        self.add_widget(raiz)

    # Cada perfil define su título y subtítulo
    def titulo(self) -> str:
        return ""

    def subtitulo(self) -> str:
        return ""

    def reiniciar(self) -> None:
        """Se llama al iniciar sesión: vuelve a la primera pestaña."""
        self.pestana = self.PESTANAS[0][0]
        self._posiciones.clear()
        self._scroll = None

    def actualizar(self) -> None:
        if self.app.usuario is None:
            return
        self._zona_superior.clear_widgets()
        self._zona_superior.add_widget(BarraSuperior(self.app, self.titulo(), self.subtitulo(), acento=self.ACENTO))
        self.dibujar_pestana(conservar_posicion=True)

    def dibujar_pestana(self, conservar_posicion: bool = True) -> None:
        if self._scroll is not None and self._pestana_dibujada:
            self._posiciones[self._pestana_dibujada] = self._scroll.scroll_y
        self._zona_contenido.clear_widgets()
        scroll, columna = crear_desplazable()
        getattr(self, f"pestana_{self.pestana}")(columna)
        self._zona_contenido.add_widget(scroll)
        self._scroll, self._pestana_dibujada = scroll, self.pestana
        if conservar_posicion and self.pestana in self._posiciones:
            posicion = self._posiciones[self.pestana]
            Clock.schedule_once(lambda _dt: setattr(scroll, "scroll_y", posicion), 0.05)
        self.barra_inferior.activar(self.pestana)
        self.actualizar_insignias()

    def actualizar_insignias(self) -> None:
        """Las subclases pueden mostrar contadores en las pestañas."""

    def cambiar_pestana(self, clave: str) -> None:
        if self._scroll is not None and self._pestana_dibujada:
            self._posiciones[self._pestana_dibujada] = self._scroll.scroll_y
        self.pestana = clave
        self.dibujar_pestana(conservar_posicion=False)

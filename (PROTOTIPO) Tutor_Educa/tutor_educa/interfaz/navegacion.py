"""
Barras de navegación: barra superior (con el estado de conexión), barra de
pestañas inferior y control segmentado (Aprende / Ejemplos / Prueba).
"""

from __future__ import annotations

from functools import partial

from kivy.graphics import Color, Ellipse, Rectangle
from kivy.metrics import dp, sp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.utils import escape_markup

from .componentes import TRANSPARENTE, Avatar, BotonIcono, ConFondo, Icono, InsigniaIcono
from .estilo import Iconos, Paleta, Tipografia, color


class _ConLinea:
    """Mezcla: dibuja una línea fina arriba o abajo del widget."""

    def _agregar_linea(self, arriba: bool):
        self._linea_arriba = arriba
        with self.canvas.after:
            Color(rgba=color(Paleta.LINEA))
            self._linea = Rectangle()
        self.bind(pos=self._mover_linea, size=self._mover_linea)

    def _mover_linea(self, *_):
        y = self.top - dp(1) if self._linea_arriba else self.y
        self._linea.pos, self._linea.size = (self.x, y), (self.width, dp(1))


class PildoraConexion(ButtonBehavior, ConFondo, BoxLayout):
    """Indicador "En línea / Sin conexión / Sincronizando". Al tocarlo muestra el detalle."""

    def __init__(self, app, **kwargs):
        super().__init__(orientation="horizontal", size_hint=(None, None), height=dp(30),
                         padding=(dp(10), 0), spacing=dp(5), radio=dp(15), **kwargs)
        self.app = app
        self._icono = Icono("wifi", tamano=14, size=(dp(16), dp(16)), pos_hint={"center_y": 0.5})
        self._texto = Label(font_name=Tipografia.MEDIA, font_size=sp(12), size_hint_x=None)
        self._texto.bind(texture_size=self._ajustar)
        self.add_widget(self._icono)
        self.add_widget(self._texto)
        app.bind(en_linea=self.actualizar, sincronizando=self.actualizar, pendientes=self.actualizar,
                 conexion_revisada=self.actualizar)
        self.bind(on_release=lambda *_: app.mostrar_estado_conexion())
        self.actualizar()

    def _ajustar(self, *_):
        self._texto.width = self._texto.texture_size[0]
        self.width = dp(20) + dp(16) + dp(5) + self._texto.width

    def actualizar(self, *_):
        app = self.app
        if app.sincronizando:
            icono, texto, tinta = "refresh-cw", "Sincronizando", Paleta.AZUL
        elif not app.conexion_revisada:
            icono, texto, tinta = "clock", "Conectando", Paleta.TINTA_SUAVE
        elif app.en_linea:
            icono, texto, tinta = "wifi", "En línea", Paleta.VERDE
        else:
            pendientes = f" ({app.pendientes})" if app.pendientes else ""
            icono, texto, tinta = "wifi-off", "Sin conexión" + pendientes, Paleta.AMBAR
        self._icono.cambiar(icono)
        self._icono.color = self._texto.color = color(tinta)
        self._texto.text = texto
        self.color_fondo = color(Paleta.suave(tinta))


class BarraSuperior(_ConLinea, ConFondo, BoxLayout):
    """Barra de arriba: avatar o botón volver, título, estado de conexión y salir."""

    def __init__(self, app, titulo: str, subtitulo: str = "", acento=Paleta.AZUL, volver: bool = False,
                 mostrar_salir: bool = True, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(64),
                         padding=(dp(10), dp(8), dp(6), dp(8)), spacing=dp(10),
                         color_fondo=color(Paleta.SUPERFICIE), radio=0, **kwargs)
        self._agregar_linea(arriba=False)
        centro = {"center_y": 0.5}
        if volver:
            self.add_widget(BotonIcono("arrow-left", al_presionar=app.volver, pos_hint=centro))
        elif app.usuario is not None:
            self.add_widget(Avatar(app.usuario.iniciales, tinta=acento, lado=40, pos_hint=centro))
        textos = BoxLayout(orientation="vertical", padding=(0, dp(3)))
        textos.add_widget(self._linea_texto(titulo, 16.5, Tipografia.SEMI, Paleta.TINTA,
                                            "bottom" if subtitulo else "middle"))
        if subtitulo:
            textos.add_widget(self._linea_texto(subtitulo, 12.5, Tipografia.NORMAL, Paleta.TINTA_SUAVE, "top"))
        self.add_widget(textos)
        self.add_widget(PildoraConexion(app, pos_hint=centro))
        if mostrar_salir:
            self.add_widget(BotonIcono("log-out", al_presionar=app.cerrar_sesion, tinta=Paleta.TINTA_SUAVE,
                                       lado=40, tamano=19, pos_hint=centro))

    @staticmethod
    def _linea_texto(texto, tamano, fuente, tinta, valign) -> Label:
        etiqueta = Label(text=texto, font_name=fuente, font_size=sp(tamano), color=color(tinta), halign="left",
                         valign=valign, shorten=True, shorten_from="right")
        etiqueta.bind(size=lambda w, s: setattr(w, "text_size", s))
        return etiqueta


class BotonPestana(ButtonBehavior, BoxLayout):
    """Una pestaña de la barra inferior (ícono + texto + contador opcional)."""

    def __init__(self, texto: str, icono: str, acento, al_presionar):
        super().__init__(orientation="vertical", padding=(0, dp(6), 0, dp(4)), spacing=dp(3))
        self.acento = acento
        # Zona simple (no es un layout): el ícono y el contador se ubican a mano.
        self._zona = Widget(size_hint_y=None, height=dp(30))
        self._pildora = InsigniaIcono(icono, tinta=Paleta.TINTA_TENUE, fondo=Paleta.SUPERFICIE, lado=30,
                                      tamano_icono=19)
        self._pildora.size = (dp(58), dp(30))
        self._pildora.radio = dp(15)
        self._insignia = Label(font_name=Tipografia.SEMI, font_size=sp(10), color=color("#FFFFFF"),
                               size_hint=(None, None), size=(dp(18), dp(18)), opacity=0)
        with self._insignia.canvas.before:
            Color(rgba=color(Paleta.ROJO))
            self._circulo = Ellipse(size=self._insignia.size)
        self._zona.add_widget(self._pildora)
        self._zona.add_widget(self._insignia)
        self._zona.bind(pos=self._ubicar, size=self._ubicar)
        self._etiqueta = Label(text=texto, font_name=Tipografia.MEDIA, font_size=sp(11.5),
                               color=color(Paleta.TINTA_TENUE), size_hint_y=None, height=dp(16))
        self.add_widget(self._zona)
        self.add_widget(self._etiqueta)
        self.bind(on_release=lambda *_: al_presionar())

    def _ubicar(self, *_):
        self._pildora.center = self._zona.center
        self._insignia.pos = (self._pildora.right - dp(14), self._pildora.top - dp(12))
        self._circulo.pos = self._insignia.pos

    def activar(self, activo: bool) -> None:
        tinta = self.acento if activo else Paleta.TINTA_TENUE
        self._pildora.color = color(tinta)
        self._pildora.color_fondo = color(Paleta.suave(self.acento)) if activo else TRANSPARENTE
        self._etiqueta.color = color(tinta if activo else Paleta.TINTA_SUAVE)
        self._etiqueta.font_name = Tipografia.SEMI if activo else Tipografia.MEDIA

    def insignia(self, cantidad: int) -> None:
        self._insignia.text = str(cantidad) if cantidad < 10 else "9+"
        self._insignia.opacity = 1 if cantidad else 0
        self._ubicar()


class BarraInferior(_ConLinea, ConFondo, BoxLayout):
    """Barra de pestañas inferior (como en las apps de celular)."""

    def __init__(self, pestanas, acento, al_cambiar, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(66), padding=(dp(4), 0),
                         color_fondo=color(Paleta.SUPERFICIE), radio=0, **kwargs)
        self._agregar_linea(arriba=True)
        self.botones = {}
        for clave, texto, icono in pestanas:
            boton = BotonPestana(texto, icono, acento, partial(al_cambiar, clave))
            self.botones[clave] = boton
            self.add_widget(boton)

    def activar(self, clave: str) -> None:
        for nombre, boton in self.botones.items():
            boton.activar(nombre == clave)

    def insignia(self, clave: str, cantidad: int) -> None:
        if clave in self.botones:
            self.botones[clave].insignia(cantidad)


class _Segmento(ButtonBehavior, ConFondo, Label):
    pass


class ControlSegmentado(ConFondo, BoxLayout):
    """Selector de secciones con forma de interruptor de varias posiciones."""

    def __init__(self, opciones, seleccion: str, acento, al_cambiar, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(46), padding=dp(4),
                         spacing=dp(4), color_fondo=color(Paleta.GRIS_SUAVE), radio=dp(13), **kwargs)
        self.acento = acento
        self._segmentos = {}
        for clave, texto, icono in opciones:
            segmento = _Segmento(text=f"{Iconos.markup(icono, 15)}  {escape_markup(texto)}", markup=True,
                                 font_size=sp(13.5), radio=dp(10))
            segmento.bind(on_release=lambda _w, c=clave: al_cambiar(c))
            self._segmentos[clave] = segmento
            self.add_widget(segmento)
        self.seleccionar(seleccion)

    def seleccionar(self, clave: str) -> None:
        for nombre, segmento in self._segmentos.items():
            activo = nombre == clave
            segmento.color_fondo = color(Paleta.SUPERFICIE) if activo else TRANSPARENTE
            segmento.color_borde = color(Paleta.LINEA) if activo else TRANSPARENTE
            segmento.color = color(self.acento if activo else Paleta.TINTA_SUAVE)
            segmento.font_name = Tipografia.SEMI if activo else Tipografia.MEDIA

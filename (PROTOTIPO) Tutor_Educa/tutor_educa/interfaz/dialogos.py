"""
Diálogos y notificaciones.

El prototipo anterior usaba el ``Popup`` estándar de Kivy: fondo oscuro,
alto fijo y texto sin salto de línea, por eso los párrafos se salían del
recuadro. ``Dialogo`` es una tarjeta blanca cuyo alto se adapta al texto y
que se puede desplazar si el mensaje es muy largo.
"""

from __future__ import annotations

from functools import partial

from kivy.animation import Animation
from kivy.core.window import Window
from kivy.effects.scroll import ScrollEffect
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView

from .componentes import TRANSPARENTE, Boton, Columna, ConFondo, Fila, Icono, InsigniaIcono, Superficie, Texto
from .estilo import Paleta, Tipografia, color


class Dialogo(ModalView):
    """
    Ventana modal con título, texto, contenido opcional y botones.

    ``botones`` es una lista de tuplas (texto, acción, variante). Si la acción
    devuelve False, el diálogo no se cierra (útil para validar formularios).
    """

    def __init__(self, titulo: str, texto: str = "", contenido=None, botones=None, icono: str = "",
                 tinta=Paleta.AZUL, cerrar_al_tocar_fuera: bool = True, **kwargs):
        super().__init__(size_hint=(None, None), background="", background_color=TRANSPARENTE,
                         overlay_color=[0.07, 0.1, 0.18, 0.5], auto_dismiss=cerrar_al_tocar_fuera, **kwargs)
        self.width = min(Window.width - dp(28), dp(440))
        self.tarjeta = Superficie(padding=dp(20), spacing=dp(14), radio=dp(20), color_borde=TRANSPARENTE)

        cabecera = Fila(spacing=dp(12))
        if icono:
            cabecera.add_widget(InsigniaIcono(icono, tinta=tinta, lado=40, pos_hint={"center_y": 0.5}))
        cabecera.add_widget(Texto(titulo, tamano=18, fuente=Tipografia.SEMI, pos_hint={"center_y": 0.5}))
        self.tarjeta.add_widget(cabecera)

        self.cuerpo = Columna(spacing=dp(12))
        if texto:
            self.cuerpo.add_widget(Texto(texto, tamano=14.5, color_texto=Paleta.TINTA_SUAVE, interlineado=1.25))
        if contenido is not None:
            self.cuerpo.add_widget(contenido)
        self.desplazable = ScrollView(size_hint_y=None, do_scroll_x=False, effect_cls=ScrollEffect,
                                      bar_width=dp(3))
        self.desplazable.add_widget(self.cuerpo)
        self.tarjeta.add_widget(self.desplazable)

        botones = [("Entendido", None, "primario")] if botones is None else botones
        if botones:
            fila = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
            for texto_boton, accion, variante in botones:
                fila.add_widget(Boton(texto_boton, variante=variante, acento=tinta,
                                      al_presionar=partial(self._presionar, accion)))
            self.tarjeta.add_widget(fila)
        self.add_widget(self.tarjeta)
        self.cuerpo.bind(height=self._ajustar)
        self.tarjeta.bind(height=self._ajustar_modal)
        self._ajustar()

    def _ajustar(self, *_):
        maximo = Window.height * 0.86 - dp(170)
        self.desplazable.height = min(self.cuerpo.height, max(dp(90), maximo))

    def _ajustar_modal(self, *_):
        self.height = self.tarjeta.height

    def _presionar(self, accion):
        if accion is not None and accion() is False:
            return
        self.dismiss()

    # --- Atajos -------------------------------------------------------------
    @classmethod
    def informar(cls, titulo: str, texto: str, icono: str = "info", tinta=Paleta.AZUL) -> "Dialogo":
        dialogo = cls(titulo, texto, icono=icono, tinta=tinta)
        dialogo.open()
        return dialogo

    @classmethod
    def confirmar(cls, titulo: str, texto: str, texto_confirmar: str, al_confirmar, peligro: bool = False,
                  icono: str = "circle-help", tinta=Paleta.AZUL) -> "Dialogo":
        dialogo = cls(titulo, texto, icono=icono, tinta=Paleta.ROJO if peligro else tinta,
                      botones=[("Cancelar", None, "contorno"),
                               (texto_confirmar, al_confirmar, "peligro" if peligro else "primario")])
        dialogo.open()
        return dialogo


class _Tostada(ConFondo, BoxLayout):
    def __init__(self, texto: str, tinta: str, icono: str):
        super().__init__(orientation="horizontal", size_hint=(None, None), padding=(dp(16), dp(12)),
                         spacing=dp(10), color_fondo=color(tinta), radio=dp(14))
        self.width = min(Window.width - dp(32), dp(400))
        self.add_widget(Icono(icono, tamano=18, color_icono="#FFFFFF", pos_hint={"center_y": 0.5}))
        self.add_widget(Texto(texto, tamano=14, color_texto="#FFFFFF", pos_hint={"center_y": 0.5}))
        self.bind(minimum_height=self.setter("height"))


class Notificador:
    """Mensajes cortos que aparecen abajo y se van solos ("tostadas")."""

    ESTILOS = {"info": (Paleta.TINTA, "info"), "exito": (Paleta.VERDE, "circle-check"),
               "error": (Paleta.ROJO, "circle-x"), "aviso": (Paleta.AMBAR, "wifi-off")}

    def __init__(self, capa):
        self.capa = capa
        self._actual = None

    def mostrar(self, texto: str, tipo: str = "info", duracion: float = 3.0) -> None:
        if self._actual is not None:
            Animation.cancel_all(self._actual)
            self.capa.remove_widget(self._actual)
        tinta, icono = self.ESTILOS.get(tipo, self.ESTILOS["info"])
        tostada = _Tostada(texto, tinta, icono)
        tostada.pos_hint = {"center_x": 0.5, "y": 0.12}
        tostada.opacity = 0
        self.capa.add_widget(tostada)
        self._actual = tostada
        animacion = Animation(opacity=1, d=0.2) + Animation(d=duracion) + Animation(opacity=0, d=0.3)
        animacion.bind(on_complete=lambda *_: self._quitar(tostada))
        animacion.start(tostada)

    def _quitar(self, tostada) -> None:
        if tostada.parent is not None:
            self.capa.remove_widget(tostada)
        if self._actual is tostada:
            self._actual = None

"""
Componentes visuales reutilizables (botones, campos, tarjetas, etc.).

Todos heredan de widgets de Kivy y agregan estilo propio. Resuelven los
problemas del prototipo anterior:
- ``Texto`` ajusta el salto de línea y su alto automáticamente: los párrafos
  ya no se salen de los recuadros.
- ``Boton`` tiene un estado desactivado legible (antes el texto desaparecía).
- Los íconos son de la fuente Lucide (antes eran emojis que no se veían).
"""

from __future__ import annotations

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, InstructionGroup, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, ColorProperty, NumericProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import escape_markup

from .estilo import FormatoTexto, Iconos, Paleta, Tipografia, color, oscurecer

TRANSPARENTE = [0, 0, 0, 0]


def a_color(valor):
    """Acepta "#RRGGBB" o una lista rgba."""
    return color(valor) if isinstance(valor, str) else valor


# ---------------------------------------------------------------------------
# Mezclas (mixins) de dibujo
# ---------------------------------------------------------------------------
class ConFondo:
    """Mezcla que dibuja un fondo redondeado y un borde detrás del widget."""

    color_fondo = ColorProperty(TRANSPARENTE)
    color_borde = ColorProperty(TRANSPARENTE)
    radio = NumericProperty(dp(14))
    grosor_borde = NumericProperty(dp(1))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            self._pintura_fondo = Color(rgba=self.color_fondo)
            self._figura_fondo = RoundedRectangle(pos=self.pos, size=self.size)
            self._pintura_borde = Color(rgba=self.color_borde)
            self._figura_borde = Line(width=self.grosor_borde)
        self.bind(pos=self._redibujar_fondo, size=self._redibujar_fondo, radio=self._redibujar_fondo,
                  grosor_borde=self._redibujar_fondo, color_fondo=self._pintar_fondo,
                  color_borde=self._pintar_fondo)
        self._redibujar_fondo()

    def _pintar_fondo(self, *_):
        self._pintura_fondo.rgba = self.color_fondo
        self._pintura_borde.rgba = self.color_borde

    def _redibujar_fondo(self, *_):
        radio = max(0.0, min(self.radio, self.width / 2, self.height / 2))
        self._figura_fondo.pos, self._figura_fondo.size = self.pos, self.size
        self._figura_fondo.radius = [radio]
        self._figura_borde.width = self.grosor_borde
        if self.width > 4 and self.height > 4:
            if radio >= 1:
                self._figura_borde.rounded_rectangle = (self.x, self.y, self.width, self.height, radio)
            else:
                self._figura_borde.rectangle = (self.x, self.y, self.width, self.height)


class ConCuadricula:
    """Mezcla que dibuja papel cuadriculado (y opcionalmente el margen rojo del cuaderno)."""

    paso_cuadricula = NumericProperty(dp(18))
    margen_rojo = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._grupo_cuadricula = InstructionGroup()
        self.canvas.before.add(self._grupo_cuadricula)
        self.bind(pos=self._dibujar_cuadricula, size=self._dibujar_cuadricula)

    def _dibujar_cuadricula(self, *_):
        grupo, paso = self._grupo_cuadricula, self.paso_cuadricula
        grupo.clear()
        grupo.add(Color(rgba=color(Paleta.CUADRICULA)))
        x = self.x + paso
        while x < self.right - 2:
            grupo.add(Line(points=[x, self.y + 2, x, self.top - 2], width=1))
            x += paso
        y = self.top - paso
        while y > self.y + 2:
            grupo.add(Line(points=[self.x + 2, y, self.right - 2, y], width=1))
            y -= paso
        if self.margen_rojo:
            grupo.add(Color(rgba=color(Paleta.MARGEN)))
            xm = self.x + self.margen_rojo
            grupo.add(Line(points=[xm, self.y + 2, xm, self.top - 2], width=dp(1.1)))


# ---------------------------------------------------------------------------
# Textos e íconos
# ---------------------------------------------------------------------------
class Texto(Label):
    """
    Etiqueta que hace salto de línea automático y ajusta su alto al contenido.

    Por defecto el texto se escapa (es seguro mostrar lo que escribe el
    usuario) y se interpretan  5^3  y  **negrita**.
    """

    def __init__(self, texto: str = "", tamano: float = Tipografia.CUERPO, fuente: str = Tipografia.NORMAL,
                 color_texto=Paleta.TINTA, alinear: str = "left", interlineado: float = 1.15,
                 markup_listo: bool = False, cuaderno: bool = False, **kwargs):
        self.tamano = tamano
        self._cuaderno = cuaderno
        contenido = texto if markup_listo else FormatoTexto.enriquecer(texto, tamano, cuaderno)
        kwargs.setdefault("size_hint_y", None)
        super().__init__(text=contenido, markup=True, font_size=sp(tamano), font_name=fuente,
                         color=a_color(color_texto), halign=alinear, valign="top",
                         line_height=interlineado, **kwargs)
        self.bind(width=self._ajustar_ancho, texture_size=self._ajustar_alto)
        self._ajustar_ancho()
        self._ajustar_alto()

    def cambiar(self, texto: str) -> None:
        self.text = FormatoTexto.enriquecer(texto, self.tamano, self._cuaderno)

    def _ajustar_ancho(self, *_):
        self.text_size = (self.width, None)

    def _ajustar_alto(self, *_):
        self.height = self.texture_size[1]


class Icono(Label):
    def __init__(self, nombre: str, tamano: float = 20, color_icono=Paleta.TINTA, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(tamano + 6), dp(tamano + 6)))
        super().__init__(text=Iconos.caracter(nombre), font_name=Tipografia.ICONOS, font_size=sp(tamano),
                         color=a_color(color_icono), **kwargs)

    def cambiar(self, nombre: str) -> None:
        self.text = Iconos.caracter(nombre)


class InsigniaIcono(ConFondo, Label):
    """Ícono dentro de un cuadrado redondeado de color suave."""

    def __init__(self, icono: str, tinta=Paleta.AZUL, fondo=None, lado: float = 40,
                 tamano_icono: float = 20, redonda: bool = False, **kwargs):
        fondo = fondo or (Paleta.suave(tinta) if isinstance(tinta, str) else Paleta.GRIS_SUAVE)
        super().__init__(text=Iconos.caracter(icono), font_name=Tipografia.ICONOS, font_size=sp(tamano_icono),
                         color=a_color(tinta), color_fondo=a_color(fondo),
                         radio=dp(lado / 2) if redonda else dp(lado * 0.3),
                         size_hint=(None, None), size=(dp(lado), dp(lado)), **kwargs)


class Avatar(ConFondo, Label):
    """Círculo con las iniciales de una persona."""

    def __init__(self, iniciales: str, tinta=Paleta.AZUL, fondo=None, lado: float = 40, **kwargs):
        super().__init__(text=iniciales, font_name=Tipografia.SEMI, font_size=sp(lado * 0.36),
                         color=a_color(tinta), color_fondo=a_color(fondo or Paleta.suave(tinta)),
                         radio=dp(lado / 2), size_hint=(None, None), size=(dp(lado), dp(lado)), **kwargs)


class Etiqueta(ConFondo, Label):
    """Pastilla pequeña de estado ("En curso", "Logrado", "Evaluación"...)."""

    def __init__(self, texto: str, tinta=Paleta.AZUL, fondo=None, icono: str = "", tamano: float = 11.5,
                 **kwargs):
        contenido = (Iconos.markup(icono, tamano + 1) + " " if icono else "") + escape_markup(texto)
        super().__init__(text=contenido, markup=True, font_name=Tipografia.SEMI, font_size=sp(tamano),
                         color=a_color(tinta), color_fondo=a_color(fondo or Paleta.suave(tinta)),
                         radio=dp(11), size_hint=(None, None), height=dp(24), padding=(dp(10), 0), **kwargs)
        self.bind(texture_size=self._ajustar)

    def _ajustar(self, *_):
        self.width = self.texture_size[0]


class TextoDestacado(Label):
    """Texto con marcador amarillo detrás (como subrayado con destacador)."""

    avance = NumericProperty(1.0)   # 0 a 1: permite animar el trazo del destacador

    def __init__(self, texto: str, tamano: float = 22, fuente: str = Tipografia.CUADERNO,
                 color_texto=Paleta.TINTA_CUADERNO, **kwargs):
        super().__init__(text=FormatoTexto.enriquecer(texto, tamano, cuaderno=True), markup=True,
                         font_name=fuente, font_size=sp(tamano), color=a_color(color_texto),
                         size_hint=(None, None), padding=(dp(8), dp(2)), **kwargs)
        with self.canvas.before:
            Color(rgba=color(Paleta.DESTACADOR, 0.9))
            self._marca = RoundedRectangle(radius=[dp(3)])
        self.bind(texture_size=self._ajustar, pos=self._dibujar, size=self._dibujar, avance=self._dibujar)

    def _ajustar(self, *_):
        self.size = self.texture_size

    def _dibujar(self, *_):
        self._marca.pos = (self.x, self.y + self.height * 0.1)
        self._marca.size = (self.width * self.avance, self.height * 0.55)


# ---------------------------------------------------------------------------
# Botones y controles
# ---------------------------------------------------------------------------
class Boton(ButtonBehavior, ConFondo, Label):
    """
    Botón con variantes: "primario", "secundario", "contorno", "fantasma" y "peligro".
    ``acento`` define el color principal (cambia según el perfil).
    """

    cargando = BooleanProperty(False)

    def __init__(self, texto: str = "", icono: str = "", variante: str = "primario", acento=Paleta.AZUL,
                 al_presionar=None, alto: float = 48, tamano: float = 15, **kwargs):
        self.texto_base, self.icono, self.variante = texto, icono, variante
        self.acento, self.tamano = acento, tamano
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(alto))
        super().__init__(markup=True, font_name=Tipografia.SEMI, font_size=sp(tamano), halign="center",
                         valign="middle", radio=dp(12), **kwargs)
        self.disabled_color = color(Paleta.TINTA_TENUE)
        self.bind(size=self._ajustar_texto, state=self._aplicar_estilo, disabled=self._aplicar_estilo,
                  cargando=self._al_cargar)
        if al_presionar:
            self.bind(on_release=lambda *_: al_presionar())
        self._actualizar_texto()
        self._aplicar_estilo()

    def cambiar_texto(self, texto: str, icono: str | None = None) -> None:
        self.texto_base = texto
        if icono is not None:
            self.icono = icono
        self._actualizar_texto()

    def _ajustar_texto(self, *_):
        self.text_size = (max(self.width - dp(20), 10), None)

    def _al_cargar(self, *_):
        self.disabled = self.cargando
        self._actualizar_texto()

    def _actualizar_texto(self):
        texto = "Un momento…" if self.cargando else self.texto_base
        icono = Iconos.markup(self.icono, self.tamano + 3) + "  " if (self.icono and not self.cargando) else ""
        self.text = icono + escape_markup(texto)

    def _colores(self):
        suave = Paleta.suave(self.acento)
        return {"primario": (self.acento, "#FFFFFF", None),
                "secundario": (suave, self.acento, None),
                "contorno": (Paleta.SUPERFICIE, Paleta.TINTA, Paleta.LINEA),
                "fantasma": (None, self.acento, None),
                "peligro": (Paleta.ROJO_SUAVE, Paleta.ROJO, None)}[self.variante]

    def _aplicar_estilo(self, *_):
        fondo, tinta, borde = self._colores()
        if self.disabled:
            self.color_fondo = color(Paleta.GRIS_SUAVE) if fondo else TRANSPARENTE
            self.color_borde = TRANSPARENTE
            return
        presionado = self.state == "down"
        if fondo:
            self.color_fondo = oscurecer(fondo, 0.9) if presionado else color(fondo)
        else:
            self.color_fondo = color(Paleta.suave(self.acento)) if presionado else TRANSPARENTE
        self.color = color(tinta)
        self.color_borde = color(borde) if borde else TRANSPARENTE


class BotonIcono(ButtonBehavior, ConFondo, Label):
    """Botón redondo que solo muestra un ícono."""

    def __init__(self, icono: str, al_presionar=None, tinta=Paleta.TINTA, fondo=None, lado: float = 44,
                 tamano: float = 20, **kwargs):
        self._fondo = fondo
        kwargs.setdefault("size_hint", (None, None))
        super().__init__(text=Iconos.caracter(icono), font_name=Tipografia.ICONOS, font_size=sp(tamano),
                         color=a_color(tinta), size=(dp(lado), dp(lado)), radio=dp(lado / 2), **kwargs)
        self.disabled_color = color(Paleta.TINTA_TENUE)
        self.bind(state=self._estilo, disabled=self._estilo)
        if al_presionar:
            self.bind(on_release=lambda *_: al_presionar())
        self._estilo()

    def cambiar_icono(self, icono: str) -> None:
        self.text = Iconos.caracter(icono)

    def _estilo(self, *_):
        if self._fondo:
            base = Paleta.LINEA if self.disabled else self._fondo
            self.color_fondo = oscurecer(base, 0.9) if self.state == "down" else color(base)
        else:
            self.color_fondo = color(Paleta.LINEA, 0.7) if self.state == "down" else TRANSPARENTE


class Chip(ButtonBehavior, ConFondo, Label):
    """Opción seleccionable con forma de pastilla (filtros, respuestas rápidas)."""

    seleccionado = BooleanProperty(False)

    def __init__(self, texto: str, seleccionado: bool = False, acento=Paleta.AZUL, al_presionar=None,
                 icono: str = "", **kwargs):
        self.acento = acento
        contenido = (Iconos.markup(icono, 15) + "  " if icono else "") + escape_markup(texto)
        super().__init__(text=contenido, markup=True, font_name=Tipografia.MEDIA, font_size=sp(13.5),
                         size_hint=(None, None), height=dp(36), padding=(dp(14), 0), radio=dp(18),
                         seleccionado=seleccionado, **kwargs)
        self.bind(texture_size=self._ajustar, seleccionado=self._estilo, state=self._estilo)
        if al_presionar:
            self.bind(on_release=lambda *_: al_presionar())
        self._estilo()

    def _ajustar(self, *_):
        self.width = self.texture_size[0]

    def _estilo(self, *_):
        if self.seleccionado:
            self.color_fondo, self.color_borde, self.color = color(self.acento), TRANSPARENTE, color("#FFFFFF")
        else:
            fondo = Paleta.GRIS_SUAVE if self.state == "down" else Paleta.SUPERFICIE
            self.color_fondo, self.color_borde, self.color = color(fondo), color(Paleta.LINEA), color(Paleta.TINTA)


class CampoTexto(ConFondo, BoxLayout):
    """Campo de texto con ícono, borde que se colorea al escribir y opción de ver la contraseña."""

    def __init__(self, sugerencia: str = "", icono: str = "", clave: bool = False, multilinea: bool = False,
                 alto: float = 52, texto: str = "", al_confirmar=None, acento=Paleta.AZUL, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(alto))
        super().__init__(orientation="horizontal", padding=(dp(14), 0, dp(4), 0), spacing=dp(8),
                         radio=dp(12), color_fondo=color(Paleta.SUPERFICIE), color_borde=color(Paleta.LINEA),
                         **kwargs)
        self.acento = acento
        if icono:
            self.add_widget(Icono(icono, tamano=18, color_icono=Paleta.TINTA_TENUE, pos_hint={"center_y": 0.5}))
        self.entrada = TextInput(
            text=texto, hint_text=sugerencia, multiline=multilinea, password=clave, write_tab=False,
            background_normal="", background_active="", background_color=TRANSPARENTE,
            foreground_color=color(Paleta.TINTA), hint_text_color=color(Paleta.TINTA_TENUE),
            cursor_color=color(acento), cursor_width=dp(2), selection_color=color(acento, 0.25),
            font_name=Tipografia.NORMAL, font_size=sp(15))
        # line_height cambia cuando Kivy termina de cargar la fuente: hay que recentrar.
        self.entrada.bind(focus=self._al_enfocar, height=self._centrar, line_height=self._centrar)
        if al_confirmar and not multilinea:
            self.entrada.bind(on_text_validate=lambda *_: al_confirmar())
        self.add_widget(self.entrada)
        if clave:
            self._ojo = BotonIcono("eye", al_presionar=self._alternar_clave, tinta=Paleta.TINTA_TENUE, lado=40,
                                   tamano=18, pos_hint={"center_y": 0.5})
            self.add_widget(self._ojo)
        self._centrar()

    @property
    def texto(self) -> str:
        return self.entrada.text

    @texto.setter
    def texto(self, valor: str) -> None:
        self.entrada.text = valor

    def _centrar(self, *_):
        if self.entrada.multiline:
            self.entrada.padding = [0, dp(12), 0, dp(12)]
        else:
            relleno = max(0, (self.entrada.height - max(self.entrada.line_height, dp(16))) / 2)
            self.entrada.padding = [0, relleno, 0, relleno]
            self.entrada.scroll_y = 0
        # Kivy no vuelve a dibujar el texto de ayuda cuando cambia el relleno:
        # se fuerza reasignándolo en el cuadro siguiente.
        Clock.unschedule(self._refrescar_ayuda)
        Clock.schedule_once(self._refrescar_ayuda, 0)

    def _refrescar_ayuda(self, *_):
        ayuda = self.entrada.hint_text
        self.entrada.hint_text = ""
        self.entrada.hint_text = ayuda

    def _al_enfocar(self, _widget, enfocado):
        self.color_borde = color(self.acento if enfocado else Paleta.LINEA)
        self.grosor_borde = dp(1.6) if enfocado else dp(1)

    def _alternar_clave(self):
        self.entrada.password = not self.entrada.password
        self._ojo.cambiar_icono("eye" if self.entrada.password else "eye-off")


class Casilla(ButtonBehavior, BoxLayout):
    """Casilla de verificación con texto."""

    activa = BooleanProperty(False)

    def __init__(self, texto: str, activa: bool = False, acento=Paleta.AZUL, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, spacing=dp(10), activa=activa, **kwargs)
        self.acento = acento
        self._caja = InsigniaIcono("check", tinta="#FFFFFF", fondo=acento, lado=22, tamano_icono=15,
                                   pos_hint={"center_y": 0.5})
        self._caja.radio = dp(6)
        self._texto = Texto(texto, tamano=Tipografia.PEQUENA, color_texto=Paleta.TINTA_SUAVE,
                            pos_hint={"center_y": 0.5})
        self.add_widget(self._caja)
        self.add_widget(self._texto)
        self.bind(minimum_height=self._ajustar_alto, activa=self._estilo)
        self._estilo()

    def _ajustar_alto(self, *_):
        self.height = max(dp(36), self.minimum_height)

    def on_release(self):
        self.activa = not self.activa

    def _estilo(self, *_):
        self._caja.color_fondo = color(self.acento) if self.activa else color(Paleta.SUPERFICIE)
        self._caja.color_borde = TRANSPARENTE if self.activa else color(Paleta.TINTA_TENUE)
        self._caja.grosor_borde = dp(1.5)
        self._caja.color = color("#FFFFFF") if self.activa else TRANSPARENTE


class Interruptor(ButtonBehavior, Widget):
    """Interruptor animado (encendido / apagado)."""

    activo = BooleanProperty(False)
    avance = NumericProperty(0.0)

    def __init__(self, activo: bool = False, acento=Paleta.AZUL, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(50), dp(30)))
        super().__init__(**kwargs)
        self.acento = color(acento)
        with self.canvas:
            self._pintura_pista = Color()
            self._pista = RoundedRectangle()
            Color(1, 1, 1, 1)
            self._perilla = Ellipse()
        self.activo = activo
        self.avance = 1.0 if activo else 0.0
        self.bind(pos=self._dibujar, size=self._dibujar, avance=self._dibujar, activo=self._animar)
        self._dibujar()

    def on_release(self):
        self.activo = not self.activo

    def _animar(self, *_):
        Animation.cancel_all(self, "avance")
        Animation(avance=1.0 if self.activo else 0.0, d=0.18, t="out_quad").start(self)

    def _dibujar(self, *_):
        gris = color("#C5CFDD")
        a = self.avance
        self._pintura_pista.rgba = [gris[i] + (self.acento[i] - gris[i]) * a for i in range(3)] + [1]
        self._pista.pos, self._pista.size, self._pista.radius = self.pos, self.size, [self.height / 2]
        diametro = self.height - dp(6)
        self._perilla.pos = (self.x + dp(3) + a * (self.width - diametro - dp(6)), self.y + dp(3))
        self._perilla.size = (diametro, diametro)


class BarraProgreso(Widget):
    valor = NumericProperty(0.0)   # entre 0 y 1

    def __init__(self, valor: float = 0.0, color_barra=Paleta.AZUL, alto: float = 8, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(alto))
        super().__init__(valor=max(0.0, min(1.0, valor)), **kwargs)
        with self.canvas:
            Color(rgba=color(Paleta.GRIS_SUAVE))
            self._pista = RoundedRectangle()
            Color(rgba=a_color(color_barra))
            self._relleno = RoundedRectangle()
        self.bind(pos=self._dibujar, size=self._dibujar, valor=self._dibujar)
        self._dibujar()

    def _dibujar(self, *_):
        radio = [self.height / 2]
        self._pista.pos, self._pista.size, self._pista.radius = self.pos, self.size, radio
        ancho = self.width * self.valor
        self._relleno.pos, self._relleno.radius = self.pos, radio
        self._relleno.size = (max(ancho, self.height) if self.valor > 0 else 0, self.height)


class Separador(Widget):
    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(1))
        super().__init__(**kwargs)
        with self.canvas:
            Color(rgba=color(Paleta.LINEA))
            self._linea = Rectangle()
        self.bind(pos=self._dibujar, size=self._dibujar)

    def _dibujar(self, *_):
        self._linea.pos, self._linea.size = self.pos, self.size


class Espacio(Widget):
    """Espacio vertical fijo."""

    def __init__(self, alto: float = 8, **kwargs):
        super().__init__(size_hint_y=None, height=dp(alto), **kwargs)


# ---------------------------------------------------------------------------
# Contenedores
# ---------------------------------------------------------------------------
class Superficie(ConFondo, BoxLayout):
    """Tarjeta blanca vertical cuyo alto se ajusta sola al contenido."""

    def __init__(self, ajustar_alto: bool = True, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("padding", dp(16))
        kwargs.setdefault("spacing", dp(10))
        kwargs.setdefault("color_fondo", color(Paleta.SUPERFICIE))
        kwargs.setdefault("color_borde", color(Paleta.LINEA))
        super().__init__(**kwargs)
        if ajustar_alto:
            self.size_hint_y = None
            self.bind(minimum_height=self.setter("height"))


class TarjetaTocable(ButtonBehavior, Superficie):
    """Tarjeta que responde al toque (cambia de color mientras se presiona)."""

    def __init__(self, al_presionar=None, **kwargs):
        super().__init__(**kwargs)
        self._fondo_normal = list(self.color_fondo)
        self.bind(state=self._estilo)
        if al_presionar:
            self.bind(on_release=lambda *_: al_presionar())

    def _estilo(self, *_):
        self.color_fondo = color(Paleta.GRIS_SUAVE) if self.state == "down" else self._fondo_normal


class Fila(BoxLayout):
    """Fila horizontal cuyo alto es el del hijo más alto."""

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("spacing", dp(10))
        kwargs.setdefault("size_hint_y", None)
        super().__init__(**kwargs)
        self.bind(minimum_height=self.setter("height"))


class Columna(BoxLayout):
    """Columna vertical cuyo alto es la suma de sus hijos."""

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("spacing", dp(4))
        kwargs.setdefault("size_hint_y", None)
        super().__init__(**kwargs)
        self.bind(minimum_height=self.setter("height"))


class CajaNota(ConFondo, BoxLayout):
    """Recuadro de color con ícono, título y texto (clave, error frecuente, avisos)."""

    def __init__(self, titulo: str, texto: str, icono: str = "info", tinta=Paleta.AZUL, fondo=None,
                 **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, padding=dp(14), spacing=dp(12),
                         color_fondo=a_color(fondo or Paleta.suave(tinta)), radio=dp(14), **kwargs)
        self.add_widget(Icono(icono, tamano=20, color_icono=tinta, pos_hint={"top": 1}))
        columna = Columna(spacing=dp(4), pos_hint={"top": 1})
        if titulo:
            columna.add_widget(Texto(titulo, tamano=14, fuente=Tipografia.SEMI, color_texto=tinta))
        self.cuerpo = Texto(texto, tamano=14.5, color_texto=Paleta.TINTA, interlineado=1.2)
        columna.add_widget(self.cuerpo)
        self.add_widget(columna)
        self.bind(minimum_height=self.setter("height"))


class BloqueCuaderno(ConCuadricula, ConFondo, BoxLayout):
    """Ejemplo resuelto "escrito a mano" en una hoja cuadriculada con margen rojo."""

    def __init__(self, pasos, resultado: str, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, padding=(dp(44), dp(16), dp(14), dp(16)),
                         spacing=dp(6), color_fondo=color(Paleta.SUPERFICIE), color_borde=color(Paleta.LINEA),
                         radio=dp(12), margen_rojo=dp(32), **kwargs)
        self.bind(minimum_height=self.setter("height"))
        for paso in pasos:
            self.add_widget(Texto(paso.expresion, tamano=19, fuente=Tipografia.CUADERNO,
                                  color_texto=Paleta.TINTA_CUADERNO, cuaderno=True))
            if paso.nota:
                self.add_widget(Texto(paso.nota, tamano=12.5, color_texto=Paleta.TINTA_SUAVE))
        fila = Fila(padding=(0, dp(6), 0, 0))
        fila.add_widget(Texto("Resultado:", tamano=13, fuente=Tipografia.SEMI, color_texto=Paleta.TINTA_SUAVE,
                              size_hint_x=None, width=dp(84), pos_hint={"center_y": 0.5}))
        fila.add_widget(TextoDestacado(resultado, tamano=21, pos_hint={"center_y": 0.5}))
        fila.add_widget(Widget(size_hint_y=None, height=dp(1)))
        self.add_widget(fila)


class FilaLista(ButtonBehavior, BoxLayout):
    """Fila de una lista: elemento inicial, título, subtítulo y elemento final."""

    def __init__(self, titulo: str, subtitulo: str = "", inicio=None, fin=None, al_presionar=None,
                 flecha: bool | None = None, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, padding=(0, dp(10)), spacing=dp(12),
                         **kwargs)
        with self.canvas.before:
            self._pintura = Color(rgba=TRANSPARENTE)
            self._resalte = RoundedRectangle(radius=[dp(8)])
        self.bind(pos=self._dibujar, size=self._dibujar, state=self._estilo)
        if inicio is not None:
            inicio.pos_hint = {"center_y": 0.5}
            self.add_widget(inicio)
        centro = Columna(spacing=dp(2), pos_hint={"center_y": 0.5})
        centro.add_widget(Texto(titulo, tamano=15, fuente=Tipografia.MEDIA))
        if subtitulo:
            centro.add_widget(Texto(subtitulo, tamano=12.5, color_texto=Paleta.TINTA_SUAVE))
        self.add_widget(centro)
        if fin is not None:
            fin.pos_hint = {"center_y": 0.5}
            self.add_widget(fin)
        if al_presionar and flecha is not False:
            self.add_widget(Icono("chevron-right", tamano=18, color_icono=Paleta.TINTA_TENUE,
                                  pos_hint={"center_y": 0.5}))
        self._al_presionar = al_presionar
        self.bind(minimum_height=self._ajustar_alto)

    def on_release(self):
        if self._al_presionar:
            self._al_presionar()

    def _ajustar_alto(self, *_):
        self.height = max(dp(56), self.minimum_height)

    def _dibujar(self, *_):
        self._resalte.pos = (self.x - dp(6), self.y)
        self._resalte.size = (self.width + dp(12), self.height)

    def _estilo(self, *_):
        activo = self.state == "down" and self._al_presionar is not None
        self._pintura.rgba = color(Paleta.GRIS_SUAVE) if activo else TRANSPARENTE


class EstadoVacio(Columna):
    """Mensaje amable cuando no hay nada que mostrar."""

    def __init__(self, icono: str, titulo: str, texto: str, tinta=Paleta.AZUL, **kwargs):
        super().__init__(spacing=dp(10), padding=(dp(12), dp(28)), **kwargs)
        fila = BoxLayout(size_hint_y=None, height=dp(64))
        fila.add_widget(Widget())
        fila.add_widget(InsigniaIcono(icono, tinta=tinta, lado=64, tamano_icono=30, redonda=True))
        fila.add_widget(Widget())
        self.add_widget(fila)
        self.add_widget(Texto(titulo, tamano=17, fuente=Tipografia.SEMI, alinear="center"))
        self.add_widget(Texto(texto, tamano=14, color_texto=Paleta.TINTA_SUAVE, alinear="center"))


class Metrica(Columna):
    """Número grande con una descripción corta debajo."""

    def __init__(self, valor: str, etiqueta: str, tinta=Paleta.TINTA, **kwargs):
        super().__init__(spacing=dp(2), **kwargs)
        self.add_widget(Texto(valor, tamano=22, fuente=Tipografia.SEMI, color_texto=tinta))
        self.add_widget(Texto(etiqueta, tamano=12, color_texto=Paleta.TINTA_SUAVE))


def encabezado_seccion(titulo: str, detalle: str = "") -> Columna:
    """Título de una sección con una línea opcional de explicación."""
    columna = Columna(spacing=dp(2), padding=(0, dp(6), 0, 0))
    columna.add_widget(Texto(titulo, tamano=Tipografia.SUBTITULO, fuente=Tipografia.SEMI))
    if detalle:
        columna.add_widget(Texto(detalle, tamano=13, color_texto=Paleta.TINTA_SUAVE))
    return columna


def insignia_nota(nota, lado: float = 44) -> Label:
    """Nota dentro de un cuadrado de color según su rango (rojo, ámbar, normal, verde)."""
    from ..modelos import EscalaNotas
    tinta, fondo = Paleta.POR_CATEGORIA_NOTA[EscalaNotas.categoria(nota)]
    etiqueta = InsigniaIcono("circle", tinta=tinta, fondo=fondo, lado=lado)
    etiqueta.font_name, etiqueta.font_size = Tipografia.SEMI, sp(15)
    etiqueta.text = EscalaNotas.formatear(nota)
    return etiqueta

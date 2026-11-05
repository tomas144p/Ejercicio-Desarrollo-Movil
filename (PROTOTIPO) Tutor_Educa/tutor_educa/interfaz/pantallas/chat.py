"""
Chat con el tutor IA (estudiante) o con el asistente para familias (apoderado).

Las respuestas se piden en segundo plano para que la pantalla no se congele
mientras la IA "piensa"; mientras tanto se muestra "Escribiendo…".
"""

from __future__ import annotations

from kivy.clock import Clock
from kivy.effects.scroll import ScrollEffect
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from ..componentes import BotonIcono, CampoTexto, Chip, Columna, ConFondo, InsigniaIcono, Texto, TRANSPARENTE
from ..estilo import FormatoTexto, Paleta, Tipografia, color
from ..navegacion import BarraSuperior, _ConLinea
from .base import FondoPapel, PantallaBase, crear_desplazable

RAPIDAS_ESTUDIANTE = ["Explícame el tema", "Dame un ejemplo", "Hazme una prueba", "Dame una pista", "No entendí"]
RAPIDAS_APODERADO = ["¿Cómo va en sus notas?", "¿Qué está reforzando?", "¿Cómo lo apoyo en casa?",
                     "¿Hay pruebas próximas?"]


class _Globo(ConFondo, BoxLayout):
    pass


class Burbuja(BoxLayout):
    """Un mensaje del chat: a la izquierda el tutor, a la derecha la persona."""

    def __init__(self, rol: str, texto: str, acento, nota: str = "", **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, spacing=dp(8), **kwargs)
        self.es_usuario = rol == "usuario"
        self.globo = _Globo(orientation="vertical", size_hint=(None, None), padding=(dp(14), dp(10)),
                            spacing=dp(6), radio=dp(16))
        if self.es_usuario:
            self.globo.color_fondo = color(acento)
        else:
            self.globo.color_fondo, self.globo.color_borde = color(Paleta.SUPERFICIE), color(Paleta.LINEA)
        self.etiqueta = Label(text=FormatoTexto.enriquecer(texto, 15), markup=True, font_size=sp(15),
                              font_name=Tipografia.NORMAL, line_height=1.2, halign="left", valign="top",
                              color=color("#FFFFFF" if self.es_usuario else Paleta.TINTA), size_hint=(None, None))
        self.globo.add_widget(self.etiqueta)
        self.nota = None
        if nota:
            self.nota = Texto(nota, tamano=11.5, color_texto=Paleta.TINTA_TENUE)
            self.globo.add_widget(self.nota)
        if self.es_usuario:
            self.add_widget(Widget())
            self.add_widget(self.globo)
        else:
            self.add_widget(InsigniaIcono("bot", tinta=acento, lado=30, tamano_icono=16, redonda=True,
                                          pos_hint={"top": 1}))
            self.add_widget(self.globo)
            self.add_widget(Widget())
        self.globo.bind(minimum_height=self._alto)
        self.bind(width=self._ajustar)

    def cambiar_texto(self, texto: str) -> None:
        self.etiqueta.text = FormatoTexto.enriquecer(texto, 15)
        self._ajustar()

    def _ajustar(self, *_):
        if self.width <= 100:
            return
        maximo = self.width * 0.82 - (0 if self.es_usuario else dp(38)) - dp(28)
        etiqueta = self.etiqueta
        etiqueta.text_size = (None, None)
        etiqueta.texture_update()
        ancho = min(etiqueta.texture_size[0], maximo)
        if self.nota is not None:
            ancho = max(ancho, min(dp(220), maximo))
        etiqueta.text_size = (ancho, None)
        etiqueta.texture_update()
        etiqueta.size = (ancho, etiqueta.texture_size[1])
        self.globo.width = ancho + dp(28)

    def _alto(self, *_):
        self.globo.height = self.globo.minimum_height
        self.height = self.globo.height


class _BarraEntrada(_ConLinea, ConFondo, BoxLayout):
    pass


class PantallaChat(PantallaBase):
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.conversacion = None
        self.titulo_chat = self.subtitulo_chat = ""
        self._pregunta_inicial = None
        self._esperando = False
        self._escribiendo = None
        raiz = FondoPapel()
        self._zona_superior = BoxLayout(size_hint_y=None, height=dp(64))
        self.scroll, self.lista = crear_desplazable(spacing=dp(12))
        self._zona_rapidas = BoxLayout(size_hint_y=None, height=dp(52), padding=(dp(12), dp(8)))
        self._zona_entrada = _BarraEntrada(orientation="horizontal", size_hint_y=None, height=dp(70),
                                           padding=(dp(12), dp(10)), spacing=dp(8),
                                           color_fondo=color(Paleta.SUPERFICIE), radio=0)
        self._zona_entrada._agregar_linea(arriba=True)
        for widget in (self._zona_superior, self.scroll, self._zona_rapidas, self._zona_entrada):
            raiz.add_widget(widget)
        self.add_widget(raiz)

    def preparar(self, conversacion, titulo: str, subtitulo: str = "", pregunta_inicial: str | None = None) -> None:
        self.conversacion = conversacion
        self.titulo_chat, self.subtitulo_chat = titulo, subtitulo
        self._pregunta_inicial = pregunta_inicial

    @property
    def _es_apoderado(self) -> bool:
        return self.conversacion is not None and self.conversacion.contexto.modo == "apoderado"

    def actualizar(self) -> None:
        if self.conversacion is None:
            return
        self._zona_superior.clear_widgets()
        self._zona_superior.add_widget(BarraSuperior(self.app, self.titulo_chat, self.subtitulo_chat,
                                                     acento=self.acento, volver=True, mostrar_salir=False))
        self._dibujar_mensajes()
        self._dibujar_rapidas()
        self._dibujar_entrada()
        if self._pregunta_inicial:
            pregunta, self._pregunta_inicial = self._pregunta_inicial, None
            Clock.schedule_once(lambda _dt: self.enviar(pregunta), 0.4)

    def al_cambiar_datos(self) -> None:
        self._dibujar_entrada()

    # ------------------------------------------------------------------
    def _dibujar_mensajes(self) -> None:
        self.lista.clear_widgets()
        if self.app.tutor_ia.usa_ia_real:
            aviso = f"Responde {self.app.tutor_ia.descripcion}. La IA puede equivocarse."
        else:
            aviso = "Modo demostración: responde el tutor integrado de Tutor Educa."
        self.lista.add_widget(Texto(aviso, tamano=11.5, color_texto=Paleta.TINTA_TENUE, alinear="center"))
        for mensaje in self.conversacion.mensajes:
            self.lista.add_widget(Burbuja(mensaje.rol, mensaje.texto, self.acento, mensaje.nota))
        self._escribiendo = None
        if self._esperando:
            self._mostrar_escribiendo()
        self._bajar()

    def _dibujar_rapidas(self) -> None:
        self._zona_rapidas.clear_widgets()
        desplazable = ScrollView(do_scroll_y=False, bar_width=0, effect_cls=ScrollEffect)
        fila = BoxLayout(orientation="horizontal", size_hint_x=None, spacing=dp(8))
        fila.bind(minimum_width=fila.setter("width"))
        for texto in (RAPIDAS_APODERADO if self._es_apoderado else RAPIDAS_ESTUDIANTE):
            fila.add_widget(Chip(texto, acento=self.acento, al_presionar=lambda t=texto: self.enviar(t),
                                 pos_hint={"center_y": 0.5}))
        desplazable.add_widget(fila)
        self._zona_rapidas.add_widget(desplazable)

    def _dibujar_entrada(self) -> None:
        self._zona_entrada.clear_widgets()
        hay_internet = self.app.internet
        sugerencia = ("Escribe tu pregunta…" if self._es_apoderado else "Escribe tu duda…") if hay_internet \
            else "Sin internet: el chat vuelve cuando haya conexión"
        self.campo = CampoTexto(sugerencia, al_confirmar=self.enviar, acento=self.acento, alto=50)
        self.campo.disabled = not hay_internet
        self.boton_enviar = BotonIcono("send", al_presionar=self.enviar, tinta="#FFFFFF", fondo=self.acento,
                                       lado=50, tamano=20, pos_hint={"center_y": 0.5})
        self.boton_enviar.disabled = not hay_internet or self._esperando
        self._zona_entrada.add_widget(self.campo)
        self._zona_entrada.add_widget(self.boton_enviar)

    def _bajar(self) -> None:
        Clock.schedule_once(lambda _dt: setattr(self.scroll, "scroll_y", 0), 0.12)

    def _mostrar_escribiendo(self) -> None:
        self._escribiendo = Burbuja("tutor", "Escribiendo…", self.acento)
        self.lista.add_widget(self._escribiendo)
        self._puntos = 0
        Clock.unschedule(self._animar_puntos)
        Clock.schedule_interval(self._animar_puntos, 0.4)

    def _animar_puntos(self, _dt):
        if self._escribiendo is None:
            return False
        self._puntos = (self._puntos + 1) % 4
        self._escribiendo.cambiar_texto("Escribiendo" + "." * self._puntos)
        return True

    def _quitar_escribiendo(self) -> None:
        Clock.unschedule(self._animar_puntos)
        if self._escribiendo is not None and self._escribiendo.parent is not None:
            self.lista.remove_widget(self._escribiendo)
        self._escribiendo = None

    # ------------------------------------------------------------------
    def enviar(self, texto: str | None = None) -> None:
        texto = (texto if texto is not None else self.campo.texto).strip()
        if not texto or self._esperando or self.conversacion is None:
            return
        if not self.app.internet:
            self.app.notificador.mostrar("Sin internet no se puede usar el chat.", "aviso")
            return
        self.campo.texto = ""
        mensaje = self.conversacion.agregar_usuario(texto)
        self.lista.add_widget(Burbuja(mensaje.rol, mensaje.texto, self.acento))
        self._esperando = True
        self.boton_enviar.disabled = True
        self._mostrar_escribiendo()
        self._bajar()
        conversacion = self.conversacion
        self.app.ejecutor_ia.enviar(conversacion.generar_respuesta,
                                    lambda respuesta: self._recibir(conversacion, respuesta),
                                    lambda error: self._fallo(conversacion, error))

    def _recibir(self, conversacion, mensaje) -> None:
        self._esperando = False
        if conversacion is not self.conversacion:
            return   # la persona cambió de conversación; la respuesta ya quedó guardada en la otra
        self._quitar_escribiendo()
        self.lista.add_widget(Burbuja(mensaje.rol, mensaje.texto, self.acento, mensaje.nota))
        self.boton_enviar.disabled = not self.app.internet
        self._bajar()

    def _fallo(self, conversacion, error) -> None:
        self._esperando = False
        if conversacion is self.conversacion:
            self._quitar_escribiendo()
            self.boton_enviar.disabled = not self.app.internet
        self.app.notificador.mostrar(f"No se pudo obtener respuesta: {error}", "error")

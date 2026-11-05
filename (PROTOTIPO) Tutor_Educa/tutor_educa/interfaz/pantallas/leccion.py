"""
Pantalla de una lección (tema de refuerzo).

Tres secciones, igual que en el prototipo de Figma:
- Aprende: explicación, "la clave" y el error frecuente.
- Ejemplos: ejercicios resueltos paso a paso en una hoja de cuaderno.
- Prueba: preguntas con corrección inmediata, pistas y nota final.

Todo el contenido viene de la base local: funciona sin internet. El
docente (y el apoderado) pueden abrirla en "vista previa": ven lo mismo,
pero la prueba no se guarda.
"""

from __future__ import annotations

from functools import partial

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget

from ...evaluacion import SesionPrueba
from ...modelos import EscalaNotas, Intento, Rol
from ..componentes import (BarraProgreso, BloqueCuaderno, Boton, CajaNota, CampoTexto, Columna, Fila, FilaLista,
                           Icono, InsigniaIcono, Separador, Superficie, Texto, encabezado_seccion)
from ..estilo import Paleta, Tipografia
from ..navegacion import BarraSuperior, ControlSegmentado
from .base import FondoPapel, PantallaBase, crear_desplazable


class PantallaLeccion(PantallaBase):
    SECCIONES = [("aprende", "Aprende", "book-open"), ("ejemplos", "Ejemplos", "notebook-pen"),
                 ("prueba", "Prueba", "target")]

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.tema = None
        self.estudiante_id = None
        self.vista_previa = False
        self.nota_previa = ""
        self.seccion = "aprende"
        self.sesion: SesionPrueba | None = None
        raiz = FondoPapel()
        self._zona_superior = BoxLayout(size_hint_y=None, height=dp(64))
        self._zona_control = BoxLayout(size_hint_y=None, height=dp(62), padding=(dp(16), dp(8)))
        self._zona_contenido = BoxLayout()
        for widget in (self._zona_superior, self._zona_control, self._zona_contenido):
            raiz.add_widget(widget)
        self.add_widget(raiz)

    def preparar(self, tema_id: str, estudiante_id: int | None = None, vista_previa: bool = False,
                 nota_previa: str = "") -> None:
        self.tema = self.app.datos.tema(tema_id)
        self.estudiante_id = estudiante_id
        self.vista_previa = vista_previa or estudiante_id is None
        self.nota_previa = nota_previa
        self.seccion = "aprende"
        self.sesion = None
        self._reiniciar_pregunta()
        if estudiante_id and not self.vista_previa:
            self.app.datos.iniciar_tema(estudiante_id, tema_id)   # «Nuevo» pasa a «En curso»

    def _reiniciar_pregunta(self):
        self._elegida = None
        self._texto_respuesta = ""
        self._resultado = None
        self._pista_visible = False
        self._logro_nuevo = False

    def actualizar(self) -> None:
        if self.tema is None:
            return
        self._zona_superior.clear_widgets()
        self._zona_superior.add_widget(BarraSuperior(self.app, self.tema.titulo, self.nota_previa or self.tema.nivel,
                                                     acento=self.acento, volver=True, mostrar_salir=False))
        self._zona_control.clear_widgets()
        self.control = ControlSegmentado(self.SECCIONES, self.seccion, self.acento, self.cambiar_seccion)
        self._zona_control.add_widget(self.control)
        self.dibujar()

    def al_cambiar_datos(self) -> None:
        # El contenido no cambia al sincronizar y redibujar borraría lo que se está escribiendo.
        pass

    def cambiar_seccion(self, clave: str) -> None:
        self.seccion = clave
        self.control.seleccionar(clave)
        self.dibujar()

    def dibujar(self) -> None:
        self._zona_contenido.clear_widgets()
        scroll, columna = crear_desplazable()
        getattr(self, f"_seccion_{self.seccion}")(columna)
        self._zona_contenido.add_widget(scroll)
        self._scroll = scroll

    @property
    def _es_estudiante(self) -> bool:
        return self.app.usuario is not None and self.app.usuario.rol == Rol.ESTUDIANTE and not self.vista_previa

    # ------------------------------------------------------------------
    def _seccion_aprende(self, c) -> None:
        tema = self.tema
        c.add_widget(Texto(tema.resumen, tamano=17, fuente=Tipografia.MEDIA, interlineado=1.25))
        for parrafo in tema.parrafos:
            c.add_widget(Texto(parrafo, tamano=15, interlineado=1.3))
        c.add_widget(CajaNota("La clave", tema.clave, icono="lightbulb", tinta=Paleta.AMBAR,
                              fondo=Paleta.DESTACADOR_SUAVE))
        c.add_widget(CajaNota("Error frecuente", tema.error_comun, icono="triangle-alert", tinta=Paleta.ROJO))
        c.add_widget(Boton("Ver ejemplos resueltos", icono="notebook-pen", variante="secundario", acento=self.acento,
                           al_presionar=lambda: self.cambiar_seccion("ejemplos")))
        if self._es_estudiante and self.app.internet:
            c.add_widget(Boton("Preguntar al tutor IA", icono="bot", variante="contorno", acento=self.acento,
                               al_presionar=lambda: self.app.abrir_chat_estudiante(self.tema.id)))

    def _seccion_ejemplos(self, c) -> None:
        for numero, ejemplo in enumerate(self.app.datos.ejemplos(self.tema.id), start=1):
            bloque = Columna(spacing=dp(8))
            bloque.add_widget(Texto(f"Ejemplo {numero}: {ejemplo.titulo}", tamano=16, fuente=Tipografia.SEMI))
            bloque.add_widget(Texto(ejemplo.enunciado, tamano=15, color_texto=Paleta.TINTA_SUAVE))
            bloque.add_widget(BloqueCuaderno(ejemplo.pasos, ejemplo.resultado))
            if ejemplo.comprobacion:
                bloque.add_widget(CajaNota("Comprueba", ejemplo.comprobacion, icono="circle-check", tinta=Paleta.VERDE))
            c.add_widget(bloque)
        c.add_widget(Boton("Ir a la prueba", icono="target", acento=self.acento,
                           al_presionar=lambda: self.cambiar_seccion("prueba")))

    # ------------------------------------------------------------------
    def _seccion_prueba(self, c) -> None:
        if self.sesion is None:
            self._intro_prueba(c)
        elif self.sesion.terminada:
            self._resultado_prueba(c)
        else:
            self._pregunta(c)

    def _intro_prueba(self, c) -> None:
        total = len(self.app.datos.preguntas(self.tema.id))
        tarjeta = Superficie(spacing=dp(12), padding=dp(18))
        cabecera = Fila(spacing=dp(12))
        cabecera.add_widget(InsigniaIcono("target", tinta=self.acento, lado=48, tamano_icono=24,
                                          pos_hint={"center_y": 0.5}))
        textos = Columna(spacing=dp(2), pos_hint={"center_y": 0.5})
        textos.add_widget(Texto("Prueba del tema", tamano=17, fuente=Tipografia.SEMI))
        textos.add_widget(Texto(f"{total} preguntas. Con 60 % o más logras el tema.", tamano=13.5,
                                color_texto=Paleta.TINTA_SUAVE))
        cabecera.add_widget(textos)
        tarjeta.add_widget(cabecera)
        tarjeta.add_widget(Texto("Responde cada pregunta una vez. Si te complicas, pide una pista antes de "
                                 "comprobar. La nota se calcula con la escala chilena (exigencia de 60 %).",
                                 tamano=14, color_texto=Paleta.TINTA_SUAVE, interlineado=1.25))
        if self._es_estudiante:
            ficha = self.app.datos.ficha(self.estudiante_id)
            mejor = ficha.mejor_intento(self.tema.id) if ficha else None
            if mejor:
                tarjeta.add_widget(Texto(f"Tu mejor resultado hasta ahora: {mejor.porcentaje} % "
                                         f"(nota {EscalaNotas.formatear(mejor.nota)}).", tamano=14,
                                         fuente=Tipografia.MEDIA))
        else:
            tarjeta.add_widget(CajaNota("", "Vista previa: los resultados de esta prueba no se guardan.",
                                        icono="eye", tinta=Paleta.TINTA_SUAVE, fondo=Paleta.GRIS_SUAVE))
        tarjeta.add_widget(Boton("Comenzar prueba", icono="play", acento=self.acento, al_presionar=self._comenzar))
        c.add_widget(tarjeta)

    def _comenzar(self) -> None:
        self.sesion = SesionPrueba(self.app.datos.preguntas(self.tema.id))
        self._reiniciar_pregunta()
        self.dibujar()

    def _pregunta(self, c) -> None:
        sesion, pregunta = self.sesion, self.sesion.actual
        respondida = self._resultado is not None
        tarjeta = Superficie(spacing=dp(14), padding=dp(18))
        cabecera = Fila()
        cabecera.add_widget(Texto(f"Pregunta {sesion.numero} de {sesion.total}", tamano=13, fuente=Tipografia.SEMI,
                                  color_texto=self.acento))
        cabecera.add_widget(Texto(f"{sesion.correctas} correctas", tamano=13, color_texto=Paleta.TINTA_SUAVE,
                                  alinear="right"))
        tarjeta.add_widget(cabecera)
        tarjeta.add_widget(BarraProgreso(sesion.indice / sesion.total, color_barra=self.acento, alto=6))
        tarjeta.add_widget(Texto(pregunta.enunciado, tamano=18, fuente=Tipografia.MEDIA, interlineado=1.25))

        if pregunta.es_alternativas:
            for alternativa in pregunta.alternativas:
                variante, acento = "contorno", self.acento
                if respondida:
                    if alternativa in pregunta.respuestas_aceptadas:
                        variante, acento = "secundario", Paleta.VERDE
                    elif alternativa == self._elegida:
                        variante, acento = "secundario", Paleta.ROJO
                elif alternativa == self._elegida:
                    variante = "secundario"
                tarjeta.add_widget(Boton(alternativa, variante=variante, acento=acento, alto=50, tamano=15.5,
                                         al_presionar=partial(self._elegir, alternativa)))
        else:
            self.campo = CampoTexto("Escribe tu respuesta", icono="pencil", texto=self._texto_respuesta,
                                    al_confirmar=self._comprobar, acento=self.acento)
            self.campo.entrada.readonly = respondida
            tarjeta.add_widget(self.campo)

        if self._pista_visible and not respondida:
            tarjeta.add_widget(CajaNota("Pista", pregunta.pista, icono="lightbulb", tinta=Paleta.AMBAR,
                                        fondo=Paleta.DESTACADOR_SUAVE))
        if respondida:
            if self._resultado.correcta:
                tarjeta.add_widget(CajaNota("¡Correcto!", pregunta.explicacion, icono="circle-check", tinta=Paleta.VERDE))
            else:
                tarjeta.add_widget(CajaNota(f"La respuesta correcta es {self._resultado.respuesta_correcta}",
                                            pregunta.explicacion, icono="circle-x", tinta=Paleta.ROJO))
            ultima = sesion.indice + 1 >= sesion.total
            tarjeta.add_widget(Boton("Ver mi resultado" if ultima else "Siguiente pregunta",
                                     icono="chevron-right", acento=self.acento, al_presionar=self._siguiente))
        else:
            fila = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
            fila.add_widget(Boton("Pista", icono="lightbulb", variante="contorno", acento=self.acento,
                                  al_presionar=self._mostrar_pista, disabled=self._pista_visible))
            fila.add_widget(Boton("Comprobar", icono="check", acento=self.acento, al_presionar=self._comprobar))
            tarjeta.add_widget(fila)
        c.add_widget(tarjeta)

    def _elegir(self, alternativa: str) -> None:
        if self._resultado is None:
            self._elegida = alternativa
            self.dibujar()

    def _mostrar_pista(self) -> None:
        self.sesion.pista()
        self._pista_visible = True
        if not self.sesion.actual.es_alternativas:
            self._texto_respuesta = self.campo.texto
        self.dibujar()

    def _comprobar(self) -> None:
        pregunta = self.sesion.actual
        respuesta = self._elegida if pregunta.es_alternativas else self.campo.texto
        if not (respuesta or "").strip():
            self.app.notificador.mostrar("Primero elige o escribe una respuesta.")
            return
        if not pregunta.es_alternativas:
            self._texto_respuesta = respuesta
        self._resultado = self.sesion.responder(respuesta)
        self.dibujar()

    def _siguiente(self) -> None:
        self.sesion.siguiente()
        self._reiniciar_pregunta()
        if self.sesion.terminada:
            self._guardar_resultado()
        self.dibujar()

    def _guardar_resultado(self) -> None:
        if not self._es_estudiante:
            return
        intento = Intento.nuevo(self.estudiante_id, self.tema.id, self.sesion.correctas, self.sesion.total)
        self._logro_nuevo = self.app.datos.registrar_intento(intento)
        mensaje = "Resultado guardado."
        if not self.app.en_linea:
            mensaje += " Se enviará a tu docente cuando vuelva la conexión."
        self.app.notificador.mostrar(mensaje, "exito" if self.app.en_linea else "aviso")

    def _resultado_prueba(self, c) -> None:
        sesion = self.sesion
        tinta = Paleta.VERDE if sesion.logrado else Paleta.AMBAR
        tarjeta = Superficie(spacing=dp(8), padding=dp(20))
        fila = Fila()
        fila.add_widget(Widget())
        fila.add_widget(InsigniaIcono("trophy" if sesion.logrado else "target", tinta=tinta, lado=64,
                                      tamano_icono=30, redonda=True))
        fila.add_widget(Widget())
        tarjeta.add_widget(fila)
        tarjeta.add_widget(Texto(f"{sesion.porcentaje} %", tamano=40, fuente=Tipografia.NEGRITA, color_texto=tinta,
                                 alinear="center"))
        tarjeta.add_widget(Texto(f"{sesion.correctas} de {sesion.total} correctas. Nota estimada "
                                 f"{EscalaNotas.formatear(sesion.nota)}.", tamano=14.5,
                                 color_texto=Paleta.TINTA_SUAVE, alinear="center"))
        tarjeta.add_widget(Texto(sesion.mensaje_final(), tamano=15, fuente=Tipografia.MEDIA, alinear="center"))
        if self._logro_nuevo:
            tarjeta.add_widget(CajaNota("¡Tema logrado!", "Tu docente y tu apoderado verán este avance.",
                                        icono="sparkles", tinta=Paleta.VERDE))
        c.add_widget(tarjeta)

        c.add_widget(encabezado_seccion("Tus respuestas"))
        lista = Superficie(padding=(dp(16), dp(4)), spacing=0)
        for numero, registro in enumerate(sesion.historial, start=1):
            detalle = f"Tu respuesta: {registro.respuesta}"
            if not registro.correcta:
                detalle += f". Correcta: {registro.pregunta.respuesta_para_mostrar}"
            if numero > 1:
                lista.add_widget(Separador())
            lista.add_widget(FilaLista(f"{numero}. {registro.pregunta.enunciado}", detalle,
                                       inicio=Icono("circle-check" if registro.correcta else "circle-x", tamano=20,
                                                    color_icono=Paleta.VERDE if registro.correcta else Paleta.ROJO)))
        c.add_widget(lista)
        c.add_widget(Boton("Repetir la prueba", icono="rotate-ccw", variante="contorno", acento=self.acento,
                           al_presionar=self._comenzar))
        c.add_widget(Boton("Volver a la materia", icono="book-open", acento=self.acento,
                           al_presionar=self._volver_a_materia))
        if self._es_estudiante and self.app.internet and not sesion.logrado:
            c.add_widget(Boton("Repasar con el tutor IA", icono="bot", variante="secundario", acento=self.acento,
                               al_presionar=lambda: self.app.abrir_chat_estudiante(self.tema.id)))
        Clock.schedule_once(lambda _dt: setattr(self._scroll, "scroll_y", 1), 0.05)

    def _volver_a_materia(self) -> None:
        self.sesion = None
        self.cambiar_seccion("aprende")

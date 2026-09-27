"""
Ficha de un estudiante (vista del docente).

Aquí el docente desbloquea o bloquea cada tema de Matemáticas para ESE
estudiante con un interruptor, y ve sus notas y el historial de pruebas.
Bloquear un tema no borra el avance: si se vuelve a desbloquear, el
estudiante sigue donde quedó.
"""

from __future__ import annotations

from functools import partial

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout

from ...modelos import EscalaNotas
from ..componentes import (Avatar, CajaNota, CampoTexto, Columna, EstadoVacio, Fila, FilaLista, InsigniaIcono,
                           Interruptor, Metrica, Separador, Superficie, Texto, encabezado_seccion, insignia_nota)
from ..dialogos import Dialogo
from ..estilo import FormatoTexto, Paleta, Tipografia, color
from ..navegacion import BarraSuperior
from .base import FondoPapel, PantallaBase, crear_desplazable

CENTRO = {"center_y": 0.5}


class PantallaFichaEstudiante(PantallaBase):
    ACENTO = Paleta.PIZARRA

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.estudiante_id = None
        self.ficha = None
        self._ignorar = False
        self._scroll = None
        raiz = FondoPapel()
        self._zona_superior = BoxLayout(size_hint_y=None, height=dp(64))
        self._zona_contenido = BoxLayout()
        raiz.add_widget(self._zona_superior)
        raiz.add_widget(self._zona_contenido)
        self.add_widget(raiz)

    def preparar(self, estudiante_id: int) -> None:
        if estudiante_id != self.estudiante_id:
            self._scroll = None
        self.estudiante_id = estudiante_id

    def actualizar(self) -> None:
        self.ficha = self.app.datos.ficha(self.estudiante_id) if self.estudiante_id else None
        if self.ficha is None:
            return
        ficha = self.ficha
        self._zona_superior.clear_widgets()
        self._zona_superior.add_widget(BarraSuperior(self.app, ficha.estudiante.nombre,
                                                     ficha.curso.nombre if ficha.curso else "",
                                                     acento=self.ACENTO, volver=True, mostrar_salir=False))
        posicion = self._scroll.scroll_y if self._scroll is not None else 1
        self._zona_contenido.clear_widgets()
        self._scroll, c = crear_desplazable()
        self._contenido(c)
        self._zona_contenido.add_widget(self._scroll)
        Clock.schedule_once(lambda _dt: setattr(self._scroll, "scroll_y", posicion), 0.05)

    def _contenido(self, c) -> None:
        ficha = self.ficha
        nombre = ficha.estudiante.primer_nombre

        cabecera = Superficie(spacing=dp(14))
        fila = Fila(spacing=dp(14))
        fila.add_widget(Avatar(ficha.estudiante.iniciales, tinta=self.ACENTO, lado=56, pos_hint=CENTRO))
        textos = Columna(spacing=dp(2), pos_hint=CENTRO)
        textos.add_widget(Texto(ficha.estudiante.nombre, tamano=18, fuente=Tipografia.SEMI))
        textos.add_widget(Texto(ficha.estudiante.correo, tamano=12.5, color_texto=Paleta.TINTA_SUAVE))
        textos.add_widget(Texto(f"Apoderado/a: {ficha.apoderado_nombre}" if ficha.apoderado_nombre
                                else "Sin apoderado registrado", tamano=12.5, color_texto=Paleta.TINTA_SUAVE))
        fila.add_widget(textos)
        cabecera.add_widget(fila)
        metricas = Fila()
        mate = ficha.promedio("mat")
        metricas.add_widget(Metrica(EscalaNotas.formatear(mate), "Matemáticas",
                                    tinta=Paleta.POR_CATEGORIA_NOTA[EscalaNotas.categoria(mate)][0]))
        metricas.add_widget(Metrica(EscalaNotas.formatear(ficha.promedio_general), "Promedio general"))
        metricas.add_widget(Metrica(f"{ficha.asistencia} %", "Asistencia"))
        cabecera.add_widget(metricas)
        c.add_widget(cabecera)
        if ficha.necesita_refuerzo:
            c.add_widget(CajaNota("Sugerencia", f"{nombre} tiene promedio bajo 5,0 en Matemáticas. Revisa sus "
                                  "notas y desbloquea los temas donde más le cuesta.", icono="lightbulb",
                                  tinta=Paleta.AMBAR, fondo=Paleta.DESTACADOR_SUAVE))

        c.add_widget(encabezado_seccion("Temas de Matemáticas", f"Activa un tema para que {nombre} lo vea en su "
                                        "app. Bloquearlo no borra su avance."))
        lista = Superficie(padding=(dp(16), dp(4)), spacing=0)
        refuerzos = {r.tema_id: r for r in ficha.refuerzos}
        for indice, tema in enumerate(self.app.datos.temas()):
            refuerzo = refuerzos.get(tema.id)
            activo = bool(refuerzo and refuerzo.activo)
            mejor = ficha.mejor_intento(tema.id)
            if activo:
                detalle = refuerzo.nombre_estado + (f", mejor resultado {mejor.porcentaje} %" if mejor else "")
            elif refuerzo:
                detalle = f"Bloqueado (antes: {refuerzo.nombre_estado.lower()})"
            else:
                detalle = f"Bloqueado, {tema.nivel}"
            interruptor = Interruptor(activo=activo, acento=self.ACENTO)
            interruptor.bind(activo=partial(self._cambiar, tema))
            if indice:
                lista.add_widget(Separador())
            lista.add_widget(FilaLista(tema.titulo, detalle,
                                       inicio=InsigniaIcono(tema.icono, tinta=self.ACENTO if activo else Paleta.TINTA_TENUE,
                                                            fondo=Paleta.PIZARRA_SUAVE if activo else Paleta.GRIS_SUAVE,
                                                            lado=38),
                                       fin=interruptor))
        c.add_widget(lista)

        c.add_widget(encabezado_seccion("Notas por asignatura"))
        notas = Superficie(padding=(dp(16), dp(4)), spacing=0)
        for indice, asignatura in enumerate(self.app.datos.asignaturas()):
            valores = "   ".join(EscalaNotas.formatear(n) for n in ficha.notas_de(asignatura.id)) or "Sin notas"
            if indice:
                notas.add_widget(Separador())
            notas.add_widget(FilaLista(asignatura.nombre, valores,
                                       inicio=InsigniaIcono(asignatura.icono, tinta=asignatura.color,
                                                            fondo=color(asignatura.color, 0.12), lado=36),
                                       fin=insignia_nota(ficha.promedio(asignatura.id), lado=40)))
        c.add_widget(notas)

        c.add_widget(encabezado_seccion("Historial de pruebas"))
        if not ficha.intentos:
            c.add_widget(EstadoVacio("target", "Sin pruebas todavía", f"Cuando {nombre} rinda una prueba, "
                                     "aparecerá aquí.", tinta=self.ACENTO))
            return
        historial = Superficie(padding=(dp(16), dp(4)), spacing=0)
        for indice, intento in enumerate(ficha.intentos):
            tema = self.app.datos.tema(intento.tema_id)
            if indice:
                historial.add_widget(Separador())
            historial.add_widget(FilaLista(tema.titulo if tema else intento.tema_id,
                                           f"{intento.correctas} de {intento.total} correctas ({intento.porcentaje} %), "
                                           f"{FormatoTexto.fecha_relativa(intento.realizado_en)}",
                                           inicio=InsigniaIcono("circle-check" if intento.logrado else "target",
                                                                tinta=Paleta.VERDE if intento.logrado else Paleta.AMBAR,
                                                                lado=36, redonda=True),
                                           fin=insignia_nota(intento.nota, lado=40)))
        c.add_widget(historial)

    # ------------------------------------------------------------------
    def _revertir(self, interruptor, valor: bool) -> None:
        self._ignorar = True
        interruptor.activo = valor
        self._ignorar = False

    def _cambiar(self, tema, interruptor, activo: bool) -> None:
        if self._ignorar:
            return
        nombre = self.ficha.estudiante.primer_nombre
        estudiante_id = self.ficha.estudiante.id
        if activo:
            campo = CampoTexto("Mensaje opcional, por ejemplo: «repasa antes de la prueba»", multilinea=True,
                               alto=90, acento=self.ACENTO)

            def confirmar():
                self.app.datos.cambiar_desbloqueo(estudiante_id, tema.id, True, campo.texto.strip() or None)
                self.app.notificador.mostrar(f"{tema.titulo} desbloqueado para {nombre}.", "exito")
                self.actualizar()

            Dialogo(f"Desbloquear {tema.titulo}", f"{nombre} verá este tema en su app y podrá estudiarlo sin "
                    "internet.", contenido=campo, icono="lock-open", tinta=self.ACENTO, cerrar_al_tocar_fuera=False,
                    botones=[("Cancelar", lambda: self._revertir(interruptor, False), "contorno"),
                             ("Desbloquear", confirmar, "primario")]).open()
        else:
            def bloquear():
                self.app.datos.cambiar_desbloqueo(estudiante_id, tema.id, False)
                self.app.notificador.mostrar(f"{tema.titulo} bloqueado para {nombre}.")
                self.actualizar()

            Dialogo("¿Bloquear este tema?", f"{nombre} dejará de verlo en su app. Su avance y sus resultados se "
                    "conservan.", icono="lock", tinta=Paleta.ROJO, cerrar_al_tocar_fuera=False,
                    botones=[("Cancelar", lambda: self._revertir(interruptor, True), "contorno"),
                             ("Bloquear", bloquear, "peligro")]).open()

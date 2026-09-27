"""
Pantalla principal del apoderado.

Pestañas:
- Resumen: cómo va su estudiante en todas las asignaturas.
- Refuerzos: temas desbloqueados por la docente e ideas para apoyar en casa.
- Avisos: mensajes de la docente (con contador de no leídos).
- Asistente: chat con IA para orientar a la familia (solo con internet).
"""

from __future__ import annotations

from kivy.metrics import dp
from kivy.uix.stacklayout import StackLayout

from ...modelos import EscalaNotas, EstadoRefuerzo
from ..componentes import (Avatar, BarraProgreso, Boton, CajaNota, Chip, Columna, EstadoVacio, Etiqueta, Fila,
                           FilaLista, InsigniaIcono, Metrica, Separador, Superficie, TarjetaTocable, Texto,
                           encabezado_seccion)
from ..dialogos import Dialogo
from ..estilo import FormatoTexto, Paleta, Tipografia, color
from .base import PantallaConPestanas

CENTRO = {"center_y": 0.5}
PREGUNTAS_FRECUENTES = ["¿Cómo va en sus notas?", "¿Qué está reforzando?", "¿Cómo lo apoyo en casa?",
                        "¿Hay pruebas próximas?"]


class PantallaApoderado(PantallaConPestanas):
    PESTANAS = [("resumen", "Resumen", "house"), ("refuerzos", "Refuerzos", "book-open"),
                ("avisos", "Avisos", "bell"), ("asistente", "Asistente", "bot")]
    ACENTO = Paleta.MORA

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.hijo_id = None
        self.hijos, self.ficha, self.avisos = [], None, []

    def reiniciar(self) -> None:
        super().reiniciar()
        self.hijo_id = None

    def actualizar(self) -> None:
        if self.app.usuario is None:
            return
        self.hijos = self.app.datos.hijos()
        ids = [h.estudiante.id for h in self.hijos]
        if self.hijo_id not in ids:
            self.hijo_id = ids[0] if ids else None
        self.ficha = next((h for h in self.hijos if h.estudiante.id == self.hijo_id), None)
        self.avisos = self.app.datos.avisos_apoderado()
        super().actualizar()

    def titulo(self) -> str:
        return f"Hola, {self.app.usuario.primer_nombre}"

    def subtitulo(self) -> str:
        return f"Apoderado/a de {self.ficha.estudiante.primer_nombre}" if self.ficha else "Apoderado/a"

    def actualizar_insignias(self) -> None:
        self.barra_inferior.insignia("avisos", sum(1 for a in self.avisos if not a.leido))

    def _sin_datos(self, c) -> bool:
        if self.ficha is None:
            c.add_widget(EstadoVacio("cloud-off", "Aún no hay datos en este dispositivo",
                                     "Ingresa una vez con conexión para descargar la información de tu estudiante.",
                                     tinta=self.ACENTO))
            return True
        return False

    # ------------------------------------------------------------------
    def pestana_resumen(self, c) -> None:
        if self._sin_datos(c):
            return
        ficha = self.ficha
        if len(self.hijos) > 1:
            selector = StackLayout(orientation="lr-tb", size_hint_y=None, spacing=dp(8))
            selector.bind(minimum_height=selector.setter("height"))
            for hijo in self.hijos:
                selector.add_widget(Chip(hijo.estudiante.primer_nombre, seleccionado=hijo.estudiante.id == self.hijo_id,
                                         acento=self.ACENTO,
                                         al_presionar=lambda e=hijo.estudiante.id: self._elegir_hijo(e)))
            c.add_widget(selector)
        if not self.app.en_linea:
            c.add_widget(CajaNota("Sin conexión", "Estás viendo los datos de la última sincronización.",
                                  icono="wifi-off", tinta=Paleta.AMBAR))

        activos = [r for r in ficha.refuerzos_activos if r.tema]
        logrados = sum(1 for r in activos if r.estado == EstadoRefuerzo.LOGRADO)
        tarjeta = Superficie(spacing=dp(14))
        fila = Fila(spacing=dp(14))
        fila.add_widget(Avatar(ficha.estudiante.iniciales, tinta=self.ACENTO, lado=52, pos_hint=CENTRO))
        textos = Columna(spacing=dp(2), pos_hint=CENTRO)
        textos.add_widget(Texto(ficha.estudiante.nombre, tamano=17, fuente=Tipografia.SEMI))
        textos.add_widget(Texto(ficha.curso.nombre if ficha.curso else "", tamano=13, color_texto=Paleta.TINTA_SUAVE))
        fila.add_widget(textos)
        tarjeta.add_widget(fila)
        metricas = Fila()
        general = ficha.promedio_general
        metricas.add_widget(Metrica(EscalaNotas.formatear(general), "Promedio general",
                                    tinta=Paleta.POR_CATEGORIA_NOTA[EscalaNotas.categoria(general)][0]))
        metricas.add_widget(Metrica(f"{ficha.asistencia} %", "Asistencia"))
        metricas.add_widget(Metrica(f"{logrados} de {len(activos)}", "Temas logrados", tinta=Paleta.VERDE))
        tarjeta.add_widget(metricas)
        c.add_widget(tarjeta)

        no_leidos = sum(1 for a in self.avisos if not a.leido)
        if no_leidos:
            c.add_widget(Boton(f"Tienes {no_leidos} {'aviso' if no_leidos == 1 else 'avisos'} sin leer", icono="bell",
                               variante="secundario", acento=self.ACENTO,
                               al_presionar=lambda: self.cambiar_pestana("avisos")))

        c.add_widget(encabezado_seccion("Rendimiento por asignatura", "Escala de 1,0 a 7,0. Se aprueba con 4,0."))
        lista = Superficie(spacing=dp(14))
        for asignatura in self.app.datos.asignaturas():
            nota = ficha.promedio(asignatura.id)
            tinta = Paleta.POR_CATEGORIA_NOTA[EscalaNotas.categoria(nota)][0]
            fila = Fila(spacing=dp(12))
            fila.add_widget(Texto(asignatura.nombre, tamano=13.5, fuente=Tipografia.MEDIA, size_hint_x=None,
                                  width=dp(128), pos_hint=CENTRO))
            fila.add_widget(BarraProgreso((nota or 0) / 7, color_barra=tinta, pos_hint=CENTRO))
            fila.add_widget(Texto(EscalaNotas.formatear(nota), tamano=15, fuente=Tipografia.SEMI, color_texto=tinta,
                                  alinear="right", size_hint_x=None, width=dp(36), pos_hint=CENTRO))
            lista.add_widget(fila)
        c.add_widget(lista)

        c.add_widget(encabezado_seccion("Lo que está reforzando"))
        if not activos:
            c.add_widget(Texto("Por ahora no tiene temas de refuerzo.", tamano=14, color_texto=Paleta.TINTA_SUAVE))
            return
        refuerzos = Superficie(padding=(dp(16), dp(4)), spacing=0)
        for indice, refuerzo in enumerate(activos):
            tinta, fondo = Paleta.POR_ESTADO[refuerzo.estado]
            if indice:
                refuerzos.add_widget(Separador())
            refuerzos.add_widget(FilaLista(refuerzo.tema.titulo, refuerzo.tema.nivel,
                                           inicio=InsigniaIcono(refuerzo.tema.icono, tinta=self.ACENTO, lado=38),
                                           fin=Etiqueta(refuerzo.nombre_estado, tinta=tinta, fondo=fondo),
                                           al_presionar=lambda: self.cambiar_pestana("refuerzos")))
        c.add_widget(refuerzos)

    def _elegir_hijo(self, estudiante_id: int) -> None:
        self.hijo_id = estudiante_id
        self.actualizar()

    # ------------------------------------------------------------------
    def pestana_refuerzos(self, c) -> None:
        if self._sin_datos(c):
            return
        ficha = self.ficha
        nombre = ficha.estudiante.primer_nombre
        activos = [r for r in ficha.refuerzos_activos if r.tema]
        c.add_widget(Texto(f"Temas que la docente desbloqueó para {nombre}, con ideas simples para acompañar "
                           "desde la casa.", tamano=13.5, color_texto=Paleta.TINTA_SUAVE))
        if not activos:
            c.add_widget(EstadoVacio("book-open", "Sin temas de refuerzo", f"Cuando la docente desbloquee un "
                                     f"tema para {nombre}, aparecerá aquí.", tinta=self.ACENTO))
            return
        for refuerzo in activos:
            tema = refuerzo.tema
            tinta, fondo = Paleta.POR_ESTADO[refuerzo.estado]
            tarjeta = Superficie(spacing=dp(12))
            cabecera = Fila(spacing=dp(12))
            cabecera.add_widget(InsigniaIcono(tema.icono, tinta=self.ACENTO, lado=44, pos_hint=CENTRO))
            textos = Columna(spacing=dp(2), pos_hint=CENTRO)
            textos.add_widget(Texto(tema.titulo, tamano=15.5, fuente=Tipografia.SEMI))
            textos.add_widget(Texto(tema.nivel, tamano=12.5, color_texto=Paleta.TINTA_SUAVE))
            cabecera.add_widget(textos)
            cabecera.add_widget(Etiqueta(refuerzo.nombre_estado, tinta=tinta, fondo=fondo, pos_hint=CENTRO))
            tarjeta.add_widget(cabecera)
            ultimo = next((i for i in ficha.intentos if i.tema_id == tema.id), None)
            if ultimo:
                texto = (f"Último intento: {ultimo.correctas} de {ultimo.total} correctas ({ultimo.porcentaje} %), "
                         f"{FormatoTexto.fecha_relativa(ultimo.realizado_en)}.")
            else:
                texto = "Aún no rinde la prueba de este tema."
            tarjeta.add_widget(Texto(texto, tamano=13.5, color_texto=Paleta.TINTA_SUAVE))
            if refuerzo.mensaje:
                tarjeta.add_widget(CajaNota("Mensaje de la docente", refuerzo.mensaje, icono="message-circle",
                                            tinta=Paleta.TINTA_SUAVE, fondo=Paleta.PAPEL))
            tarjeta.add_widget(CajaNota("Cómo apoyar en casa", tema.consejo_apoderado, icono="heart-handshake",
                                        tinta=self.ACENTO))
            tarjeta.add_widget(Boton("Ver la materia", icono="book-open", variante="contorno", acento=self.ACENTO,
                                     alto=44, tamano=14,
                                     al_presionar=lambda t=tema.id: self.app.abrir_leccion(
                                         t, vista_previa=True, nota=f"Materia de {nombre}")))
            c.add_widget(tarjeta)

    # ------------------------------------------------------------------
    def pestana_avisos(self, c) -> None:
        if not self.avisos:
            c.add_widget(EstadoVacio("bell", "Sin avisos", "Aquí verás los mensajes de la docente.", tinta=self.ACENTO))
            return
        if any(not a.leido for a in self.avisos):
            c.add_widget(Boton("Marcar todos como leídos", icono="check", variante="fantasma", acento=self.ACENTO,
                               alto=40, tamano=14, al_presionar=self._marcar_todos))
        nombres = {h.estudiante.id: h.estudiante.primer_nombre for h in self.hijos}
        for aviso in self.avisos:
            tinta, fondo, icono, nombre_tipo = Paleta.POR_TIPO_AVISO.get(aviso.tipo, Paleta.POR_TIPO_AVISO["info"])
            tarjeta = TarjetaTocable(spacing=dp(8), al_presionar=lambda a=aviso: self._abrir_aviso(a))
            if not aviso.leido:
                tarjeta.color_borde, tarjeta.grosor_borde = color(self.ACENTO), dp(1.5)
            cabecera = Fila(spacing=dp(8))
            cabecera.add_widget(Etiqueta(nombre_tipo, tinta=tinta, fondo=fondo, icono=icono, pos_hint=CENTRO))
            if not aviso.leido:
                cabecera.add_widget(Etiqueta("Nuevo", tinta="#FFFFFF", fondo=self.ACENTO, pos_hint=CENTRO))
            cabecera.add_widget(Texto(FormatoTexto.fecha_relativa(aviso.creado_en), tamano=12,
                                      color_texto=Paleta.TINTA_TENUE, alinear="right", pos_hint=CENTRO))
            tarjeta.add_widget(cabecera)
            tarjeta.add_widget(Texto(aviso.titulo, tamano=15.5, fuente=Tipografia.SEMI))
            resumen = aviso.cuerpo if len(aviso.cuerpo) <= 120 else aviso.cuerpo[:117].rstrip() + "…"
            tarjeta.add_widget(Texto(resumen, tamano=13.5, color_texto=Paleta.TINTA_SUAVE))
            para = f"para {nombres.get(aviso.estudiante_id, 'tu estudiante')}" if aviso.estudiante_id else "para todo el curso"
            tarjeta.add_widget(Texto(f"De {self.app.datos.nombre_de(aviso.autor_id) or 'la docente'}, {para}",
                                     tamano=12, color_texto=Paleta.TINTA_TENUE))
            c.add_widget(tarjeta)

    def _abrir_aviso(self, aviso) -> None:
        tinta, _fondo, icono, _nombre = Paleta.POR_TIPO_AVISO.get(aviso.tipo, Paleta.POR_TIPO_AVISO["info"])
        Dialogo.informar(aviso.titulo, aviso.cuerpo, icono=icono, tinta=tinta)
        if not aviso.leido:
            self.app.datos.marcar_leido(aviso)
            self.dibujar_pestana(conservar_posicion=True)

    def _marcar_todos(self) -> None:
        for aviso in self.avisos:
            self.app.datos.marcar_leido(aviso)
        self.dibujar_pestana(conservar_posicion=True)

    # ------------------------------------------------------------------
    def pestana_asistente(self, c) -> None:
        nombre = self.ficha.estudiante.primer_nombre if self.ficha else "tu estudiante"
        if not self.app.internet:
            c.add_widget(EstadoVacio("wifi-off", "El asistente necesita internet", f"Cuando vuelva la conexión "
                                     f"podrás preguntarle cómo apoyar a {nombre} en casa.", tinta=Paleta.AMBAR))
            return
        if self._sin_datos(c):
            return
        tarjeta = Superficie(spacing=dp(12))
        cabecera = Fila(spacing=dp(12))
        cabecera.add_widget(InsigniaIcono("bot", tinta=self.ACENTO, lado=50, tamano_icono=26, pos_hint=CENTRO))
        textos = Columna(spacing=dp(3), pos_hint=CENTRO)
        textos.add_widget(Texto("Asistente para familias", tamano=17, fuente=Tipografia.SEMI))
        textos.add_widget(Texto(f"Pregúntale cómo va {nombre}, qué está aprendiendo y cómo apoyar en casa.",
                                tamano=13.5, color_texto=Paleta.TINTA_SUAVE))
        cabecera.add_widget(textos)
        tarjeta.add_widget(cabecera)
        if self.app.tutor_ia.usa_ia_real:
            tarjeta.add_widget(CajaNota("", f"Funciona con {self.app.tutor_ia.descripcion} y solo usa los datos de "
                                        f"{nombre} que ves en esta app.", icono="shield-check", tinta=self.ACENTO))
        else:
            tarjeta.add_widget(CajaNota("", "Modo demostración: responde el asistente integrado con los datos de la "
                                        "app. Con una clave de IA responde Claude.", icono="info",
                                        tinta=Paleta.TINTA_SUAVE, fondo=Paleta.GRIS_SUAVE))
        tarjeta.add_widget(Boton("Abrir el asistente", icono="message-circle", acento=self.ACENTO,
                                 al_presionar=lambda: self.app.abrir_chat_apoderado(self.hijo_id)))
        c.add_widget(tarjeta)
        c.add_widget(encabezado_seccion("Preguntas frecuentes"))
        lista = Superficie(padding=(dp(16), dp(4)), spacing=0)
        for indice, pregunta in enumerate(PREGUNTAS_FRECUENTES):
            if indice:
                lista.add_widget(Separador())
            lista.add_widget(FilaLista(pregunta, inicio=InsigniaIcono("message-circle", tinta=self.ACENTO, lado=36),
                                       al_presionar=lambda p=pregunta: self.app.abrir_chat_apoderado(self.hijo_id, p)))
        c.add_widget(lista)

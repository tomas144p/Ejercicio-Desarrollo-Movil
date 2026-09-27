"""
Pantalla principal del estudiante.

Pestañas:
- Inicio: temas de refuerzo que desbloqueó su docente (se estudian sin internet).
- Notas: rendimiento en todas sus asignaturas.
- Progreso: avance por tema e historial de pruebas.
- Tutor IA: chat con el tutor (solo con internet).
"""

from __future__ import annotations

from kivy.metrics import dp

from ...modelos import EscalaNotas, EstadoRefuerzo
from ..componentes import (BarraProgreso, CajaNota, Columna, EstadoVacio, Etiqueta, Fila, FilaLista, Icono,
                           InsigniaIcono, Metrica, Separador, Superficie, TarjetaTocable, Texto,
                           encabezado_seccion, insignia_nota)
from ..estilo import FormatoTexto, Paleta, Tipografia, color
from .base import PantallaConPestanas

CENTRO = {"center_y": 0.5}


def tinta_nota(nota) -> str:
    return Paleta.POR_CATEGORIA_NOTA[EscalaNotas.categoria(nota)][0]


class PantallaEstudiante(PantallaConPestanas):
    PESTANAS = [("inicio", "Inicio", "house"), ("notas", "Notas", "chart-column"),
                ("progreso", "Progreso", "trophy"), ("tutor", "Tutor IA", "bot")]
    ACENTO = Paleta.AZUL

    def actualizar(self) -> None:
        self.ficha = self.app.datos.ficha(self.app.usuario.id) if self.app.usuario else None
        super().actualizar()

    def titulo(self) -> str:
        return f"Hola, {self.app.usuario.primer_nombre}"

    def subtitulo(self) -> str:
        return self.ficha.curso.nombre if self.ficha and self.ficha.curso else "Estudiante"

    def _sin_datos(self, c) -> bool:
        if self.ficha is None:
            c.add_widget(EstadoVacio("cloud-off", "Aún no hay datos en este dispositivo",
                                     "Ingresa una vez con conexión para descargar tu información."))
            return True
        return False

    # ------------------------------------------------------------------
    def pestana_inicio(self, c) -> None:
        if self._sin_datos(c):
            return
        ficha = self.ficha
        if not self.app.en_linea:
            c.add_widget(CajaNota("Estás sin conexión", "Puedes leer la materia y rendir las pruebas. Tus "
                                  "resultados se enviarán solos cuando vuelva la conexión.", icono="wifi-off",
                                  tinta=Paleta.AMBAR))
        activos = [r for r in ficha.refuerzos_activos if r.tema]
        logrados = sum(1 for r in activos if r.estado == EstadoRefuerzo.LOGRADO)
        resumen = Superficie()
        fila = Fila()
        fila.add_widget(Metrica(EscalaNotas.formatear(ficha.promedio_general), "Promedio general",
                                tinta=tinta_nota(ficha.promedio_general)))
        fila.add_widget(Metrica(f"{ficha.asistencia} %", "Asistencia"))
        fila.add_widget(Metrica(f"{logrados} de {len(activos)}", "Temas logrados", tinta=Paleta.VERDE))
        resumen.add_widget(fila)
        c.add_widget(resumen)

        c.add_widget(encabezado_seccion("Tus temas de refuerzo", "Los desbloquea tu docente según lo que "
                                        "necesitas. Puedes estudiarlos incluso sin internet."))
        if not activos:
            c.add_widget(EstadoVacio("sparkles", "Aún no tienes temas desbloqueados",
                                     "Cuando tu docente desbloquee un tema, aparecerá aquí."))
        for refuerzo in activos:
            c.add_widget(self._tarjeta_refuerzo(refuerzo))

    def _tarjeta_refuerzo(self, refuerzo):
        tema = refuerzo.tema
        tinta_estado, fondo_estado = Paleta.POR_ESTADO[refuerzo.estado]
        tarjeta = TarjetaTocable(al_presionar=lambda: self.app.abrir_leccion(tema.id), spacing=dp(12))
        cabecera = Fila(spacing=dp(12))
        cabecera.add_widget(InsigniaIcono(tema.icono, tinta=Paleta.AZUL, lado=46, tamano_icono=22, pos_hint=CENTRO))
        textos = Columna(spacing=dp(2), pos_hint=CENTRO)
        textos.add_widget(Texto(tema.titulo, tamano=16, fuente=Tipografia.SEMI))
        textos.add_widget(Texto(tema.nivel, tamano=12.5, color_texto=Paleta.TINTA_SUAVE))
        cabecera.add_widget(textos)
        cabecera.add_widget(Etiqueta(refuerzo.nombre_estado, tinta=tinta_estado, fondo=fondo_estado, pos_hint=CENTRO))
        tarjeta.add_widget(cabecera)
        if refuerzo.mensaje:
            tarjeta.add_widget(CajaNota("Mensaje de tu docente", refuerzo.mensaje, icono="message-circle",
                                        tinta=Paleta.AZUL, fondo=Paleta.PAPEL))
        mejor = self.ficha.mejor_intento(tema.id)
        if mejor:
            tarjeta.add_widget(BarraProgreso(mejor.porcentaje / 100, alto=6,
                                             color_barra=Paleta.VERDE if mejor.logrado else Paleta.AMBAR))
            detalle = f"Mejor resultado: {mejor.porcentaje} % (nota {EscalaNotas.formatear(mejor.nota)})"
        else:
            detalle = "Aún no rindes la prueba de este tema"
        pie = Fila()
        pie.add_widget(Texto(detalle, tamano=13, color_texto=Paleta.TINTA_SUAVE, pos_hint=CENTRO))
        pie.add_widget(Texto("Estudiar", tamano=13.5, fuente=Tipografia.SEMI, color_texto=Paleta.AZUL,
                             alinear="right", size_hint_x=None, width=dp(66), pos_hint=CENTRO))
        pie.add_widget(Icono("chevron-right", tamano=16, color_icono=Paleta.AZUL, pos_hint=CENTRO))
        tarjeta.add_widget(pie)
        return tarjeta

    # ------------------------------------------------------------------
    def pestana_notas(self, c) -> None:
        if self._sin_datos(c):
            return
        ficha = self.ficha
        resumen = Superficie()
        fila = Fila()
        fila.add_widget(Metrica(EscalaNotas.formatear(ficha.promedio_general), "Promedio general",
                                tinta=tinta_nota(ficha.promedio_general)))
        fila.add_widget(Metrica(f"{ficha.asistencia} %", "Asistencia"))
        resumen.add_widget(fila)
        resumen.add_widget(Texto("Escala de 1,0 a 7,0. Se aprueba con 4,0.", tamano=12.5,
                                 color_texto=Paleta.TINTA_TENUE))
        c.add_widget(resumen)
        c.add_widget(encabezado_seccion("Por asignatura"))
        lista = Superficie(padding=(dp(16), dp(4)), spacing=0)
        for indice, asignatura in enumerate(self.app.datos.asignaturas()):
            notas = ficha.notas_de(asignatura.id)
            detalle = "   ".join(EscalaNotas.formatear(n) for n in notas) or "Sin notas todavía"
            if asignatura.tiene_tutor:
                detalle += "\nCon tutor de refuerzo"
            if indice:
                lista.add_widget(Separador())
            lista.add_widget(FilaLista(asignatura.nombre, detalle,
                                       inicio=InsigniaIcono(asignatura.icono, tinta=asignatura.color,
                                                            fondo=color(asignatura.color, 0.12), lado=40),
                                       fin=insignia_nota(ficha.promedio(asignatura.id))))
        c.add_widget(lista)

    # ------------------------------------------------------------------
    def pestana_progreso(self, c) -> None:
        if self._sin_datos(c):
            return
        ficha = self.ficha
        activos = [r for r in ficha.refuerzos_activos if r.tema]
        logrados = sum(1 for r in activos if r.estado == EstadoRefuerzo.LOGRADO)
        mejor_nota = max((i.nota for i in ficha.intentos), default=None)
        resumen = Superficie()
        fila = Fila()
        fila.add_widget(Metrica(f"{logrados} de {len(activos)}", "Temas logrados", tinta=Paleta.VERDE))
        fila.add_widget(Metrica(str(len(ficha.intentos)), "Pruebas rendidas"))
        fila.add_widget(Metrica(EscalaNotas.formatear(mejor_nota), "Mejor nota", tinta=tinta_nota(mejor_nota)))
        resumen.add_widget(fila)
        c.add_widget(resumen)

        if activos:
            c.add_widget(encabezado_seccion("Avance por tema"))
            lista = Superficie(spacing=dp(14))
            for refuerzo in activos:
                mejor = ficha.mejor_intento(refuerzo.tema_id)
                bloque = Columna(spacing=dp(6))
                cabecera = Fila()
                cabecera.add_widget(Texto(refuerzo.tema.titulo, tamano=14.5, fuente=Tipografia.MEDIA, pos_hint=CENTRO))
                tinta, fondo = Paleta.POR_ESTADO[refuerzo.estado]
                cabecera.add_widget(Etiqueta(refuerzo.nombre_estado, tinta=tinta, fondo=fondo, pos_hint=CENTRO))
                bloque.add_widget(cabecera)
                bloque.add_widget(BarraProgreso(mejor.porcentaje / 100 if mejor else 0,
                                                color_barra=Paleta.VERDE if refuerzo.estado == EstadoRefuerzo.LOGRADO
                                                else Paleta.AZUL))
                bloque.add_widget(Texto(f"Mejor resultado: {mejor.porcentaje} %" if mejor else "Sin pruebas todavía",
                                        tamano=12, color_texto=Paleta.TINTA_SUAVE))
                lista.add_widget(bloque)
            c.add_widget(lista)

        c.add_widget(encabezado_seccion("Historial de pruebas"))
        if not ficha.intentos:
            c.add_widget(EstadoVacio("target", "Todavía no rindes pruebas",
                                     "Cuando termines la prueba de un tema, tu resultado aparecerá aquí."))
            return
        lista = Superficie(padding=(dp(16), dp(4)), spacing=0)
        for indice, intento in enumerate(ficha.intentos):
            tema = self.app.datos.tema(intento.tema_id)
            icono, tinta = ("circle-check", Paleta.VERDE) if intento.logrado else ("target", Paleta.AMBAR)
            if indice:
                lista.add_widget(Separador())
            lista.add_widget(FilaLista(tema.titulo if tema else intento.tema_id,
                                       f"{intento.correctas} de {intento.total} correctas, "
                                       f"{FormatoTexto.fecha_relativa(intento.realizado_en)}",
                                       inicio=InsigniaIcono(icono, tinta=tinta, lado=38, redonda=True),
                                       fin=insignia_nota(intento.nota, lado=42)))
        c.add_widget(lista)

    # ------------------------------------------------------------------
    def pestana_tutor(self, c) -> None:
        if not self.app.internet:
            c.add_widget(EstadoVacio("wifi-off", "El tutor IA necesita internet",
                                     "Mientras tanto puedes leer la materia y practicar con la prueba de cada "
                                     "tema: eso funciona sin conexión.", tinta=Paleta.AMBAR))
            return
        tarjeta = Superficie(spacing=dp(12))
        cabecera = Fila(spacing=dp(12))
        cabecera.add_widget(InsigniaIcono("bot", lado=50, tamano_icono=26, pos_hint=CENTRO))
        textos = Columna(spacing=dp(3), pos_hint=CENTRO)
        textos.add_widget(Texto("Tu tutor de matemáticas", tamano=17, fuente=Tipografia.SEMI))
        textos.add_widget(Texto("Te explica tus dudas, te muestra ejemplos resueltos y te toma una mini prueba.",
                                tamano=13.5, color_texto=Paleta.TINTA_SUAVE))
        cabecera.add_widget(textos)
        tarjeta.add_widget(cabecera)
        tarjeta.add_widget(self._nota_modo_ia())
        c.add_widget(tarjeta)

        c.add_widget(encabezado_seccion("¿Sobre qué quieres conversar?"))
        lista = Superficie(padding=(dp(16), dp(4)), spacing=0)
        activos = [r for r in (self.ficha.refuerzos_activos if self.ficha else []) if r.tema]
        for refuerzo in activos:
            lista.add_widget(FilaLista(refuerzo.tema.titulo, refuerzo.tema.nivel,
                                       inicio=InsigniaIcono(refuerzo.tema.icono, lado=38),
                                       al_presionar=lambda t=refuerzo.tema_id: self.app.abrir_chat_estudiante(t)))
            lista.add_widget(Separador())
        lista.add_widget(FilaLista("Otra duda de matemáticas", "Pregunta libre sobre cualquier tema",
                                   inicio=InsigniaIcono("circle-help", tinta=Paleta.TINTA_SUAVE, lado=38),
                                   al_presionar=lambda: self.app.abrir_chat_estudiante(None)))
        c.add_widget(lista)

    def _nota_modo_ia(self):
        if self.app.tutor_ia.usa_ia_real:
            return CajaNota("", f"Funciona con {self.app.tutor_ia.descripcion}. La IA puede equivocarse: si algo "
                            "no calza, pregúntale a tu docente.", icono="sparkles", tinta=Paleta.AZUL)
        return CajaNota("", "Modo demostración: responde el tutor integrado usando la materia del colegio. "
                        "Para usar Claude, agrega una clave en config.local.json.", icono="info",
                        tinta=Paleta.TINTA_SUAVE, fondo=Paleta.GRIS_SUAVE)

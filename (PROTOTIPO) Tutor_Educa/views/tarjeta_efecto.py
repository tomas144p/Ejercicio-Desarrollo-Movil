"""
Tarjetas con el efecto de Tutor Educa: promedio inicial y actual, variación y aciertos del primer intento.

Se muestran en la ficha del estudiante (docente), en la vista del apoderado y, resumidas, en «Mi curso».
La variación va siempre con una palabra y un ícono (no solo color) y junto con cuánto practicó el estudiante, porque
una subida o bajada del promedio no prueba por sí sola que Tutor Educa sea la causa.
"""

from __future__ import annotations

from kivy.metrics import dp

from models.modelos import EscalaNotas
from services.metricas import (MIN_GRUPO, UMBRAL_PRACTICA, Metricas, ResumenEfecto, lectura, nota_texto,
                               variacion_texto)
from views.componentes import Boton, Columna, Etiqueta, Fila, Metrica, Superficie, Texto
from views.estilo import Paleta, Tipografia

TENDENCIA = {"sube": "sube", "baja": "baja", "estable": "estable"}


def _porcentaje(valor) -> str:
    return "—" if valor is None else f"{round(valor)} %"


def _tinta_nota(nota):
    return Paleta.POR_CATEGORIA_NOTA[EscalaNotas.categoria(nota)][0] if nota is not None else Paleta.TINTA


def _titulo(texto: str, detalle: str) -> Columna:
    caja = Columna(spacing=dp(2))
    caja.add_widget(Texto(texto, tamano=16, fuente=Tipografia.SEMI))
    caja.add_widget(Texto(detalle, tamano=12.5, color_texto=Paleta.TINTA_SUAVE))
    return caja


def tarjeta_efecto(m: Metricas, para: str = "docente", nombre: str = "") -> Superficie:
    """Efecto de un estudiante. ``para``: «docente» o «apoderado» (cambia el tono del texto)."""
    tarjeta = Superficie(spacing=dp(12))
    tarjeta.add_widget(_titulo("Efecto de Tutor Educa", m.semestre.nombre))
    if m.notas == 0:
        tarjeta.add_widget(Texto(lectura(m, para, nombre), tamano=13.5, color_texto=Paleta.TINTA_SUAVE))
        return tarjeta

    notas = Fila()
    notas.add_widget(Metrica(nota_texto(m.promedio_inicial), "Inicial", tinta=_tinta_nota(m.promedio_inicial)))
    notas.add_widget(Metrica(nota_texto(m.promedio_final), "Promedio actual", tinta=_tinta_nota(m.promedio_final)))
    if m.suficientes:
        tinta, icono, palabra = Paleta.POR_TENDENCIA[m.direccion]
        notas.add_widget(Metrica(variacion_texto(m.variacion), "Variación", tinta=tinta))
    else:
        notas.add_widget(Metrica("—", "Variación", tinta=Paleta.TINTA_TENUE))
    tarjeta.add_widget(notas)
    if m.suficientes:
        tinta, icono, palabra = Paleta.POR_TENDENCIA[m.direccion]
        tarjeta.add_widget(Etiqueta(palabra, tinta=tinta, icono=icono))

    uso = Fila()
    uso.add_widget(Metrica(_porcentaje(m.aciertos_primer_intento), "Aciertos al 1.er intento"))
    uso.add_widget(Metrica(str(m.pruebas), "Pruebas rendidas"))
    uso.add_widget(Metrica(str(m.dias_activos), "Días con actividad"))
    tarjeta.add_widget(uso)

    tarjeta.add_widget(Texto(lectura(m, para, nombre), tamano=13.5, color_texto=Paleta.TINTA))
    origen = ("El inicial es el promedio registrado al comenzar." if m.origen_inicial == "registrado"
              else "El inicial es la primera nota del semestre.")
    aclaracion = (f"{origen} La variación puede deberse a otras causas, no solo a Tutor Educa."
                  if para == "docente" else f"{origen} Compara con el promedio de hoy.")
    tarjeta.add_widget(Texto(aclaracion, tamano=12, color_texto=Paleta.TINTA_TENUE))
    return tarjeta


def tarjeta_efecto_curso(r: ResumenEfecto, semestre: str, al_exportar) -> Superficie:
    """Resumen del curso y botón para exportar las métricas."""
    tarjeta = Superficie(spacing=dp(12))
    tarjeta.add_widget(_titulo("Efecto de Tutor Educa en el curso", semestre))
    if not r.con_datos:
        tarjeta.add_widget(Texto("Todavía hay pocas notas en este semestre para comparar el promedio de cada "
                                 "estudiante.", tamano=13.5, color_texto=Paleta.TINTA_SUAVE))
    else:
        fila = Fila()
        fila.add_widget(Metrica(str(r.subieron), "Mejoraron", tinta=Paleta.VERDE if r.subieron else Paleta.TINTA))
        fila.add_widget(Metrica(str(r.estables), "Se mantienen"))
        fila.add_widget(Metrica(str(r.bajaron), "Bajaron", tinta=Paleta.ROJO if r.bajaron else Paleta.TINTA))
        tarjeta.add_widget(fila)
        tarjeta.add_widget(Texto(f"Cambio medio del promedio: {variacion_texto(r.variacion_promedio)} "
                                 f"({r.con_datos} {'estudiante' if r.con_datos == 1 else 'estudiantes'} con "
                                 f"datos). Acierto medio al primer intento: {_porcentaje(r.aciertos_primer_intento)}.",
                                 tamano=13.5, color_texto=Paleta.TINTA))
        if r.comparacion_confiable:
            tarjeta.add_widget(Texto(
                f"Con práctica ({UMBRAL_PRACTICA} o más pruebas, {r.n_con_practica}): "
                f"{variacion_texto(r.variacion_con_practica)}. Sin práctica ({r.n_sin_practica}): "
                f"{variacion_texto(r.variacion_sin_practica)}. Es una comparación, no prueba una causa.",
                tamano=13.5, color_texto=Paleta.TINTA))
        else:
            tarjeta.add_widget(Texto(f"Todavía no se puede comparar a quienes practican con quienes no: hacen falta al "
                                     f"menos {MIN_GRUPO} estudiantes en cada grupo.", tamano=12.5,
                                     color_texto=Paleta.TINTA_TENUE))
    tarjeta.add_widget(Boton("Exportar métricas (CSV)", icono="download", variante="contorno", alto=42, tamano=13.5,
                             al_presionar=al_exportar))
    return tarjeta

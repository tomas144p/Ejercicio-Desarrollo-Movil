"""
Gráfico de progreso con Matplotlib (Python puro, sin Kivy).

Dibuja las notas y la duración de cada prueba y guarda la figura como imagen PNG;
la vista solo muestra ese archivo. Se usa el motor «Agg», que dibuja a un archivo
sin abrir ninguna ventana.
"""

from pathlib import Path

import numpy as np

from models.modelos import Intento
from services.estadisticas import ordenar_cronologico

AZUL, VERDE, AMBAR, GRIS = "#2747C7", "#1E8E5A", "#D9902F", "#8A91A5"


def grafico_progreso(intentos: list, ruta: Path) -> bool:
    """Guarda en ``ruta`` el gráfico de las pruebas. Devuelve False si hay menos de 2 (no hay nada que comparar)."""
    if len(intentos) < 2:
        return False
    from matplotlib.backends.backend_agg import FigureCanvasAgg   # se importa aquí para no demorar el inicio de la app
    from matplotlib.figure import Figure

    ordenados = ordenar_cronologico(intentos)
    x = np.arange(len(ordenados))
    notas = np.array([i.nota for i in ordenados], dtype=float)
    segundos = np.array([i.duracion_seg for i in ordenados], dtype=float)
    etiquetas = [i.fecha_legible[:5] for i in ordenados]              # «dd/mm»

    figura = Figure(figsize=(6.0, 4.4), dpi=110)
    FigureCanvasAgg(figura)
    arriba, abajo = figura.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios": [3, 2]})

    # Notas por prueba + recta de tendencia (np.polyfit)
    arriba.plot(x, notas, marker="o", color=AZUL, linewidth=2, label="Nota")
    arriba.axhline(4.0, color=AMBAR, linestyle="--", linewidth=1, label="Nota 4,0")
    pendiente, origen = np.polyfit(x, notas, 1)
    arriba.plot(x, pendiente * x + origen, color=GRIS, linestyle=":", linewidth=1.6, label="Tendencia")
    arriba.set_ylim(1, 7.3)
    arriba.set_ylabel("Nota")
    arriba.set_title("Mi progreso en las pruebas", fontsize=11, fontweight="bold")
    arriba.legend(fontsize=7.5, loc="lower right", ncol=3, frameon=False)
    arriba.grid(alpha=0.25)

    # Duración de cada prueba
    abajo.bar(x, segundos, color=VERDE, width=0.55)
    abajo.set_ylabel("Segundos")
    abajo.set_xticks(x)
    abajo.set_xticklabels(etiquetas, fontsize=8)
    abajo.grid(axis="y", alpha=0.25)

    figura.tight_layout()
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    figura.savefig(ruta, format="png")
    return True

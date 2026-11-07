"""
Estadísticas de la bitácora de práctica con NumPy (Python puro, sin Kivy).

Recibe una lista de ``Intento`` y calcula promedios, desviación estándar y la
tendencia de las notas (pendiente de una recta ajustada con ``np.polyfit``).
"""

import numpy as np

# Cambio mínimo de nota por prueba para hablar de mejora o baja (bajo eso se considera estable).
UMBRAL_TENDENCIA = 0.05


def ordenar_cronologico(intentos: list) -> list:
    """Del intento más antiguo al más reciente (el orden que necesita un gráfico)."""
    return sorted(intentos, key=lambda i: i.realizado_en)


def tendencia(notas) -> str:
    """«mejorando», «estable» o «bajando», según la pendiente de la recta que mejor ajusta las notas."""
    if len(notas) < 2:
        return "sin datos"
    pendiente = np.polyfit(np.arange(len(notas)), np.asarray(notas, dtype=float), 1)[0]
    if pendiente > UMBRAL_TENDENCIA:
        return "mejorando"
    if pendiente < -UMBRAL_TENDENCIA:
        return "bajando"
    return "estable"


def resumen(intentos: list) -> dict:
    """Números que muestra la bitácora. Con lista vacía devuelve ceros."""
    if not intentos:
        return {"cantidad": 0, "nota_promedio": 0.0, "nota_desviacion": 0.0, "mejor_nota": 0.0,
                "duracion_promedio": 0.0, "tendencia": "sin datos"}
    ordenados = ordenar_cronologico(intentos)
    notas = np.array([i.nota for i in ordenados], dtype=float)
    duraciones = np.array([i.duracion_seg for i in ordenados if i.duracion_seg > 0], dtype=float)
    return {"cantidad": len(ordenados),
            "nota_promedio": float(np.mean(notas)),
            "nota_desviacion": float(np.std(notas)),
            "mejor_nota": float(np.max(notas)),
            "duracion_promedio": float(np.mean(duraciones)) if duraciones.size else 0.0,
            "tendencia": tendencia(notas)}

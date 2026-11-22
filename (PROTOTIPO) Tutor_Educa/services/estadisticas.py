"""
Estadísticas de la bitácora de práctica con NumPy (Python puro, sin Kivy).

Recibe una lista de ``Intento`` y calcula promedios, desviación estándar y la
tendencia de las notas (pendiente de una recta ajustada con ``np.polyfit``).

NumPy es opcional: en el computador se usa NumPy; si no está instalado (por ejemplo, en el APK, donde se deja fuera
para que compile más rápido y pese menos) se calcula lo mismo con Python puro. Las dos formas dan el mismo resultado
(hay una prueba que lo comprueba).
"""

try:
    import numpy as np
except ImportError:          # el APK no lleva NumPy
    np = None

# Cambio mínimo de nota por prueba para hablar de mejora o baja (bajo eso se considera estable).
UMBRAL_TENDENCIA = 0.05


def ordenar_cronologico(intentos: list) -> list:
    """Del intento más antiguo al más reciente (el orden que necesita un gráfico)."""
    return sorted(intentos, key=lambda i: i.realizado_en)


def _pendiente(notas: list[float]) -> float:
    """Pendiente de la recta que mejor ajusta las notas (mínimos cuadrados), con o sin NumPy."""
    if np is not None:
        return float(np.polyfit(np.arange(len(notas)), np.asarray(notas, dtype=float), 1)[0])
    n = len(notas)
    media_x, media_y = (n - 1) / 2, sum(notas) / n
    numerador = sum((x - media_x) * (y - media_y) for x, y in enumerate(notas))
    denominador = sum((x - media_x) ** 2 for x in range(n))
    return numerador / denominador


def tendencia(notas) -> str:
    """«mejorando», «estable» o «bajando», según la pendiente de la recta que mejor ajusta las notas."""
    if len(notas) < 2:
        return "sin datos"
    pendiente = _pendiente([float(n) for n in notas])
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
    notas = [float(i.nota) for i in ordenados]
    duraciones = [float(i.duracion_seg) for i in ordenados if i.duracion_seg > 0]
    if np is not None:
        promedio, desviacion = float(np.mean(notas)), float(np.std(notas))
    else:
        promedio = sum(notas) / len(notas)
        desviacion = (sum((n - promedio) ** 2 for n in notas) / len(notas)) ** 0.5      # desviación poblacional, como np.std
    return {"cantidad": len(ordenados),
            "nota_promedio": promedio,
            "nota_desviacion": desviacion,
            "mejor_nota": max(notas),
            "duracion_promedio": sum(duraciones) / len(duraciones) if duraciones else 0.0,
            "tendencia": tendencia(notas)}

"""
Demostración por consola de las librerías del proyecto (sin abrir la app):

1. Persistencia: un objeto Intento se guarda en JSON y se vuelve a leer.
2. NumPy: estadísticas de las pruebas (promedio, variación, tendencia).
3. Matplotlib: gráfico de progreso guardado como imagen PNG.
4. time.perf_counter(): benchmark entre un ciclo de Python y NumPy.

Uso:  python herramientas/demo_librerias.py
Si ya existe datos_locales/intentos.json (hay pruebas rendidas en la app) usa esos datos;
si no, usa datos de ejemplo.
"""

import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import numpy as np

from models.modelos import Intento
from services.almacen_json import AlmacenIntentos
from services.estadisticas import resumen
from services.graficos import grafico_progreso


def datos_de_ejemplo() -> list:
    """Cinco pruebas de ejemplo, una por día, con notas que van mejorando."""
    intentos = []
    for dias_atras, (correctas, segundos) in zip((4, 3, 2, 1, 0), ((2, 95), (3, 80), (3, 70), (4, 62), (5, 55))):
        intento = Intento.nuevo(1, "mat-ecuaciones", correctas, 5, duracion_seg=segundos)
        intento.realizado_en = (datetime.now() - timedelta(days=dias_atras)).strftime("%Y-%m-%d %H:%M:%S")
        intentos.append(intento)
    return intentos


print("=== 1. Persistencia en JSON (POO + to_dict) ===")
with tempfile.TemporaryDirectory() as carpeta:
    almacen_prueba = AlmacenIntentos(Path(carpeta) / "prueba.json")
    nuevo = Intento.nuevo(1, "mat-fracciones", 4, 5, duracion_seg=61.3)
    print("Objeto a diccionario:", nuevo.to_dict())
    almacen_prueba.agregar(nuevo)
    leido = almacen_prueba.cargar()[0]
    print(f"Leído desde el archivo: {leido.tema_id}, nota {leido.nota}, {leido.fecha_legible}, {leido.duracion_legible}")

print("\n=== 2. NumPy: estadísticas ===")
real = AlmacenIntentos(RAIZ / "datos_locales" / "intentos.json").cargar()
intentos = real or datos_de_ejemplo()
print("Datos usados:", f"{len(real)} pruebas de datos_locales/intentos.json" if real else "5 pruebas de ejemplo")
for nombre, valor in resumen(intentos).items():
    print(f"  {nombre}: {valor:.2f}" if isinstance(valor, float) else f"  {nombre}: {valor}")

print("\n=== 3. Matplotlib: gráfico de progreso ===")
ruta = RAIZ / "datos_locales" / "grafico_demo.png"
if grafico_progreso(intentos, ruta):
    print(f"Gráfico guardado en: {ruta}")

print("\n=== 4. time.perf_counter(): benchmark ===")
numeros = [float(n) for n in range(1_000_000)]
inicio = time.perf_counter()
suma = 0.0
for numero in numeros:
    suma += numero
t_python = time.perf_counter() - inicio

arreglo = np.array(numeros)
inicio = time.perf_counter()
suma_np = arreglo.sum()
t_numpy = time.perf_counter() - inicio
print(f"Ciclo de Python: {t_python * 1000:.2f} ms | NumPy: {t_numpy * 1000:.3f} ms | "
      f"NumPy fue {t_python / max(t_numpy, 1e-9):.0f} veces más rápido (mismo resultado: {suma == suma_np})")

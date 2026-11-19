"""
Orden de la lista de estudiantes del docente.

Python puro (sin Kivy): así se puede probar sin abrir la app y la pantalla solo lo llama.
"""

from __future__ import annotations

ORDENES = ("menor", "mayor", "nombre")


def ordenar_fichas(fichas: list, orden: str = "menor", asignatura_id: str = "mat") -> list:
    """
    Ordena fichas de estudiantes por promedio de la asignatura o por nombre.

    - ``"menor"``: de la nota más baja a la más alta (quien más ayuda necesita, primero).
    - ``"mayor"``: de la nota más alta a la más baja.
    - ``"nombre"``: alfabético.

    Quien aún no tiene nota va siempre al final, ordenado por nombre.
    """
    if orden not in ORDENES:
        raise ValueError(f"Orden desconocido: {orden!r}")
    if orden == "nombre":
        return sorted(fichas, key=lambda f: f.estudiante.nombre)
    con_nota = [f for f in fichas if f.promedio(asignatura_id) is not None]
    sin_nota = sorted((f for f in fichas if f.promedio(asignatura_id) is None), key=lambda f: f.estudiante.nombre)
    # Desempate por nombre siempre ascendente, también en "mayor".
    con_nota.sort(key=lambda f: f.estudiante.nombre)
    con_nota.sort(key=lambda f: f.promedio(asignatura_id), reverse=orden == "mayor")
    return con_nota + sin_nota

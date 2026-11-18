"""
Elección de curso para docentes con más de uno (Python puro, sin interfaz).

Reglas:
- Con un solo curso no se pregunta nada: se entra directo.
- Con varios, la docente elige primero el curso y después ve la lista de estudiantes.
- Si el curso que había elegido ya no es suyo (por ejemplo, se lo reasignaron), vuelve a elegir.
- En el selector, los cursos con más estudiantes en riesgo aparecen primero (lo urgente arriba).
"""

from __future__ import annotations

from dataclasses import dataclass

from models.modelos import Curso


@dataclass
class ResumenCurso:
    """Lo que la docente necesita ver de un curso antes de entrar."""

    curso: Curso
    estudiantes: int
    en_riesgo: int          # estudiantes con promedio bajo 5,0 en Matemáticas
    sin_apoderado: int = 0  # estudiantes sin apoderado registrado (nadie recibiría sus avisos)
    avisos_sin_confirmar: int = 0   # avisos recientes a los que aún les faltan «Recibido»


def curso_activo(cursos: list[Curso], elegido_id: int | None) -> Curso | None:
    """El curso con que se trabaja, o None si la docente todavía tiene que elegir (o no tiene cursos)."""
    if not cursos:
        return None
    if len(cursos) == 1:
        return cursos[0]
    return next((c for c in cursos if c.id == elegido_id), None)


def ordenar_resumenes(resumenes: list[ResumenCurso]) -> list[ResumenCurso]:
    """Primero los cursos con más estudiantes en riesgo; a igualdad, por nombre."""
    return sorted(resumenes, key=lambda r: (-r.en_riesgo, r.curso.nombre))

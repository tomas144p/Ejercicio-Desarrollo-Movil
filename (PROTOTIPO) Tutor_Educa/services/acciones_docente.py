"""
Ayudas para que la app le ahorre trabajo a la docente (Python puro, sin interfaz).

Responde a tres preguntas del tipo «¿qué hago hoy?»:
- ¿Qué tema le conviene desbloquear a los estudiantes que están en riesgo?
- ¿Quiénes están en riesgo y todavía no tienen ningún refuerzo?
- ¿Cuántas familias aún no confirman «Recibido» en los avisos recientes?

Además guarda las plantillas de aviso, para no escribir lo mismo cada vez.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

DIAS_AVISOS_RECIENTES = 14      # los avisos más antiguos no se reclaman


def tiene_tema(ficha, tema_id: str) -> bool:
    return any(r.tema_id == tema_id and r.activo for r in ficha.refuerzos)


@dataclass
class SugerenciaTema:
    tema_id: str
    estudiantes: int        # a cuántos estudiantes en riesgo les falta este tema


def en_riesgo_sin_refuerzo(fichas: list) -> list:
    """Estudiantes bajo el umbral de Matemáticas que todavía no tienen ningún tema desbloqueado."""
    return [f for f in fichas if f.necesita_refuerzo and not f.refuerzos_activos]


def tema_sugerido(fichas: list, temas: list) -> SugerenciaTema | None:
    """
    El tema que más estudiantes en riesgo todavía no tienen; si hay empate, el primero del programa.
    Devuelve None si nadie está en riesgo o si todos tienen ya todos los temas.
    """
    riesgo = [f for f in fichas if f.necesita_refuerzo]
    mejor: SugerenciaTema | None = None
    for tema in sorted(temas, key=lambda t: t.orden):
        faltan = sum(1 for f in riesgo if not tiene_tema(f, tema.id))
        if faltan and (mejor is None or faltan > mejor.estudiantes):
            mejor = SugerenciaTema(tema.id, faltan)
    return mejor


@dataclass
class AvisosSinConfirmar:
    avisos: int = 0         # cuántos avisos recientes tienen familias sin «Recibido»
    familias: int = 0       # suma de familias que faltan (una familia puede contarse en varios avisos)


def avisos_sin_confirmar(avisos: list, fichas: list, ahora: datetime | None = None,
                         dias: int = DIAS_AVISOS_RECIENTES) -> AvisosSinConfirmar:
    """Avisos ya enviados, de los últimos ``dias`` días, a los que les faltan confirmaciones."""
    ahora = ahora or datetime.now()
    limite = ahora - timedelta(days=dias)
    con_apoderado = {f.estudiante.id for f in fichas if f.apoderado_nombre}
    resumen = AvisosSinConfirmar()
    for aviso in avisos:
        if aviso.pendiente or _fecha(aviso.creado_en, ahora) < limite:
            continue
        destinatarios = (1 if aviso.estudiante_id in con_apoderado else 0) if aviso.estudiante_id \
            else len(con_apoderado)
        faltan = destinatarios - aviso.lectores
        if faltan > 0:
            resumen.avisos += 1
            resumen.familias += faltan
    return resumen


def _fecha(texto: str, respaldo: datetime) -> datetime:
    """Fecha de un aviso; si no se puede leer, se considera reciente (mejor avisar de más que de menos)."""
    try:
        fecha = datetime.fromisoformat(texto)
    except (TypeError, ValueError):
        return respaldo
    return fecha.replace(tzinfo=None) if fecha.tzinfo else fecha


# ----------------------------------------------------------------------
# Plantillas de aviso
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class PlantillaAviso:
    nombre: str
    tipo: str
    titulo: str
    cuerpo: str     # lo que va entre [corchetes] la docente debe completarlo antes de enviar


PLANTILLAS_AVISO = [
    PlantillaAviso("Evaluación", "evaluacion", "Evaluación de Matemáticas",
                   "Les recuerdo que el [fecha] tendremos una evaluación de Matemáticas sobre [contenidos]. "
                   "Pueden ayudar a su hijo/a repasando el tema en la app, incluso sin internet."),
    PlantillaAviso("Refuerzo", "refuerzo", "Tema para repasar en casa",
                   "Está disponible el tema «[tema]» en la sección Refuerzos. Con unos 15 minutos al día "
                   "es suficiente. Gracias por acompañarlos."),
    PlantillaAviso("Reunión", "info", "Reunión de apoderados",
                   "Los invito a la reunión de apoderados el [fecha] a las [hora] en [lugar]. "
                   "Por favor confirmen que recibieron este aviso."),
    PlantillaAviso("Felicitación", "logro", "¡Felicitaciones al curso!",
                   "Quiero felicitar al curso por su esfuerzo en [logro]. "
                   "Gracias por el apoyo que dan en casa."),
]

_MARCA_SIN_COMPLETAR = re.compile(r"\[[^\[\]]+\]")


def tiene_datos_sin_completar(*textos: str) -> bool:
    """True si queda algún [dato] de una plantilla sin reemplazar."""
    return any(_MARCA_SIN_COMPLETAR.search(t or "") for t in textos)

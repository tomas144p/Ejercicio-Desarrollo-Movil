"""
Calculadora de notas (tarea 19): puntaje ↔ nota con exigencia variable, tabla de puntajes y «¿qué nota necesito?».

Python puro (sin Kivy, sin base de datos, sin internet): lo usan la app y las pruebas, y funciona sin conexión.

Fórmula habitual en Chile, con exigencia ``e`` (por defecto 60 %), puntaje máximo ``M`` y puntaje obtenido ``p``:
- si ``p ≥ e·M``:  nota = 4 + 3 · (p − e·M) / (M − e·M)
- si no:           nota = 1 + 3 · p / (e·M)

Convenciones (para confirmar con docentes, porque algunos colegios usan otra escala):
- La nota se redondea a **un decimal, con el redondeo escolar** (5,15 → 5,2), igual que en el resto de la app.
- Exigencia 0 %: todos llegan al 4,0 sin hacer nada y la nota sube de 4,0 a 7,0. Exigencia 100 %: solo el puntaje
  máximo aprueba y **el puntaje máximo siempre es un 7,0**.
- «Puntos necesarios para una nota» es el puntaje **más bajo** cuya nota (ya redondeada, la que se ve en pantalla)
  llega a la nota pedida. Por defecto avanza de a 1 punto; con ``paso=0,5`` de a medio punto.
- «¿Qué nota necesito?» mira el promedio **redondeado**, porque es el que se informa.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction

from models.modelos import EscalaNotas, redondear

EXIGENCIA_DEFECTO = 60.0
MAX_PUNTAJE = 1000.0
MINIMA, APROBACION, MAXIMA = EscalaNotas.MINIMA, EscalaNotas.APROBACION, EscalaNotas.MAXIMA


class ErrorCalculo(ValueError):
    """Un dato que no sirve para calcular; el mensaje está escrito para mostrarse tal cual."""


# ---------------------------------------------------------------------------
# Leer lo que escribe una persona
# ---------------------------------------------------------------------------
def parsear_numero(texto, nombre: str = "El número") -> float:
    """«5,5», «5.5», « 12 » → número. Acepta coma o punto. Lo demás es un error con mensaje claro."""
    if isinstance(texto, (int, float)) and not isinstance(texto, bool):
        valor = float(texto)
    else:
        limpio = str(texto or "").strip().replace(",", ".").replace(" ", "")
        if not limpio:
            raise ErrorCalculo(f"{nombre} está vacío.")
        try:
            valor = float(limpio)
        except ValueError:
            raise ErrorCalculo(f"{nombre} no es un número válido (escríbelo así: 5,5).") from None
    if math.isnan(valor) or math.isinf(valor):
        raise ErrorCalculo(f"{nombre} no es un número válido.")
    return valor


def parsear_nota(texto, nombre: str = "La nota") -> float:
    valor = parsear_numero(texto, nombre)
    if not MINIMA <= valor <= MAXIMA:
        raise ErrorCalculo(f"{nombre} debe estar entre 1,0 y 7,0.")
    return valor


def parsear_notas(texto: str) -> list[float]:
    """«5,5  6,0 4,2» (separadas por espacios, saltos de línea o punto y coma) → [5.5, 6.0, 4.2]."""
    partes = [p for p in str(texto or "").replace(";", " ").replace("\n", " ").split() if p]
    return [parsear_nota(p, f"La nota «{p}»") for p in partes]


# ---------------------------------------------------------------------------
# Puntaje ↔ nota
# ---------------------------------------------------------------------------
def _f(valor) -> Fraction:
    """Un número como fracción exacta: 4,1 + 0,1 da justo 4,2 (con decimales de computador daría 4,199999...)."""
    return Fraction(str(valor))


def _validar_prueba(maximo: float, exigencia: float) -> None:
    if not 0 < maximo <= MAX_PUNTAJE:
        raise ErrorCalculo(f"El puntaje máximo debe ser mayor que 0 y de hasta {MAX_PUNTAJE:g} puntos.")
    if not 0 <= exigencia <= 100:
        raise ErrorCalculo("La exigencia debe estar entre 0 % y 100 %.")


validar_prueba = _validar_prueba        # público: la pantalla lo usa para avisar de un dato malo antes de calcular


def nota_exacta(maximo: float, obtenido: float, exigencia: float = EXIGENCIA_DEFECTO) -> float:
    """La nota sin redondear. Un puntaje fuera de 0..máximo se acota (no hay notas bajo 1,0 ni sobre 7,0)."""
    _validar_prueba(maximo, exigencia)
    m, e = _f(maximo), _f(exigencia) / 100
    puntaje = max(Fraction(0), min(m, _f(obtenido)))
    minimo_para_aprobar = e * m
    if puntaje >= minimo_para_aprobar:
        if m == minimo_para_aprobar:                       # exigencia 100 %: solo el máximo aprueba, y es un 7,0
            return MAXIMA if puntaje >= m else APROBACION
        return float(_f(APROBACION) + (_f(MAXIMA) - _f(APROBACION)) * (puntaje - minimo_para_aprobar)
                     / (m - minimo_para_aprobar))
    return float(_f(MINIMA) + (_f(APROBACION) - _f(MINIMA)) * puntaje / minimo_para_aprobar)


def nota_por_puntaje(maximo: float, obtenido: float, exigencia: float = EXIGENCIA_DEFECTO) -> float:
    """La nota (1,0 a 7,0) con un decimal."""
    return redondear(nota_exacta(maximo, obtenido, exigencia))


def puntaje_para_nota(maximo: float, nota: float, exigencia: float = EXIGENCIA_DEFECTO,
                      paso: float = 1.0) -> float | None:
    """
    El puntaje más bajo (de a ``paso`` puntos) que da esa nota o más. ``None`` si ni el puntaje máximo alcanza
    (solo pasa con exigencia 100 % y una nota sobre 4,0... y el máximo siempre da 7,0, así que en la práctica no ocurre).
    """
    _validar_prueba(maximo, exigencia)
    if not MINIMA <= nota <= MAXIMA:
        raise ErrorCalculo("La nota debe estar entre 1,0 y 7,0.")
    if paso <= 0:
        raise ErrorCalculo("El avance de puntos debe ser mayor que 0.")
    nota = redondear(nota)
    pasos = int(math.floor(maximo / paso + 1e-9))
    for n in range(pasos + 1):
        puntaje = round(n * paso, 6)
        if nota_por_puntaje(maximo, puntaje, exigencia) >= nota:
            return puntaje
    return maximo if nota_por_puntaje(maximo, maximo, exigencia) >= nota else None


def tabla_puntajes(maximo: float, exigencia: float = EXIGENCIA_DEFECTO, paso: float = 1.0) -> list[tuple[float, float]]:
    """[(puntaje, nota)] de toda la prueba, del puntaje 0 al máximo."""
    _validar_prueba(maximo, exigencia)
    if paso <= 0:
        raise ErrorCalculo("El avance de puntos debe ser mayor que 0.")
    pasos = int(math.floor(maximo / paso + 1e-9))
    puntajes = [round(n * paso, 6) for n in range(pasos + 1)]
    if puntajes[-1] < maximo:
        puntajes.append(float(maximo))                    # el máximo siempre aparece
    return [(p, nota_por_puntaje(maximo, p, exigencia)) for p in puntajes]


def formato_puntaje(valor: float) -> str:
    """12.5 → «12,5»; 36.0 → «36» (coma decimal, como se escribe en Chile)."""
    return f"{valor:g}".replace(".", ",")


def etiqueta_puntos(valor: float) -> str:
    """«1 punto», «36 puntos», «12,5 puntos»."""
    return f"{formato_puntaje(valor)} {'punto' if valor == 1 else 'puntos'}"


def texto_tabla(maximo: float, exigencia: float = EXIGENCIA_DEFECTO, paso: float = 1.0) -> str:
    """La tabla lista para pegar en un mensaje: una línea por puntaje."""
    lineas = [f"Tabla de notas · {formato_puntaje(maximo)} puntos · exigencia {formato_puntaje(exigencia)} %"]
    lineas += [f"{etiqueta_puntos(p)} → {EscalaNotas.formatear(n)}"
               for p, n in tabla_puntajes(maximo, exigencia, paso)]
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# ¿Qué nota necesito?
# ---------------------------------------------------------------------------
@dataclass
class NotaNecesaria:
    estado: str                      # "ya_cumple" | "alcanzable" | "imposible"
    nota: float | None               # la nota que hay que sacar en lo que falta (None si ya cumple)
    promedio_actual: float | None    # promedio de lo que ya hay (None si todavía no hay notas)
    mejor_promedio: float            # el promedio más alto posible (sacando 7,0 en todo lo que falta)


def nota_necesaria(actuales: list[tuple[float, float]], peso_restante: float, objetivo: float) -> NotaNecesaria:
    """
    ``actuales``: [(nota, peso)] de lo que ya hay (el peso puede ser un porcentaje o «1» si todas valen lo mismo).
    ``peso_restante``: lo que falta, en las mismas unidades. ``objetivo``: el promedio que se quiere.
    Devuelve la nota que se necesita en lo que falta (con un decimal; si falta más de una evaluación, es la nota
    que habría que sacar en cada una).
    """
    if not MINIMA <= objetivo <= MAXIMA:
        raise ErrorCalculo("El promedio que quieres debe estar entre 1,0 y 7,0.")
    if peso_restante <= 0:
        raise ErrorCalculo("Tiene que faltar al menos una evaluación para poder calcular.")
    for nota, peso in actuales:
        if not MINIMA <= nota <= MAXIMA or peso <= 0:
            raise ErrorCalculo("Cada nota debe estar entre 1,0 y 7,0 y tener un peso mayor que 0.")
    objetivo = redondear(objetivo)
    peso_actual = sum((_f(p) for _n, p in actuales), Fraction(0))
    suma_actual = sum((_f(n) * _f(p) for n, p in actuales), Fraction(0))
    falta = _f(peso_restante)
    total = peso_actual + falta
    mejor = redondear(float((suma_actual + _f(MAXIMA) * falta) / total))
    actual = redondear(float(suma_actual / peso_actual)) if actuales else None

    def promedio_con(x: float) -> float:
        return redondear(float((suma_actual + _f(x) * falta) / total))

    if promedio_con(MINIMA) >= objetivo:
        return NotaNecesaria("ya_cumple", None, actual, mejor)
    if promedio_con(MAXIMA) < objetivo:
        return NotaNecesaria("imposible", None, actual, mejor)
    x = max(MINIMA, math.ceil(float(((_f(objetivo) - Fraction(1, 20)) * total - suma_actual) / falta * 10)) / 10)
    while x > MINIMA and promedio_con(redondear(x - 0.1)) >= objetivo:       # por si el redondeo dejó un décimo de sobra
        x = redondear(x - 0.1)
    while x < MAXIMA and promedio_con(x) < objetivo:                          # o de menos
        x = redondear(x + 0.1)
    return NotaNecesaria("alcanzable", redondear(x), actual, mejor)

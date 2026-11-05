"""
Corrección de respuestas y lógica de la "prueba" de cada tema.

Un niño de 12 años puede escribir la misma respuesta de muchas formas:
"5", "x = 5", "x=5", "5 cm", "−9" (con el signo menos de Word), "0,75",
"3/4", "$32.000" o "32000". El corrector acepta todas esas variantes para
que la app no marque como error algo que está bien.

La clase ``SesionPrueba`` maneja el avance pregunta por pregunta y el
puntaje. No depende de Kivy: la usa la pantalla de la lección y también el
tutor sin conexión del chat.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Optional

from .modelos import PORCENTAJE_LOGRO, EscalaNotas, Pregunta

# Busca un número (con signo, separadores y fracción opcional) dentro del texto.
_PATRON_NUMERO = re.compile(r"[-+]?\d[\d.,]*(?:\s*/\s*[-+]?\d[\d.,]*)?")
_MILES_CHILENOS = re.compile(r"^\d{1,3}(\.\d{3})+$")


def normalizar_texto(texto: str) -> str:
    """Minúsculas, sin tildes, sin espacios repetidos y sin punto final."""
    texto = unicodedata.normalize("NFD", texto or "")
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"\s+", " ", texto.lower()).strip()
    return texto.rstrip(".")


@dataclass
class ResultadoRespuesta:
    """Lo que la interfaz necesita mostrar después de comprobar."""

    correcta: bool
    respuesta_correcta: str
    explicacion: str


class CorrectorRespuestas:
    """Compara la respuesta del estudiante con las respuestas aceptadas."""

    # Tolerancia cuando el estudiante redondea (por ejemplo 5/6 ≈ 0,83).
    TOLERANCIA_REDONDEO = Fraction(51, 10000)

    # --- Interpretación de números -------------------------------------
    @staticmethod
    def _limpiar(texto: str) -> str:
        texto = (texto or "").strip()
        for menos in ("−", "–", "—"):
            texto = texto.replace(menos, "-")
        # "32 000" → "32000" (espacios usados como separador de miles).
        return re.sub(r"(?<=\d) (?=\d{3}\b)", "", texto)

    @classmethod
    def _interpretaciones_decimal(cls, token: str) -> set[Fraction]:
        """
        Posibles valores de un número escrito por el estudiante.

        "32.000" puede ser treinta y dos mil (Chile) o 32,0 (calculadora),
        así que se devuelven ambas lecturas y basta con que una coincida.
        """
        token = token.replace(" ", "")
        valores: set[Fraction] = set()
        try:
            if "," in token and "." in token:
                valores.add(Fraction(token.replace(".", "").replace(",", ".")))
            elif "," in token:
                valores.add(Fraction(token.replace(",", ".")))
                if re.fullmatch(r"[-+]?\d{1,3}(,\d{3})+", token):
                    valores.add(Fraction(token.replace(",", "")))
            elif "." in token:
                sin_signo = token.lstrip("+-")
                if _MILES_CHILENOS.match(sin_signo):
                    valores.add(Fraction(token.replace(".", "")))
                if token.count(".") == 1:
                    valores.add(Fraction(token))
            else:
                valores.add(Fraction(token))
        except (ValueError, ZeroDivisionError):
            pass
        return valores

    @classmethod
    def interpretar(cls, texto: str) -> set[Fraction]:
        """Todas las lecturas numéricas razonables de lo que escribió el estudiante."""
        coincidencias = _PATRON_NUMERO.findall(cls._limpiar(texto))
        if not coincidencias:
            return set()
        # Se usa el ÚLTIMO número: en "x = 12 - 5 = 7" la respuesta es 7.
        token = coincidencias[-1].strip().rstrip(".,")
        if "/" in token:
            numerador, _, denominador = token.partition("/")
            valores = set()
            for n in cls._interpretaciones_decimal(numerador.strip()):
                for d in cls._interpretaciones_decimal(denominador.strip()):
                    if d != 0:
                        valores.add(n / d)
            return valores
        return cls._interpretaciones_decimal(token)

    @staticmethod
    def valor_esperado(texto: str) -> Optional[Fraction]:
        """Valor de una respuesta guardada en la base (formato estricto: 0.75, 5/6)."""
        try:
            return Fraction(texto.strip().replace(" ", ""))
        except (ValueError, ZeroDivisionError):
            return None

    @staticmethod
    def _decimales_escritos(texto: str) -> int:
        coincidencia = re.search(r"[.,](\d+)\s*$", texto.strip())
        return len(coincidencia.group(1)) if coincidencia else 0

    # --- Comparación ----------------------------------------------------
    def es_correcta(self, pregunta: Pregunta, respuesta: str) -> bool:
        if not (respuesta or "").strip():
            return False
        if pregunta.es_alternativas:
            elegida = normalizar_texto(respuesta)
            return any(elegida == normalizar_texto(r) for r in pregunta.respuestas_aceptadas)

        candidatos = self.interpretar(respuesta)
        if not candidatos:
            return False
        redondeo = self._decimales_escritos(self._limpiar(respuesta)) >= 2
        for aceptada in pregunta.respuestas_aceptadas:
            esperado = self.valor_esperado(aceptada)
            if esperado is None:
                # Respuesta no numérica: se compara como texto.
                if normalizar_texto(respuesta) == normalizar_texto(aceptada):
                    return True
                continue
            for valor in candidatos:
                if valor == esperado:
                    return True
                if redondeo and esperado.denominator != 1 and \
                        abs(valor - esperado) <= self.TOLERANCIA_REDONDEO:
                    return True
        return False

    def corregir(self, pregunta: Pregunta, respuesta: str) -> ResultadoRespuesta:
        return ResultadoRespuesta(correcta=self.es_correcta(pregunta, respuesta),
                                  respuesta_correcta=pregunta.respuesta_para_mostrar,
                                  explicacion=pregunta.explicacion)


@dataclass
class RegistroRespuesta:
    """Guarda qué respondió el estudiante en cada pregunta."""

    pregunta: Pregunta
    respuesta: str
    correcta: bool
    uso_pista: bool


class SesionPrueba:
    """
    Una prueba corta: se responde cada pregunta una sola vez, se muestra la
    retroalimentación y se avanza. Al final entrega porcentaje y nota.
    """

    def __init__(self, preguntas: list[Pregunta], corrector: CorrectorRespuestas | None = None):
        self.preguntas = list(preguntas)
        self.corrector = corrector or CorrectorRespuestas()
        self.indice = 0
        self.historial: list[RegistroRespuesta] = []
        self._pista_actual = False
        self._respondida = False

    # --- Estado -----------------------------------------------------------
    @property
    def total(self) -> int:
        return len(self.preguntas)

    @property
    def numero(self) -> int:
        """Número de la pregunta actual, contando desde 1."""
        return min(self.indice + 1, self.total)

    @property
    def actual(self) -> Optional[Pregunta]:
        return self.preguntas[self.indice] if self.indice < self.total else None

    @property
    def respondida(self) -> bool:
        return self._respondida

    @property
    def terminada(self) -> bool:
        return self.indice >= self.total

    @property
    def correctas(self) -> int:
        return sum(1 for r in self.historial if r.correcta)

    @property
    def porcentaje(self) -> int:
        return round(100 * self.correctas / self.total) if self.total else 0

    @property
    def nota(self) -> float:
        return EscalaNotas.nota(self.correctas, self.total)

    @property
    def logrado(self) -> bool:
        return self.porcentaje >= PORCENTAJE_LOGRO

    # --- Acciones ---------------------------------------------------------
    def pista(self) -> str:
        """Devuelve la pista de la pregunta actual y lo deja registrado."""
        if self.actual is None:
            return ""
        self._pista_actual = True
        return self.actual.pista or "Vuelve a leer la clave del tema: ahí está la idea que necesitas."

    def responder(self, respuesta: str) -> ResultadoRespuesta:
        """Corrige la respuesta a la pregunta actual (solo se permite una vez)."""
        pregunta = self.actual
        if pregunta is None:
            raise RuntimeError("La prueba ya terminó.")
        if self._respondida:
            raise RuntimeError("Esta pregunta ya fue respondida.")
        resultado = self.corrector.corregir(pregunta, respuesta)
        self.historial.append(RegistroRespuesta(pregunta, respuesta, resultado.correcta,
                                                self._pista_actual))
        self._respondida = True
        return resultado

    def siguiente(self) -> bool:
        """Avanza a la próxima pregunta. Devuelve False si la prueba terminó."""
        self.indice += 1
        self._respondida = False
        self._pista_actual = False
        return not self.terminada

    def mensaje_final(self) -> str:
        """Mensaje motivador según el resultado (se muestra al terminar)."""
        if self.porcentaje == 100:
            return "¡Perfecto! Respondiste todo bien. Este tema ya es tuyo."
        if self.logrado:
            return "¡Lo lograste! Revisa las preguntas que fallaste para dejarlo redondo."
        if self.correctas > 0:
            return "Vas por buen camino. Repasa los ejemplos resueltos y vuelve a intentarlo."
        return "No pasa nada: equivocarse es parte de aprender. Lee de nuevo la clave y los ejemplos."

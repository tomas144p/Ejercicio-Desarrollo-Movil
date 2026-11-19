"""
Métricas de uso y desempeño del estudiante (Python puro, sin Kivy ni base de datos).

Sirven para ver el efecto que ha tenido Tutor Educa en cada estudiante, sea positivo o negativo:

- **Promedio inicial**: el promedio registrado al comenzar, si existe; si no, la primera nota del semestre.
- **Promedio final**: el promedio de las notas del semestre hasta hoy.
- **Variación**: final menos inicial, con «sube», «baja» o «estable» (solo con suficientes notas).
- **Aciertos del primer intento**: el porcentaje del PRIMER intento de cada tema (promedio entre temas).
- **Uso**: pruebas rendidas, temas trabajados y días con actividad.

Una variación NO prueba que Tutor Educa sea la causa: puede deberse a otras cosas. Por eso los textos siempre
acompañan la variación con cuánto practicó el estudiante y hablan de «mientras» y no de «porque».
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime

from models.modelos import UMBRAL_TENDENCIA, promedio as promedio_redondeado

MIN_NOTAS = 3             # con menos notas no se saca conclusión sobre si el promedio sube o baja
UMBRAL_PRACTICA = 3       # pruebas rendidas desde las que se considera que el estudiante «practicó»
MIN_GRUPO = 3             # estudiantes mínimos en cada grupo para comparar «con práctica» y «sin práctica»
ASIGNATURA = "mat"        # hoy Tutor Educa solo tiene Matemáticas

# Semestres de un colegio chileno (número, (mes, día) de inicio, (mes, día) de término). Enero y febrero: vacaciones.
SEMESTRES = ((1, (3, 1), (7, 31)), (2, (8, 1), (12, 31)))


# ----------------------------------------------------------------------------------------------------------
# Semestres
# ----------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Semestre:
    anio: int
    numero: int
    desde: date
    hasta: date

    @property
    def nombre(self) -> str:
        return f"{self.numero}.º semestre {self.anio}"

    def contiene(self, fecha: date | None) -> bool:
        return fecha is not None and self.desde <= fecha <= self.hasta


def _semestres_del_anio(anio: int, divisiones=SEMESTRES) -> list[Semestre]:
    return [Semestre(anio, n, date(anio, *ini), date(anio, *fin)) for n, ini, fin in divisiones]


def semestre_de(fecha: date, divisiones=SEMESTRES) -> Semestre | None:
    """El semestre que contiene la fecha, o None si cae en vacaciones (enero y febrero)."""
    return next((s for s in _semestres_del_anio(fecha.year, divisiones) if s.contiene(fecha)), None)


def semestre_actual(hoy: date | None = None, divisiones=SEMESTRES) -> Semestre:
    """El semestre de hoy; en vacaciones, el último que terminó."""
    hoy = hoy or date.today()
    actual = semestre_de(hoy, divisiones)
    if actual is not None:
        return actual
    if hoy.month <= 2:                                    # vacaciones de verano: el 2.º semestre del año anterior
        return _semestres_del_anio(hoy.year - 1, divisiones)[-1]
    return max((s for s in _semestres_del_anio(hoy.year, divisiones) if s.hasta < hoy), key=lambda s: s.hasta)


def a_fecha(texto) -> date | None:
    """«2026-11-16» o «2026-11-16 10:30:00» a fecha. Devuelve None si no se puede leer."""
    try:
        return datetime.strptime(str(texto)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


# ----------------------------------------------------------------------------------------------------------
# Métricas de un estudiante
# ----------------------------------------------------------------------------------------------------------
@dataclass
class Metricas:
    estudiante_id: int
    semestre: Semestre
    notas: int = 0
    promedio_inicial: float | None = None
    origen_inicial: str = ""             # «registrado» o «primera_nota»
    promedio_final: float | None = None
    variacion: float | None = None
    direccion: str = "sin_datos"         # sube | baja | estable | sin_datos
    pruebas: int = 0
    temas_trabajados: int = 0
    aciertos_primer_intento: float | None = None     # 0 a 100
    mejora_practica: float | None = None             # puntos de % entre el primer y el último intento de cada tema
    dias_activos: int = 0
    ultima_actividad: str | None = None

    @property
    def suficientes(self) -> bool:
        return self.notas >= MIN_NOTAS

    @property
    def practico(self) -> bool:
        return self.pruebas >= UMBRAL_PRACTICA


def calcular_metricas(estudiante_id: int, calificaciones: list, intentos: list, semestre: Semestre,
                      asignatura: str = ASIGNATURA, promedio_inicial_registrado: float | None = None) -> Metricas:
    """Calcula las métricas del estudiante dentro de un semestre. No modifica nada."""
    notas = sorted((c for c in calificaciones if c.asignatura_id == asignatura and semestre.contiene(a_fecha(c.fecha))),
                   key=lambda c: (c.fecha, c.id))
    m = Metricas(estudiante_id=estudiante_id, semestre=semestre, notas=len(notas))
    if notas:
        m.promedio_final = promedio_redondeado([c.nota for c in notas])
        if promedio_inicial_registrado is not None:
            m.promedio_inicial, m.origen_inicial = float(promedio_inicial_registrado), "registrado"
        else:
            m.promedio_inicial, m.origen_inicial = float(notas[0].nota), "primera_nota"
        m.variacion = round(m.promedio_final - m.promedio_inicial, 1)
        if not m.suficientes:
            m.direccion = "sin_datos"
        elif m.variacion >= UMBRAL_TENDENCIA:
            m.direccion = "sube"
        elif m.variacion <= -UMBRAL_TENDENCIA:
            m.direccion = "baja"
        else:
            m.direccion = "estable"

    propios = sorted((i for i in intentos if semestre.contiene(a_fecha(i.realizado_en))),
                     key=lambda i: (i.realizado_en, i.id or 0))
    m.pruebas = len(propios)
    por_tema: dict[str, list] = {}
    for intento in propios:
        por_tema.setdefault(intento.tema_id, []).append(intento)
    m.temas_trabajados = len(por_tema)
    if por_tema:
        primeros = [lista[0].porcentaje for lista in por_tema.values()]
        m.aciertos_primer_intento = round(sum(primeros) / len(primeros), 1)
        mejoras = [lista[-1].porcentaje - lista[0].porcentaje for lista in por_tema.values() if len(lista) >= 2]
        m.mejora_practica = round(sum(mejoras) / len(mejoras), 1) if mejoras else None
        dias = {a_fecha(i.realizado_en) for i in propios} - {None}
        m.dias_activos = len(dias)
        m.ultima_actividad = max(dias).isoformat() if dias else None
    return m


# ----------------------------------------------------------------------------------------------------------
# Textos (siempre con cuidado: la variación no prueba una causa)
# ----------------------------------------------------------------------------------------------------------
def nota_texto(valor: float | None) -> str:
    return "—" if valor is None else f"{valor:.1f}".replace(".", ",")


def variacion_texto(valor: float | None) -> str:
    """«+0,8», «-0,5» o «0,0»."""
    if valor is None:
        return "—"
    signo = "+" if valor > 0 else ""
    return f"{signo}{valor:.1f}".replace(".", ",")


def _puntos(valor: float) -> str:
    if abs(valor) == 1:
        return "1 punto"
    return f"{abs(valor):.1f}".replace(".", ",") + " puntos"


def _pruebas(n: int) -> str:
    return f"{n} {'prueba' if n == 1 else 'pruebas'}"


def lectura(m: Metricas, para: str = "docente", nombre: str = "") -> str:
    """Una frase que resume el efecto, en el tono de quien la lee («docente» o «apoderado»)."""
    de = nombre or "el estudiante"
    if m.notas == 0:
        return "Todavía no hay notas en este semestre para comparar."
    if not m.suficientes:
        faltan = MIN_NOTAS - m.notas
        return (f"Aún hay pocas notas ({m.notas}) para sacar conclusiones: faltan {faltan} "
                f"más para comparar el promedio.")
    if para == "apoderado":
        if m.direccion == "sube":
            return f"¡Buenas noticias! El promedio de {de} subió {_puntos(m.variacion)} en este semestre."
        if m.direccion == "baja":
            base = f"El promedio de {de} bajó {_puntos(m.variacion)} en este semestre."
            return base + (" Está practicando; conviene conversar con su docente para ver cómo apoyarlo."
                           if m.practico else " Practicar unos minutos al día en Tutor Educa puede ayudar.")
        return f"El promedio de {de} se ha mantenido estable en este semestre."
    practica = f"practicó {_pruebas(m.pruebas)}" if m.pruebas else "todavía no practica en Tutor Educa"
    if m.direccion == "sube":
        cierre = (" Buen avance; otras cosas también pueden influir." if m.practico
                  else " Ha practicado poco: la mejora puede venir de otras cosas.")
        return f"El promedio subió {_puntos(m.variacion)} y {practica}.{cierre}"
    if m.direccion == "baja":
        cierre = (" Conviene conversar para ver qué le dificulta avanzar." if m.practico
                  else " Podría ayudar desbloquearle un refuerzo.")
        return f"El promedio bajó {_puntos(m.variacion)} y {practica}.{cierre}"
    return f"El promedio se mantiene estable y {practica}."


# ----------------------------------------------------------------------------------------------------------
# Resumen de un curso
# ----------------------------------------------------------------------------------------------------------
@dataclass
class ResumenEfecto:
    estudiantes: int = 0
    con_datos: int = 0                   # los que tienen notas suficientes para comparar
    subieron: int = 0
    bajaron: int = 0
    estables: int = 0
    variacion_promedio: float | None = None
    aciertos_primer_intento: float | None = None
    sin_practica: int = 0                # estudiantes con menos de UMBRAL_PRACTICA pruebas
    variacion_con_practica: float | None = None
    n_con_practica: int = 0
    variacion_sin_practica: float | None = None
    n_sin_practica: int = 0

    @property
    def comparacion_confiable(self) -> bool:
        """Solo se compara «con práctica» y «sin práctica» si ambos grupos tienen al menos MIN_GRUPO estudiantes."""
        return self.n_con_practica >= MIN_GRUPO and self.n_sin_practica >= MIN_GRUPO


def _promedio(valores: list[float]) -> float | None:
    return round(sum(valores) / len(valores), 1) if valores else None


def resumen_curso(metricas: list[Metricas]) -> ResumenEfecto:
    r = ResumenEfecto(estudiantes=len(metricas))
    con_datos = [m for m in metricas if m.suficientes]
    r.con_datos = len(con_datos)
    r.subieron = sum(1 for m in con_datos if m.direccion == "sube")
    r.bajaron = sum(1 for m in con_datos if m.direccion == "baja")
    r.estables = sum(1 for m in con_datos if m.direccion == "estable")
    r.variacion_promedio = _promedio([m.variacion for m in con_datos])
    r.aciertos_primer_intento = _promedio([m.aciertos_primer_intento for m in metricas
                                           if m.aciertos_primer_intento is not None])
    r.sin_practica = sum(1 for m in metricas if not m.practico)
    con = [m.variacion for m in con_datos if m.practico]
    sin = [m.variacion for m in con_datos if not m.practico]
    r.n_con_practica, r.n_sin_practica = len(con), len(sin)
    r.variacion_con_practica, r.variacion_sin_practica = _promedio(con), _promedio(sin)
    return r


# ----------------------------------------------------------------------------------------------------------
# Exportar a CSV (se abre directo en Excel en español: separador «;», decimales con coma y BOM)
# ----------------------------------------------------------------------------------------------------------
COLUMNAS_CSV = ("estudiante", "curso", "semestre", "notas", "promedio_inicial", "origen_inicial", "promedio_final",
                "variacion", "direccion", "pruebas", "temas_trabajados", "aciertos_primer_intento_pct",
                "mejora_por_practica_pct", "dias_activos", "ultima_actividad")


def a_csv(filas: list[tuple[str, str, Metricas]], anonimo: bool = False) -> str:
    """``filas``: (nombre del estudiante, nombre del curso, métricas). Anónimo: «Estudiante 01», «Estudiante 02»…"""
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";", lineterminator="\r\n")
    escritor.writerow(COLUMNAS_CSV)

    def dec(valor):
        return "" if valor is None else str(valor).replace(".", ",")

    for posicion, (nombre, curso, m) in enumerate(filas, start=1):
        escritor.writerow([f"Estudiante {posicion:02d}" if anonimo else nombre, curso, m.semestre.nombre, m.notas,
                           dec(m.promedio_inicial), m.origen_inicial, dec(m.promedio_final), dec(m.variacion),
                           m.direccion, m.pruebas, m.temas_trabajados, dec(m.aciertos_primer_intento),
                           dec(m.mejora_practica), m.dias_activos, m.ultima_actividad or ""])
    return "\ufeff" + salida.getvalue()

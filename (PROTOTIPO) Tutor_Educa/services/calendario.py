"""
Calendario escolar: qué días hay clases, cómo se calcula la asistencia y qué eventos hay (tareas 20 y 24).

Python puro (sin Kivy, sin SQL, sin FastAPI): lo usan la app, el servidor y las pruebas, así las reglas son
EXACTAMENTE las mismas en el celular (sin conexión) y en el servidor.

Reglas decididas:
- Hay clases de lunes a viernes. El **sábado** solo si el curso lo tiene activado (apagado por defecto).
  El **domingo nunca**: no se puede pasar lista un domingo, ni desde la app ni desde el servidor.
- Un **feriado** (o cualquier evento marcado «sin clases») no permite pasar lista y no cuenta en el porcentaje.
- Se pasa lista **solo por excepción**: todos aparecen presentes y se marcan los ausentes. Por eso la base guarda
  (1) los días en que se pasó lista y (2) solo los ausentes. Un día sin lista no cuenta (ni a favor ni en contra).
- **Porcentaje de asistencia** = días en que asistió ÷ días con lista. La inasistencia **justificada** se muestra
  aparte, pero cuenta como inasistencia en el porcentaje (así lo calcula el sistema escolar chileno). Para
  confirmar con docentes.
- Las fechas son **solo día** (``AAAA-MM-DD``), sin hora, y «hoy» se mide en la zona de Chile.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
FORMATO_DIA = "%Y-%m-%d"

PRESENTE = "presente"
AUSENTE = "ausente"
JUSTIFICADO = "justificado"
ESTADOS = (PRESENTE, AUSENTE, JUSTIFICADO)
ESTADOS_GUARDADOS = (AUSENTE, JUSTIFICADO)          # el presente no se guarda: es lo que queda si no hay excepción
NOMBRES_ESTADO = {PRESENTE: "Presente", AUSENTE: "Ausente", JUSTIFICADO: "Ausente justificado"}
# Ícono (Lucide) de cada estado: nunca solo color, también forma y palabra (se lee bien con poca visión del color).
ICONO_ESTADO = {PRESENTE: "check", AUSENTE: "x", JUSTIFICADO: "file-text"}

# tipo -> (nombre que se muestra, ¿hay clases ese día por defecto?)
TIPOS_EVENTO = {
    "feriado": ("Feriado", False),
    "sin_clases": ("Sin clases", False),
    "celebracion": ("Celebración", True),
    "evaluacion": ("Evaluación", True),
    "reunion": ("Reunión de apoderados", True),
    "otro": ("Otro", True),
}
MAX_DIAS_EVENTO = 120          # un evento dura como máximo ~4 meses (las vacaciones de verano caben en dos eventos)
MAX_DIAS_ATRAS = 400           # no se pasa lista de días más antiguos que esto
ALERTA_INASISTENCIAS_SEGUIDAS = 3
NOMBRES_DIA = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
NOMBRES_MES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
               "noviembre", "diciembre")


# ---------------------------------------------------------------------------
# Fechas (solo día, zona de Chile)
# ---------------------------------------------------------------------------
def _primer_domingo(anio: int, mes: int) -> date:
    d = date(anio, mes, 1)
    return d + timedelta(days=(6 - d.weekday()) % 7)


def _chile_sin_zoneinfo(ahora_utc: datetime) -> datetime:
    """Hora de Chile continental calculada a mano (por si el sistema no trae la base de zonas horarias, algo
    frecuente en Android y en contenedores mínimos). Horario de verano (UTC-3): desde el primer domingo de
    septiembre hasta el primer domingo de abril. Basta para saber en qué DÍA estamos."""
    anio = ahora_utc.year
    verano = ahora_utc.date() >= _primer_domingo(anio, 9) or ahora_utc.date() < _primer_domingo(anio, 4)
    return ahora_utc + timedelta(hours=-3 if verano else -4)


def ahora_chile(ahora_utc: datetime | None = None) -> datetime:
    """La fecha y hora de Chile (sin zona, para guardar y mostrar). ``ahora_utc`` existe para poder probarlo."""
    ahora = ahora_utc or datetime.now(timezone.utc)
    if ahora.tzinfo is None:
        ahora = ahora.replace(tzinfo=timezone.utc)
    ahora = ahora.astimezone(timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        return ahora.astimezone(ZoneInfo("America/Santiago")).replace(tzinfo=None)
    except Exception:     # sin base de zonas horarias
        return _chile_sin_zoneinfo(ahora).replace(tzinfo=None)


def hoy_chile(ahora_utc: datetime | None = None) -> date:
    """El día de hoy en Chile."""
    return ahora_chile(ahora_utc).date()


def parsear_dia(texto) -> date:
    """«2026-11-18» -> fecha. Solo ese formato (sin hora); cualquier otra cosa es un error."""
    if isinstance(texto, date) and not isinstance(texto, datetime):
        return texto
    if not isinstance(texto, str) or len(texto) != 10:
        raise ValueError("La fecha debe verse así: 2026-11-18.")
    try:
        return datetime.strptime(texto, FORMATO_DIA).date()
    except ValueError as error:
        raise ValueError("La fecha no es válida. Debe verse así: 2026-11-18.") from error


def a_texto(dia: date) -> str:
    return dia.strftime(FORMATO_DIA)


def dia_de(valor) -> str:
    """Normaliza lo que entrega la base de datos (texto, fecha o fecha con hora) a «AAAA-MM-DD»."""
    if isinstance(valor, datetime):
        return a_texto(valor.date())
    if isinstance(valor, date):
        return a_texto(valor)
    return str(valor or "")[:10]


def desde_texto_chileno(texto: str) -> str:
    """«18/11/2026» (o «18-11-2026», «18.11.2026») -> «2026-11-18». Lo que escribe una persona en un formulario."""
    limpio = (texto or "").strip().replace("-", "/").replace(".", "/")
    partes = limpio.split("/")
    if len(partes) != 3 or not all(p.isdigit() for p in partes):
        raise ValueError("Escribe la fecha así: 18/11/2026.")
    dia, mes, anio = (int(p) for p in partes)
    if anio < 100:
        anio += 2000
    try:
        return a_texto(date(anio, mes, dia))
    except ValueError as error:
        raise ValueError("Esa fecha no existe en el calendario. Revisa el día y el mes.") from error


def a_texto_chileno(dia: date | str) -> str:
    d = parsear_dia(dia) if isinstance(dia, str) else dia
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def texto_rango(inicio, fin) -> str:
    """«viernes 20 de noviembre» o «del 20 al 24 de noviembre» (un evento de varios días)."""
    i, f = (parsear_dia(x) if isinstance(x, str) else x for x in (dia_de(inicio), dia_de(fin)))
    if i == f:
        return fecha_legible(i)
    if (i.year, i.month) == (f.year, f.month):
        return f"del {i.day} al {f.day} de {NOMBRES_MES[f.month - 1]}"
    return f"del {fecha_legible(i, False)} al {fecha_legible(f, False)}"


ICONO_TIPO_EVENTO = {"feriado": "flag", "sin_clases": "calendar-off", "celebracion": "party-popper",
                     "evaluacion": "clipboard-check", "reunion": "users", "otro": "calendar"}


def nombre_dia(dia: date) -> str:
    return NOMBRES_DIA[dia.weekday()]


def fecha_legible(dia: date | str, con_dia_semana: bool = True) -> str:
    """«miércoles 18 de noviembre»."""
    d = parsear_dia(dia) if isinstance(dia, str) else dia
    base = f"{d.day} de {NOMBRES_MES[d.month - 1]}"
    return f"{nombre_dia(d)} {base}" if con_dia_semana else base


# ---------------------------------------------------------------------------
# Eventos y feriados
# ---------------------------------------------------------------------------
def _activo(evento: dict) -> bool:
    return bool(int(evento.get("activo", 1)))


def evento_cubre(evento: dict, dia: date | str) -> bool:
    d = a_texto(dia) if isinstance(dia, date) else str(dia)
    return dia_de(evento["fecha_inicio"]) <= d <= dia_de(evento["fecha_fin"])


def eventos_del_dia(eventos: list[dict], dia: date | str, curso_id: int | None = None) -> list[dict]:
    """Los eventos activos que caen ese día y que valen para el curso (los de todo el colegio valen para todos)."""
    return [e for e in eventos
            if _activo(e) and evento_cubre(e, dia)
            and (e.get("curso_id") is None or curso_id is None or int(e["curso_id"]) == int(curso_id))]


@dataclass
class EstadoDia:
    con_clases: bool
    motivo: str = ""                  # por qué no hay clases (si no las hay)
    eventos: list[dict] = field(default_factory=list)


def estado_del_dia(dia: date | str, clases_sabado: bool, eventos: list[dict], curso_id: int | None = None) -> EstadoDia:
    """¿Hay clases ese día en ese curso? Domingo nunca; sábado solo si el curso lo activó; feriado nunca."""
    d = parsear_dia(dia) if isinstance(dia, str) else dia
    del_dia = eventos_del_dia(eventos, d, curso_id)
    if d.weekday() == 6:
        return EstadoDia(False, "Los domingos no hay clases.", del_dia)
    if d.weekday() == 5 and not clases_sabado:
        return EstadoDia(False, "Este curso no tiene clases los sábados.", del_dia)
    for evento in del_dia:
        if not int(evento.get("hay_clases", 1)):
            tipo = TIPOS_EVENTO.get(evento.get("tipo"), ("", True))[0]
            etiqueta = f"{tipo}: {evento['titulo']}" if tipo and tipo.lower() not in evento["titulo"].lower() \
                else evento["titulo"]
            return EstadoDia(False, f"{etiqueta}. No hay clases.", del_dia)
    return EstadoDia(True, "", del_dia)


def validar_dia_de_lista(dia: str, hoy: date, clases_sabado: bool, eventos: list[dict],
                         curso_id: int | None = None) -> str:
    """Devuelve ``""`` si se puede pasar lista ese día, o el motivo en lenguaje simple."""
    try:
        d = parsear_dia(dia)
    except ValueError as error:
        return str(error)
    if d > hoy:
        return "No se puede pasar lista de un día que todavía no llega."
    if (hoy - d).days > MAX_DIAS_ATRAS:
        return "Ese día es demasiado antiguo para pasar lista."
    estado = estado_del_dia(d, clases_sabado, eventos, curso_id)
    return "" if estado.con_clases else estado.motivo


def validar_evento(titulo: str, tipo: str, fecha_inicio: str, fecha_fin: str) -> str:
    """Motivo por el que un evento no es válido, o ``""``."""
    if tipo not in TIPOS_EVENTO:
        return "Ese tipo de evento no existe."
    try:
        inicio, fin = parsear_dia(fecha_inicio), parsear_dia(fecha_fin)
    except ValueError as error:
        return str(error)
    if fin < inicio:
        return "La fecha de término no puede ser anterior a la de inicio."
    if (fin - inicio).days + 1 > MAX_DIAS_EVENTO:
        return f"Un evento puede durar como máximo {MAX_DIAS_EVENTO} días."
    if not (2020 <= inicio.year <= 2100 and 2020 <= fin.year <= 2100):
        return "El año del evento no es válido."
    if not (titulo or "").strip():
        return "El evento necesita un título."
    return ""


def hay_clases_por_defecto(tipo: str) -> bool:
    return TIPOS_EVENTO.get(tipo, ("", True))[1]


# ---------------------------------------------------------------------------
# Días con clases y asistencia
# ---------------------------------------------------------------------------
def dias_en_rango(desde: date, hasta: date) -> list[date]:
    return [desde + timedelta(days=n) for n in range((hasta - desde).days + 1)]


def dias_con_clases(desde: date, hasta: date, clases_sabado: bool, eventos: list[dict],
                    curso_id: int | None = None) -> list[date]:
    return [d for d in dias_en_rango(desde, hasta) if estado_del_dia(d, clases_sabado, eventos, curso_id).con_clases]


def dias_validos_con_lista(dias_con_lista: set[str], clases_sabado: bool, eventos: list[dict],
                           curso_id: int | None = None) -> list[str]:
    """Los días en que se pasó lista y que siguen contando: si después se apagó el sábado o se agregó un feriado
    en un día con lista, ese día se conserva en el historial pero ya no entra en el porcentaje."""
    validos = []
    for texto in sorted(dias_con_lista):
        try:
            if estado_del_dia(parsear_dia(texto), clases_sabado, eventos, curso_id).con_clases:
                validos.append(texto)
        except ValueError:
            continue
    return validos


@dataclass
class ResumenAsistencia:
    dias: int = 0                     # días con lista que cuentan
    presentes: int = 0
    ausentes: int = 0
    justificados: int = 0
    porcentaje: int | None = None     # None = todavía no se ha pasado lista
    seguidas: int = 0                 # inasistencias seguidas más recientes (ausente o justificado)

    @property
    def hay_datos(self) -> bool:
        return self.dias > 0

    @property
    def inasistencias(self) -> int:
        return self.ausentes + self.justificados

    @property
    def alerta_seguidas(self) -> bool:
        return self.seguidas >= ALERTA_INASISTENCIAS_SEGUIDAS


def _porcentaje(presentes: int, dias: int) -> int | None:
    return None if dias <= 0 else int(100 * presentes / dias + 0.5)


def resumen_asistencia(dias_validos: list[str], excepciones: dict[str, str]) -> ResumenAsistencia:
    """``dias_validos``: días con lista que cuentan (ordenados). ``excepciones``: {día: «ausente» o «justificado»}
    de UN estudiante. Todo día con lista sin excepción es una asistencia."""
    dias = len(dias_validos)
    ausentes = sum(1 for d in dias_validos if excepciones.get(d) == AUSENTE)
    justificados = sum(1 for d in dias_validos if excepciones.get(d) == JUSTIFICADO)
    presentes = dias - ausentes - justificados
    seguidas = 0
    for d in reversed(dias_validos):
        if excepciones.get(d) in ESTADOS_GUARDADOS:
            seguidas += 1
        else:
            break
    return ResumenAsistencia(dias, presentes, ausentes, justificados, _porcentaje(presentes, dias), seguidas)


def resumen_del_curso(dias_validos: list[str], excepciones_por_estudiante: dict[int, dict[str, str]],
                      estudiante_ids: list[int]) -> dict[int, ResumenAsistencia]:
    return {i: resumen_asistencia(dias_validos, excepciones_por_estudiante.get(i, {})) for i in estudiante_ids}


def estado_de(dia: str, dias_con_lista: set[str], excepciones: dict[str, str]) -> str | None:
    """«presente», «ausente», «justificado» o ``None`` si ese día no se pasó lista."""
    if dia not in dias_con_lista:
        return None
    return excepciones.get(dia, PRESENTE)


# ---------------------------------------------------------------------------
# Cuadrícula de un mes (para dibujar el calendario)
# ---------------------------------------------------------------------------
def semanas_del_mes(anio: int, mes: int) -> list[list[date | None]]:
    """Semanas de lunes a domingo; los espacios fuera del mes quedan en ``None``."""
    primero = date(anio, mes, 1)
    siguiente = date(anio + (mes == 12), mes % 12 + 1, 1)
    ultimo = siguiente - timedelta(days=1)
    dias: list[date | None] = [None] * primero.weekday() + dias_en_rango(primero, ultimo)
    dias += [None] * ((-len(dias)) % 7)
    return [dias[i:i + 7] for i in range(0, len(dias), 7)]


def mes_vecino(anio: int, mes: int, delta: int) -> tuple[int, int]:
    n = anio * 12 + (mes - 1) + delta
    return n // 12, n % 12 + 1


# ---------------------------------------------------------------------------
# Feriados de Chile (precargados; el administrador los puede editar)
# ---------------------------------------------------------------------------
# Revisar CADA AÑO contra la ley vigente: pueden cambiar o moverse. Se incluyen todos los feriados nacionales,
# también los que caen en fin de semana (no molestan: sábado sin clases y domingo nunca tienen clases).
# 2026: 16 feriados nacionales. 2027: 17 (incluye el viernes 17 de septiembre por la Ley 20.983, porque el 18 es sábado).
FERIADOS_CHILE: dict[int, list[tuple[str, str]]] = {
    2026: [("2026-01-01", "Año Nuevo"), ("2026-04-03", "Viernes Santo"), ("2026-04-04", "Sábado Santo"),
           ("2026-05-01", "Día del Trabajo"), ("2026-05-21", "Día de las Glorias Navales"),
           ("2026-06-21", "Día Nacional de los Pueblos Indígenas"), ("2026-06-29", "San Pedro y San Pablo"),
           ("2026-07-16", "Virgen del Carmen"), ("2026-08-15", "Asunción de la Virgen"),
           ("2026-09-18", "Independencia Nacional"), ("2026-09-19", "Día de las Glorias del Ejército"),
           ("2026-10-12", "Encuentro de Dos Mundos"), ("2026-10-31", "Día de las Iglesias Evangélicas"),
           ("2026-11-01", "Día de Todos los Santos"), ("2026-12-08", "Inmaculada Concepción"),
           ("2026-12-25", "Navidad")],
    2027: [("2027-01-01", "Año Nuevo"), ("2027-03-26", "Viernes Santo"), ("2027-03-27", "Sábado Santo"),
           ("2027-05-01", "Día del Trabajo"), ("2027-05-21", "Día de las Glorias Navales"),
           ("2027-06-20", "Día Nacional de los Pueblos Indígenas"), ("2027-06-28", "San Pedro y San Pablo"),
           ("2027-07-16", "Virgen del Carmen"), ("2027-08-15", "Asunción de la Virgen"),
           ("2027-09-17", "Feriado adicional de Fiestas Patrias"), ("2027-09-18", "Independencia Nacional"),
           ("2027-09-19", "Día de las Glorias del Ejército"), ("2027-10-11", "Encuentro de Dos Mundos"),
           ("2027-10-31", "Día de las Iglesias Evangélicas"), ("2027-11-01", "Día de Todos los Santos"),
           ("2027-12-08", "Inmaculada Concepción"), ("2027-12-25", "Navidad")],
}


def anios_con_feriados() -> list[int]:
    return sorted(FERIADOS_CHILE)


def feriados_de(anio: int) -> list[tuple[str, str]]:
    """[(día, nombre)] de los feriados nacionales precargados de ese año (vacío si no los tenemos)."""
    return list(FERIADOS_CHILE.get(int(anio), []))


def codigo_feriado(colegio_id: int, dia: str) -> str:
    """Código fijo: cargar los feriados dos veces no los duplica."""
    return f"feriado-cl-{int(colegio_id)}-{dia}"

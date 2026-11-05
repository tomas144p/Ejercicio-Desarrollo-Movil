"""
Modelos del dominio de Tutor Educa.

Cada clase representa un concepto del colegio (usuario, asignatura, nota,
tema, pregunta, refuerzo, intento, aviso...). Se usan ``dataclasses`` para
escribir menos código repetido, y herencia para los tres tipos de usuario:

    Usuario  ─┬─ Estudiante
              ├─ Docente
              └─ Apoderado

Las clases no saben nada de Kivy ni de SQL: solo guardan datos y reglas.
Por eso se pueden reutilizar en la interfaz, en la base de datos y en las
pruebas automáticas.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import ClassVar, Optional

# Promedio bajo el cual el docente ve a un estudiante como "necesita refuerzo".
UMBRAL_REFUERZO = 5.0


def ahora_iso() -> str:
    """Fecha y hora actual en el formato que usan ambas bases de datos."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def redondear(valor: float, decimales: int = 1) -> float:
    """Redondeo escolar chileno: 5,15 → 5,2 (Python por defecto daría 5,1)."""
    cuantizador = Decimal(1).scaleb(-decimales)
    return float(Decimal(str(valor)).quantize(cuantizador, rounding=ROUND_HALF_UP))


# ---------------------------------------------------------------------------
# Usuarios
# ---------------------------------------------------------------------------
class Rol:
    """Constantes de los perfiles de ingreso."""

    ESTUDIANTE = "estudiante"
    DOCENTE = "docente"
    APODERADO = "apoderado"
    TODOS = (ESTUDIANTE, DOCENTE, APODERADO)
    NOMBRES = {ESTUDIANTE: "Estudiante", DOCENTE: "Docente", APODERADO: "Apoderado/a"}


@dataclass
class Usuario:
    """Persona que ingresa a la app. El rol lo define la subclase."""

    id: int
    correo: str
    nombre: str

    ROL: ClassVar[str] = ""
    PANTALLA_INICIO: ClassVar[str] = "ingreso"

    @property
    def rol(self) -> str:
        return self.ROL

    @property
    def nombre_rol(self) -> str:
        return Rol.NOMBRES.get(self.ROL, "Usuario")

    @property
    def primer_nombre(self) -> str:
        return self.nombre.split()[0] if self.nombre else ""

    @property
    def iniciales(self) -> str:
        partes = [p for p in self.nombre.split() if p]
        return "".join(p[0] for p in partes[:2]).upper() or "?"

    @staticmethod
    def desde_fila(fila: dict) -> "Usuario":
        """
        Fábrica: crea la subclase correcta según la columna ``rol``.

        Es la razón por la que basta el correo para saber a qué pantalla
        entra cada persona: la base de datos guarda el rol de cada correo.
        """
        clases = {Rol.ESTUDIANTE: Estudiante, Rol.DOCENTE: Docente, Rol.APODERADO: Apoderado}
        clase = clases.get(fila.get("rol"))
        if clase is None:
            raise ValueError(f"Rol desconocido: {fila.get('rol')!r}")
        return clase(id=int(fila["id"]), correo=fila["correo"], nombre=fila["nombre"])


@dataclass
class Estudiante(Usuario):
    ROL: ClassVar[str] = Rol.ESTUDIANTE
    PANTALLA_INICIO: ClassVar[str] = "estudiante"


@dataclass
class Docente(Usuario):
    ROL: ClassVar[str] = Rol.DOCENTE
    PANTALLA_INICIO: ClassVar[str] = "docente"


@dataclass
class Apoderado(Usuario):
    ROL: ClassVar[str] = Rol.APODERADO
    PANTALLA_INICIO: ClassVar[str] = "apoderado"


# ---------------------------------------------------------------------------
# Escala de notas chilena
# ---------------------------------------------------------------------------
class EscalaNotas:
    """
    Convierte un puntaje en nota de 1,0 a 7,0 con exigencia del 60 %.

    Con 60 % de logro se obtiene un 4,0 (nota de aprobación en Chile).
    """

    EXIGENCIA = 0.6
    MINIMA, APROBACION, MAXIMA = 1.0, 4.0, 7.0

    @classmethod
    def nota(cls, correctas: int, total: int) -> float:
        if total <= 0:
            return cls.MINIMA
        logro = max(0.0, min(1.0, correctas / total))
        if logro < cls.EXIGENCIA:
            valor = cls.MINIMA + (cls.APROBACION - cls.MINIMA) * logro / cls.EXIGENCIA
        else:
            valor = cls.APROBACION + (cls.MAXIMA - cls.APROBACION) * (
                (logro - cls.EXIGENCIA) / (1 - cls.EXIGENCIA))
        return redondear(valor)

    @staticmethod
    def formatear(nota: Optional[float]) -> str:
        """6.25 → "6,3" (coma decimal, como se escribe en Chile)."""
        if nota is None:
            return "–"
        return f"{redondear(nota):.1f}".replace(".", ",")

    @staticmethod
    def categoria(nota: Optional[float]) -> str:
        """Categoría usada por la interfaz para elegir el color de la nota."""
        if nota is None:
            return "sin_nota"
        if nota < 4.0:
            return "insuficiente"
        if nota < 5.0:
            return "en_riesgo"
        if nota < 6.0:
            return "adecuado"
        return "destacado"


def promedio(notas: list[float]) -> Optional[float]:
    """Promedio redondeado a un decimal, o None si no hay notas."""
    return redondear(sum(notas) / len(notas)) if notas else None


# ---------------------------------------------------------------------------
# Colegio
# ---------------------------------------------------------------------------
@dataclass
class Curso:
    id: int
    nombre: str
    nivel: str
    docente_id: int
    anio: int = 2026


@dataclass
class Asignatura:
    id: str
    nombre: str
    icono: str
    color: str
    tiene_tutor: bool = False
    orden: int = 0


@dataclass
class Calificacion:
    id: int
    estudiante_id: int
    asignatura_id: str
    nota: float
    descripcion: str = ""
    fecha: str = ""


# ---------------------------------------------------------------------------
# Contenido de estudio
# ---------------------------------------------------------------------------
@dataclass
class Tema:
    """Una unidad de refuerzo (por ejemplo "Ecuaciones de primer grado")."""

    id: str
    asignatura_id: str
    titulo: str
    nivel: str
    orden: int
    resumen: str
    contenido: str          # párrafos separados por una línea en blanco
    clave: str              # la idea más importante ("La clave")
    error_comun: str        # error frecuente que conviene evitar
    consejo_apoderado: str  # cómo puede ayudar la familia en casa
    icono: str = "book-open"

    @property
    def parrafos(self) -> list[str]:
        return [p.strip() for p in self.contenido.split("\n\n") if p.strip()]


@dataclass
class PasoEjemplo:
    """Una línea del cuaderno: la expresión y una nota que explica el paso."""

    expresion: str
    nota: str = ""


@dataclass
class Ejemplo:
    id: int
    tema_id: str
    orden: int
    titulo: str
    enunciado: str
    pasos_texto: str        # una línea por paso:  "expresión || explicación"
    resultado: str
    comprobacion: str = ""

    @property
    def pasos(self) -> list[PasoEjemplo]:
        pasos = []
        for linea in self.pasos_texto.splitlines():
            if not linea.strip():
                continue
            expresion, _, nota = linea.partition("||")
            pasos.append(PasoEjemplo(expresion.strip(), nota.strip()))
        return pasos


@dataclass
class Pregunta:
    """Pregunta de la prueba. Puede ser numérica o de alternativas."""

    id: int
    tema_id: str
    orden: int
    enunciado: str
    tipo: str               # "numerica" | "alternativas"
    alternativas_texto: str  # alternativas separadas por "|"
    respuesta: str          # respuesta correcta ("|" separa respuestas válidas)
    pista: str = ""
    explicacion: str = ""

    NUMERICA: ClassVar[str] = "numerica"
    ALTERNATIVAS: ClassVar[str] = "alternativas"

    @property
    def es_alternativas(self) -> bool:
        return self.tipo == self.ALTERNATIVAS

    @property
    def alternativas(self) -> list[str]:
        return [a.strip() for a in self.alternativas_texto.split("|") if a.strip()]

    @property
    def respuestas_aceptadas(self) -> list[str]:
        return [r.strip() for r in self.respuesta.split("|") if r.strip()]

    @property
    def respuesta_para_mostrar(self) -> str:
        """La primera respuesta aceptada, escrita como en Chile (32.000 y 0,75)."""
        principal = self.respuestas_aceptadas[0] if self.respuestas_aceptadas else ""
        if self.es_alternativas or "/" in principal:
            return principal.replace("-", "−")
        try:
            numero = float(principal)
        except ValueError:
            return principal
        if numero.is_integer():
            texto = f"{int(numero):,}".replace(",", ".")
        else:
            texto = f"{numero:g}".replace(".", ",")
        return texto.replace("-", "−")


# ---------------------------------------------------------------------------
# Refuerzos, intentos y avisos
# ---------------------------------------------------------------------------
class EstadoRefuerzo:
    """Estados por los que pasa un tema desbloqueado. Nunca retrocede."""

    DISPONIBLE = "disponible"
    EN_PROGRESO = "en_progreso"
    LOGRADO = "logrado"
    ORDEN = {DISPONIBLE: 0, EN_PROGRESO: 1, LOGRADO: 2}
    NOMBRES = {DISPONIBLE: "Nuevo", EN_PROGRESO: "En curso", LOGRADO: "Logrado"}

    @classmethod
    def es_avance(cls, actual: str, nuevo: str) -> bool:
        """True si pasar de ``actual`` a ``nuevo`` es avanzar (no retroceder)."""
        return cls.ORDEN.get(nuevo, 0) > cls.ORDEN.get(actual, 0)


@dataclass
class Refuerzo:
    """Un tema que el docente desbloqueó para un estudiante."""

    id: int
    estudiante_id: int
    tema_id: str
    estado: str = EstadoRefuerzo.DISPONIBLE
    mensaje: str = ""
    desbloqueado_por: Optional[int] = None
    desbloqueado_en: str = ""
    actualizado_en: str = ""
    activo: bool = True
    tema: Optional[Tema] = None     # se completa desde el servicio de datos

    @property
    def nombre_estado(self) -> str:
        return EstadoRefuerzo.NOMBRES.get(self.estado, self.estado)


# Porcentaje mínimo en la prueba para marcar un tema como logrado.
PORCENTAJE_LOGRO = 60


@dataclass
class Intento:
    """Resultado de una prueba rendida por un estudiante."""

    id: Optional[int]
    codigo: str
    estudiante_id: int
    tema_id: str
    correctas: int
    total: int
    porcentaje: int
    nota: float
    realizado_en: str
    origen: str = "app"

    @property
    def logrado(self) -> bool:
        return self.porcentaje >= PORCENTAJE_LOGRO

    @classmethod
    def nuevo(cls, estudiante_id: int, tema_id: str, correctas: int, total: int,
              origen: str = "app") -> "Intento":
        porcentaje = round(100 * correctas / total) if total else 0
        return cls(id=None, codigo=uuid.uuid4().hex, estudiante_id=estudiante_id,
                   tema_id=tema_id, correctas=correctas, total=total,
                   porcentaje=porcentaje, nota=EscalaNotas.nota(correctas, total),
                   realizado_en=ahora_iso(), origen=origen)


@dataclass
class Aviso:
    """Mensaje del docente para los apoderados (de todo el curso o de uno)."""

    id: Optional[int]
    codigo: str
    curso_id: int
    estudiante_id: Optional[int]
    autor_id: int
    titulo: str
    cuerpo: str
    tipo: str = "info"          # "info" | "evaluacion" | "refuerzo" | "logro"
    creado_en: str = ""
    leido: bool = False         # para el apoderado que lo está viendo
    lectores: int = 0           # para el docente: cuántos apoderados lo leyeron
    pendiente: bool = False     # creado sin conexión y aún no enviado

    @classmethod
    def nuevo(cls, curso_id: int, autor_id: int, titulo: str, cuerpo: str,
              estudiante_id: Optional[int] = None, tipo: str = "info") -> "Aviso":
        return cls(id=None, codigo=uuid.uuid4().hex, curso_id=curso_id,
                   estudiante_id=estudiante_id, autor_id=autor_id, titulo=titulo.strip(),
                   cuerpo=cuerpo.strip(), tipo=tipo, creado_en=ahora_iso())


@dataclass
class FichaEstudiante:
    """Todo lo que la app sabe de un estudiante (lo usan docente y apoderado)."""

    estudiante: Estudiante
    curso: Optional[Curso] = None
    asistencia: int = 0
    apoderado_nombre: str = ""
    calificaciones: list[Calificacion] = field(default_factory=list)
    refuerzos: list[Refuerzo] = field(default_factory=list)
    intentos: list[Intento] = field(default_factory=list)

    def notas_de(self, asignatura_id: str) -> list[float]:
        return [c.nota for c in self.calificaciones if c.asignatura_id == asignatura_id]

    def promedio(self, asignatura_id: str) -> Optional[float]:
        return promedio(self.notas_de(asignatura_id))

    @property
    def promedio_general(self) -> Optional[float]:
        asignaturas = sorted({c.asignatura_id for c in self.calificaciones})
        promedios = [self.promedio(a) for a in asignaturas]
        return promedio([p for p in promedios if p is not None])

    @property
    def necesita_refuerzo(self) -> bool:
        """Regla usada por el docente: promedio de Matemáticas bajo 5,0."""
        mate = self.promedio("mat")
        return mate is not None and mate < UMBRAL_REFUERZO

    @property
    def refuerzos_activos(self) -> list[Refuerzo]:
        return [r for r in self.refuerzos if r.activo]

    def mejor_intento(self, tema_id: str) -> Optional[Intento]:
        propios = [i for i in self.intentos if i.tema_id == tema_id]
        return max(propios, key=lambda i: (i.porcentaje, i.realizado_en), default=None)

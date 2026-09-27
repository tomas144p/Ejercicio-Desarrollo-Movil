"""
Datos de demostración de Tutor Educa.

Crea un curso completo (7° Básico B) con su docente, ocho estudiantes, tres
apoderados, notas, temas desbloqueados, intentos y avisos. Las fechas se
calculan a partir de "hoy", así la demostración siempre se ve actual.

Estos mismos datos se usan en tres lugares:
- el servidor de demostración (SQLite) cuando no hay MySQL,
- el archivo ``database/tutor_educa_mysql.sql`` para phpMyAdmin,
- las pruebas automáticas.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from ..modelos import EscalaNotas
from ..seguridad import GestorClaves
from .matematicas import ASIGNATURA_ID, TEMAS_MATEMATICAS

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


class DatosIniciales:
    """Genera las filas iniciales de cada tabla, en el orden correcto para insertarlas."""

    CLAVE_DEMO = "tutor2026"          # contraseña de todas las cuentas de prueba
    DOMINIO = "tutoreduca.cl"

    # (id, nombre, icono Lucide, color, tiene tutor IA, orden)
    ASIGNATURAS = [
        ("mat", "Matemáticas", "calculator", "#2748C9", 1, 1),
        ("len", "Lenguaje", "book-open", "#B4235A", 0, 2),
        ("cie", "Ciencias Naturales", "flask-conical", "#1F8A5B", 0, 3),
        ("his", "Historia", "landmark", "#A16207", 0, 4),
        ("ing", "Inglés", "languages", "#6D3FC0", 0, 5),
    ]
    DOCENTE = (1, "carolina.fuentes", "Carolina Fuentes")
    # (id, usuario del correo, nombre, asistencia %, notas por asignatura)
    ESTUDIANTES = [
        (2, "sofia.morales", "Sofía Morales", 96, {"mat": [5.0, 4.8, 5.6], "len": [6.2, 6.5, 6.0], "cie": [5.9, 6.3, 6.1], "his": [6.8, 6.6, 7.0], "ing": [6.0, 5.5, 6.2]}),
        (3, "tomas.rojas", "Tomás Rojas", 92, {"mat": [6.1, 5.8, 6.4], "len": [5.5, 5.9, 6.0], "cie": [5.2, 5.0, 5.6], "his": [6.0, 6.3, 5.8], "ing": [5.8, 6.1, 5.5]}),
        (4, "camila.perez", "Camila Pérez", 88, {"mat": [3.8, 4.2, 4.4], "len": [5.6, 6.0, 5.8], "cie": [4.9, 5.3, 5.1], "his": [5.5, 5.9, 6.1], "ing": [4.8, 5.2, 5.0]}),
        (5, "diego.soto", "Diego Soto", 94, {"mat": [4.5, 5.0, 4.6], "len": [6.3, 6.0, 6.6], "cie": [6.0, 5.8, 6.4], "his": [6.9, 6.7, 6.8], "ing": [5.9, 6.2, 6.0]}),
        (6, "martina.diaz", "Martina Díaz", 99, {"mat": [6.8, 6.5, 7.0], "len": [6.6, 6.9, 6.4], "cie": [6.5, 6.7, 6.3], "his": [6.2, 6.6, 6.4], "ing": [6.9, 7.0, 6.7]}),
        (7, "benjamin.munoz", "Benjamín Muñoz", 90, {"mat": [5.4, 5.8, 5.5], "len": [4.9, 5.3, 5.1], "cie": [5.6, 5.2, 5.8], "his": [5.0, 5.4, 5.7], "ing": [4.6, 5.0, 5.3]}),
        (8, "isidora.vargas", "Isidora Vargas", 97, {"mat": [5.9, 6.2, 6.0], "len": [6.4, 6.1, 6.7], "cie": [5.8, 6.0, 6.2], "his": [6.5, 6.3, 6.1], "ing": [6.2, 6.4, 6.6]}),
        (9, "matias.contreras", "Matías Contreras", 85, {"mat": [4.0, 3.6, 4.5], "len": [5.0, 4.6, 5.2], "cie": [4.8, 5.0, 4.4], "his": [5.3, 5.6, 5.0], "ing": [4.3, 4.9, 4.7]}),
    ]
    # (id, usuario del correo, nombre, id del estudiante a su cargo)
    APODERADOS = [
        (10, "andres.morales", "Andrés Morales", 2),
        (11, "rodrigo.perez", "Rodrigo Pérez", 4),
        (12, "carmen.soto", "Carmen Soto", 5),
    ]
    # (estudiante, tema, estado, mensaje del docente, hace cuántos días se desbloqueó)
    REFUERZOS = [
        (2, "mat-ecuaciones", "en_progreso", "Sofía, repasa ecuaciones antes de la prueba del viernes. ¡Tú puedes!", 5),
        (2, "mat-fracciones", "logrado", "", 20),
        (4, "mat-enteros", "disponible", "Camila, empieza por los ejemplos resueltos. Vas bien.", 2),
        (4, "mat-fracciones", "en_progreso", "", 12),
        (5, "mat-porcentajes", "disponible", "", 3),
        (9, "mat-ecuaciones", "disponible", "Matías, mira los ejemplos antes de la prueba del viernes.", 1),
        (9, "mat-enteros", "en_progreso", "", 9),
    ]
    # (estudiante, tema, correctas, total, hace cuántos días)
    INTENTOS = [
        (2, "mat-fracciones", 4, 5, 15),
        (2, "mat-ecuaciones", 2, 5, 2),
        (4, "mat-fracciones", 2, 5, 8),
        (9, "mat-enteros", 2, 5, 6),
    ]

    def __init__(self, hoy: date | None = None):
        self.hoy = hoy or date.today()

    # ------------------------------------------------------------------
    def correo(self, usuario: str) -> str:
        return f"{usuario}@{self.DOMINIO}"

    def _fecha_hora(self, dias_atras: float, hora: int = 10) -> str:
        momento = datetime.combine(self.hoy, time(hora)) - timedelta(days=dias_atras)
        return momento.strftime("%Y-%m-%d %H:%M:%S")

    def _proximo_viernes(self) -> str:
        dias = (4 - self.hoy.weekday()) % 7 or 7
        viernes = self.hoy + timedelta(days=dias)
        return f"viernes {viernes.day} de {MESES[viernes.month - 1]}"

    def cuentas_demo(self) -> list[dict]:
        """Cuentas que se ofrecen en la pantalla de ingreso para probar la app."""
        return [
            {"correo": self.correo("sofia.morales"), "nombre": "Sofía Morales", "rol": "estudiante",
             "detalle": "Estudiante con ecuaciones en curso"},
            {"correo": self.correo("camila.perez"), "nombre": "Camila Pérez", "rol": "estudiante",
             "detalle": "Estudiante que necesita refuerzo"},
            {"correo": self.correo("carolina.fuentes"), "nombre": "Carolina Fuentes", "rol": "docente",
             "detalle": "Docente del 7° Básico B"},
            {"correo": self.correo("andres.morales"), "nombre": "Andrés Morales", "rol": "apoderado",
             "detalle": "Apoderado de Sofía"},
            {"correo": self.correo("rodrigo.perez"), "nombre": "Rodrigo Pérez", "rol": "apoderado",
             "detalle": "Apoderado de Camila"},
        ]

    # ------------------------------------------------------------------
    def contenido(self) -> dict[str, list[dict]]:
        """Solo la materia: se copia al teléfono para poder estudiar sin internet."""
        asignaturas = [{"id": a, "nombre": n, "icono": i, "color": c, "tiene_tutor": t, "orden": o}
                       for a, n, i, c, t, o in self.ASIGNATURAS]
        temas, ejemplos, preguntas = [], [], []
        id_ejemplo = id_pregunta = 0
        for orden, tema in enumerate(TEMAS_MATEMATICAS, start=1):
            temas.append({
                "id": tema["id"], "asignatura_id": ASIGNATURA_ID, "titulo": tema["titulo"],
                "nivel": tema["nivel"], "orden": orden, "icono": tema["icono"],
                "resumen": tema["resumen"], "contenido": "\n\n".join(tema["contenido"]),
                "clave": tema["clave"], "error_comun": tema["error_comun"],
                "consejo_apoderado": tema["consejo_apoderado"],
            })
            for n, ejemplo in enumerate(tema["ejemplos"], start=1):
                id_ejemplo += 1
                ejemplos.append({
                    "id": id_ejemplo, "tema_id": tema["id"], "orden": n, "titulo": ejemplo["titulo"],
                    "enunciado": ejemplo["enunciado"], "pasos": "\n".join(ejemplo["pasos"]),
                    "resultado": ejemplo["resultado"], "comprobacion": ejemplo["comprobacion"],
                })
            for n, pregunta in enumerate(tema["preguntas"], start=1):
                id_pregunta += 1
                preguntas.append({
                    "id": id_pregunta, "tema_id": tema["id"], "orden": n,
                    "enunciado": pregunta["enunciado"], "tipo": pregunta["tipo"],
                    "alternativas": "|".join(pregunta["alternativas"]),
                    "respuesta": pregunta["respuesta"], "pista": pregunta["pista"],
                    "explicacion": pregunta["explicacion"],
                })
        return {"asignaturas": asignaturas, "temas": temas, "ejemplos": ejemplos, "preguntas": preguntas}

    def todo(self) -> dict[str, list[dict]]:
        """Todas las tablas del servidor, en orden (primero las que otras referencian)."""
        creado = self._fecha_hora(60)
        usuarios = [self._usuario(*self.DOCENTE, "docente", creado)]
        usuarios += [self._usuario(i, u, n, "estudiante", creado) for i, u, n, _, _ in self.ESTUDIANTES]
        usuarios += [self._usuario(i, u, n, "apoderado", creado) for i, u, n, _ in self.APODERADOS]

        cursos = [{"id": 1, "nombre": "7° Básico B", "nivel": "7° básico",
                   "docente_id": self.DOCENTE[0], "anio": self.hoy.year}]
        apoderado_de = {estudiante: apoderado for apoderado, _, _, estudiante in self.APODERADOS}
        estudiantes = [{"usuario_id": i, "curso_id": 1, "apoderado_id": apoderado_de.get(i),
                        "asistencia": asistencia} for i, _, _, asistencia, _ in self.ESTUDIANTES]

        calificaciones, id_nota = [], 0
        for estudiante_id, _, _, _, notas in self.ESTUDIANTES:
            for asignatura_id, lista in notas.items():
                for n, nota in enumerate(lista, start=1):
                    id_nota += 1
                    calificaciones.append({
                        "id": id_nota, "estudiante_id": estudiante_id, "asignatura_id": asignatura_id,
                        "nota": nota, "descripcion": f"Evaluación {n}",
                        "fecha": self._fecha_hora(70 - 25 * n)[:10],
                    })

        refuerzos = []
        for n, (estudiante_id, tema_id, estado, mensaje, dias) in enumerate(self.REFUERZOS, start=1):
            refuerzos.append({
                "id": n, "estudiante_id": estudiante_id, "tema_id": tema_id, "estado": estado,
                "mensaje": mensaje, "desbloqueado_por": self.DOCENTE[0],
                "desbloqueado_en": self._fecha_hora(dias, 9), "actualizado_en": self._fecha_hora(max(dias - 1, 0), 18),
                "activo": 1,
            })

        intentos = []
        for n, (estudiante_id, tema_id, correctas, total, dias) in enumerate(self.INTENTOS, start=1):
            intentos.append({
                "id": n, "codigo": f"demo-intento-{n}", "estudiante_id": estudiante_id, "tema_id": tema_id,
                "correctas": correctas, "total": total, "porcentaje": round(100 * correctas / total),
                "nota": EscalaNotas.nota(correctas, total), "realizado_en": self._fecha_hora(dias, 19),
                "origen": "app",
            })

        docente = self.DOCENTE[0]
        avisos = [
            {"id": 1, "codigo": "demo-aviso-1", "curso_id": 1, "estudiante_id": None, "autor_id": docente,
             "titulo": f"Prueba de ecuaciones el {self._proximo_viernes()}",
             "cuerpo": (f"Estimadas familias: el {self._proximo_viernes()} el 7° Básico B rendirá la prueba de "
                        "ecuaciones de primer grado. En Tutor Educa dejé material de repaso desbloqueado para "
                        "quienes lo necesitan. Les pido acompañar 15 minutos de estudio diario esta semana."),
             "tipo": "evaluacion", "creado_en": self._fecha_hora(3, 16)},
            {"id": 2, "codigo": "demo-aviso-2", "curso_id": 1, "estudiante_id": 4, "autor_id": docente,
             "titulo": "Refuerzo de números enteros",
             "cuerpo": ("Camila tiene disponible el tema Números enteros. Les sugiero practicar 15 minutos al "
                        "día con ejemplos de temperaturas o pisos de un edificio. Cualquier duda, me escriben "
                        "por la agenda."),
             "tipo": "refuerzo", "creado_en": self._fecha_hora(2, 12)},
            {"id": 3, "codigo": "demo-aviso-3", "curso_id": 1, "estudiante_id": 2, "autor_id": docente,
             "titulo": "Sofía logró el tema de fracciones",
             "cuerpo": ("Sofía obtuvo 80 % en la prueba de suma y resta de fracciones. Ahora le desbloqueé "
                        "ecuaciones para reforzar antes de la evaluación. ¡Gracias por el apoyo en casa!"),
             "tipo": "logro", "creado_en": self._fecha_hora(1, 11)},
        ]
        avisos_leidos = [{"aviso_id": 1, "usuario_id": 10, "leido_en": self._fecha_hora(2, 21)}]

        datos = {"usuarios": usuarios, "cursos": cursos, "estudiantes": estudiantes}
        contenido = self.contenido()
        datos["asignaturas"] = contenido["asignaturas"]
        datos["calificaciones"] = calificaciones
        datos["temas"] = contenido["temas"]
        datos["ejemplos"] = contenido["ejemplos"]
        datos["preguntas"] = contenido["preguntas"]
        datos["refuerzos"] = refuerzos
        datos["intentos"] = intentos
        datos["avisos"] = avisos
        datos["avisos_leidos"] = avisos_leidos
        return datos

    def _usuario(self, id_: int, usuario: str, nombre: str, rol: str, creado: str) -> dict:
        return {"id": id_, "correo": self.correo(usuario), "nombre": nombre, "rol": rol,
                "clave_hash": GestorClaves.generar_hash(self.CLAVE_DEMO), "activo": 1, "creado_en": creado}

"""
Estructura de la base de datos, escrita UNA sola vez para dos motores.

- SQLite: la base interna del teléfono y el servidor de demostración.
- MySQL/MariaDB: la base del colegio que se administra con phpMyAdmin.

Cada ``Tabla`` sabe generar su ``CREATE TABLE`` para ambos motores, así las
dos bases siempre tienen las mismas columnas y la sincronización es simple.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Columna:
    """Una columna con su tipo "genérico", que se traduce a cada motor."""

    nombre: str
    tipo: str                 # pk | entero | cadena | texto | decimal | fecha | fecha_hora
    largo: int = 0
    nulo: bool = True
    defecto: object = None
    unico: bool = False
    clave_primaria: bool = False
    referencia: str = ""      # por ejemplo "usuarios(id)"
    en_cascada: bool = False  # borrar las filas hijas si se borra la referenciada
    opciones: tuple = ()      # valores permitidos (ENUM en MySQL, CHECK en SQLite)

    def definicion(self, motor: str) -> str:
        sqlite = motor == "sqlite"
        if self.tipo == "pk":
            return (f"{self.nombre} INTEGER PRIMARY KEY AUTOINCREMENT" if sqlite
                    else f"{self.nombre} INT NOT NULL AUTO_INCREMENT PRIMARY KEY")
        if self.opciones and not sqlite:
            tipo = "ENUM(" + ", ".join(f"'{o}'" for o in self.opciones) + ")"
        else:
            tipo = {
                "entero": "INTEGER" if sqlite else "INT",
                "cadena": f"VARCHAR({self.largo or 120})",
                "texto": "TEXT",
                "decimal": "REAL" if sqlite else "DECIMAL(3,1)",
                "fecha": "TEXT" if sqlite else "DATE",
                "fecha_hora": "TEXT" if sqlite else "DATETIME",
            }[self.tipo]
        partes = [self.nombre, tipo]
        if not self.nulo:
            partes.append("NOT NULL")
        if self.defecto is not None:
            valor = f"'{self.defecto}'" if isinstance(self.defecto, str) else str(self.defecto)
            partes.append(f"DEFAULT {valor}")
        if self.clave_primaria:
            partes.append("PRIMARY KEY")
        if self.unico:
            partes.append("UNIQUE")
        if self.opciones and sqlite:
            partes.append(f"CHECK ({self.nombre} IN (" + ", ".join(f"'{o}'" for o in self.opciones) + "))")
        return " ".join(partes)


@dataclass(frozen=True)
class Tabla:
    nombre: str
    columnas: tuple
    unicos: tuple = ()
    clave_compuesta: tuple = ()
    indices: tuple = ()
    comentario: str = ""
    solo_local: bool = False   # tablas que existen solo en el teléfono

    @property
    def nombres_columnas(self) -> list[str]:
        return [c.nombre for c in self.columnas]

    def sentencias(self, motor: str, claves_foraneas: bool = True) -> list[str]:
        lineas = [c.definicion(motor) for c in self.columnas]
        if self.clave_compuesta:
            lineas.append(f"PRIMARY KEY ({', '.join(self.clave_compuesta)})")
        for unico in self.unicos:
            lineas.append(f"UNIQUE ({', '.join(unico)})")
        if claves_foraneas:
            for c in self.columnas:
                if c.referencia:
                    borrar = " ON DELETE CASCADE" if c.en_cascada else ""
                    lineas.append(f"FOREIGN KEY ({c.nombre}) REFERENCES {c.referencia}{borrar}")
        cuerpo = ",\n  ".join(lineas)
        if motor == "mysql":
            comentario = self.comentario.replace("'", "")
            return [f"CREATE TABLE IF NOT EXISTS {self.nombre} (\n  {cuerpo}\n) ENGINE=InnoDB "
                    f"DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='{comentario}'"]
        sentencias = [f"CREATE TABLE IF NOT EXISTS {self.nombre} (\n  {cuerpo}\n)"]
        for columna in self.indices:
            sentencias.append(f"CREATE INDEX IF NOT EXISTS idx_{self.nombre}_{columna} "
                              f"ON {self.nombre} ({columna})")
        return sentencias


C = Columna  # abreviatura para que las definiciones se lean como una tabla

TABLAS: tuple[Tabla, ...] = (
    Tabla("usuarios", (
        C("id", "pk"),
        C("correo", "cadena", 120, nulo=False, unico=True),
        C("nombre", "cadena", 120, nulo=False),
        C("rol", "cadena", 20, nulo=False, opciones=("estudiante", "docente", "apoderado")),
        C("clave_hash", "cadena", 200, nulo=False),
        C("activo", "entero", nulo=False, defecto=1),
        C("creado_en", "fecha_hora"),
    ), comentario="Cuentas de ingreso. El rol define la pantalla de inicio"),
    Tabla("cursos", (
        C("id", "pk"),
        C("nombre", "cadena", 60, nulo=False),
        C("nivel", "cadena", 40, nulo=False),
        C("docente_id", "entero", nulo=False, referencia="usuarios(id)"),
        C("anio", "entero", nulo=False, defecto=2026),
    ), comentario="Cursos y su docente a cargo"),
    Tabla("estudiantes", (
        C("usuario_id", "entero", nulo=False, clave_primaria=True, referencia="usuarios(id)", en_cascada=True),
        C("curso_id", "entero", nulo=False, referencia="cursos(id)"),
        C("apoderado_id", "entero", referencia="usuarios(id)"),
        C("asistencia", "entero", nulo=False, defecto=100),
    ), indices=("curso_id", "apoderado_id"), comentario="Datos escolares de cada estudiante"),
    Tabla("asignaturas", (
        C("id", "cadena", 10, nulo=False, clave_primaria=True),
        C("nombre", "cadena", 60, nulo=False),
        C("icono", "cadena", 40, nulo=False),
        C("color", "cadena", 9, nulo=False),
        C("tiene_tutor", "entero", nulo=False, defecto=0),
        C("orden", "entero", nulo=False, defecto=0),
    ), comentario="Asignaturas del curso"),
    Tabla("calificaciones", (
        C("id", "pk"),
        C("estudiante_id", "entero", nulo=False, referencia="estudiantes(usuario_id)", en_cascada=True),
        C("asignatura_id", "cadena", 10, nulo=False, referencia="asignaturas(id)"),
        C("nota", "decimal", nulo=False),
        C("descripcion", "cadena", 120),
        C("fecha", "fecha"),
    ), indices=("estudiante_id",), comentario="Notas de 1,0 a 7,0"),
    Tabla("temas", (
        C("id", "cadena", 40, nulo=False, clave_primaria=True),
        C("asignatura_id", "cadena", 10, nulo=False, referencia="asignaturas(id)"),
        C("titulo", "cadena", 120, nulo=False),
        C("nivel", "cadena", 40, nulo=False),
        C("orden", "entero", nulo=False, defecto=0),
        C("icono", "cadena", 40, nulo=False, defecto="book-open"),
        C("resumen", "texto", nulo=False),
        C("contenido", "texto", nulo=False),
        C("clave", "texto", nulo=False),
        C("error_comun", "texto", nulo=False),
        C("consejo_apoderado", "texto", nulo=False),
    ), comentario="Materia preescrita que se lee sin internet"),
    Tabla("ejemplos", (
        C("id", "pk"),
        C("tema_id", "cadena", 40, nulo=False, referencia="temas(id)", en_cascada=True),
        C("orden", "entero", nulo=False),
        C("titulo", "cadena", 120, nulo=False),
        C("enunciado", "texto", nulo=False),
        C("pasos", "texto", nulo=False),
        C("resultado", "cadena", 120, nulo=False),
        C("comprobacion", "texto"),
    ), indices=("tema_id",), comentario="Ejemplos resueltos paso a paso"),
    Tabla("preguntas", (
        C("id", "pk"),
        C("tema_id", "cadena", 40, nulo=False, referencia="temas(id)", en_cascada=True),
        C("orden", "entero", nulo=False),
        C("enunciado", "texto", nulo=False),
        C("tipo", "cadena", 12, nulo=False, opciones=("numerica", "alternativas")),
        C("alternativas", "texto"),
        C("respuesta", "cadena", 120, nulo=False),
        C("pista", "texto"),
        C("explicacion", "texto"),
    ), indices=("tema_id",), comentario="Preguntas de la prueba de cada tema"),
    Tabla("refuerzos", (
        C("id", "pk"),
        C("estudiante_id", "entero", nulo=False, referencia="estudiantes(usuario_id)", en_cascada=True),
        C("tema_id", "cadena", 40, nulo=False, referencia="temas(id)"),
        C("estado", "cadena", 12, nulo=False, defecto="disponible",
          opciones=("disponible", "en_progreso", "logrado")),
        C("mensaje", "texto"),
        C("desbloqueado_por", "entero", referencia="usuarios(id)"),
        C("desbloqueado_en", "fecha_hora"),
        C("actualizado_en", "fecha_hora"),
        C("activo", "entero", nulo=False, defecto=1),
    ), unicos=(("estudiante_id", "tema_id"),), indices=("estudiante_id",),
        comentario="Temas que el docente desbloqueó a cada estudiante"),
    Tabla("intentos", (
        C("id", "pk"),
        C("codigo", "cadena", 40, nulo=False, unico=True),
        C("estudiante_id", "entero", nulo=False, referencia="estudiantes(usuario_id)", en_cascada=True),
        C("tema_id", "cadena", 40, nulo=False, referencia="temas(id)"),
        C("correctas", "entero", nulo=False),
        C("total", "entero", nulo=False),
        C("porcentaje", "entero", nulo=False),
        C("nota", "decimal", nulo=False),
        C("realizado_en", "fecha_hora", nulo=False),
        C("origen", "cadena", 10, nulo=False, defecto="app"),
    ), indices=("estudiante_id",), comentario="Resultados de las pruebas (codigo evita duplicados al sincronizar)"),
    Tabla("avisos", (
        C("id", "pk"),
        C("codigo", "cadena", 40, nulo=False, unico=True),
        C("curso_id", "entero", nulo=False, referencia="cursos(id)", en_cascada=True),
        C("estudiante_id", "entero", referencia="estudiantes(usuario_id)", en_cascada=True),
        C("autor_id", "entero", nulo=False, referencia="usuarios(id)"),
        C("titulo", "cadena", 120, nulo=False),
        C("cuerpo", "texto", nulo=False),
        C("tipo", "cadena", 12, nulo=False, defecto="info",
          opciones=("info", "evaluacion", "refuerzo", "logro")),
        C("creado_en", "fecha_hora", nulo=False),
    ), indices=("curso_id",), comentario="Avisos del docente. estudiante_id NULL = todo el curso"),
    Tabla("avisos_leidos", (
        C("aviso_id", "entero", nulo=False, referencia="avisos(id)", en_cascada=True),
        C("usuario_id", "entero", nulo=False, referencia="usuarios(id)", en_cascada=True),
        C("leido_en", "fecha_hora", nulo=False),
    ), clave_compuesta=("aviso_id", "usuario_id"), comentario="Qué apoderado leyó cada aviso"),
    # --- Tablas que existen solo en el teléfono -----------------------------
    Tabla("credenciales", (
        C("correo", "cadena", 120, nulo=False, clave_primaria=True),
        C("usuario_id", "entero", nulo=False),
        C("nombre", "cadena", 120, nulo=False),
        C("rol", "cadena", 20, nulo=False),
        C("clave_hash", "cadena", 200, nulo=False),
        C("ultimo_ingreso", "fecha_hora", nulo=False),
    ), solo_local=True, comentario="Usuarios recordados para ingresar sin conexión"),
    Tabla("cola_sincronizacion", (
        C("id", "pk"),
        C("tipo", "cadena", 20, nulo=False),
        C("datos", "texto", nulo=False),
        C("creado_en", "fecha_hora", nulo=False),
        C("intentos", "entero", nulo=False, defecto=0),
        C("ultimo_error", "texto"),
    ), solo_local=True, comentario="Cambios hechos sin conexión que faltan por enviar"),
    Tabla("preferencias", (
        C("clave", "cadena", 60, nulo=False, clave_primaria=True),
        C("valor", "texto"),
    ), solo_local=True, comentario="Preferencias del dispositivo"),
)

TABLAS_POR_NOMBRE = {t.nombre: t for t in TABLAS}


def sentencias_creacion(motor: str, incluir_locales: bool = False, claves_foraneas: bool = True) -> list[str]:
    """Todas las sentencias CREATE para el motor indicado ("sqlite" o "mysql")."""
    sentencias = []
    for tabla in TABLAS:
        if tabla.solo_local and not incluir_locales:
            continue
        sentencias.extend(tabla.sentencias(motor, claves_foraneas))
    return sentencias


def crear_esquema(conexion, incluir_locales: bool = False, claves_foraneas: bool = True) -> None:
    """Crea las tablas que falten en la conexión dada."""
    for sentencia in sentencias_creacion(conexion.motor, incluir_locales, claves_foraneas):
        conexion.ejecutar(sentencia)

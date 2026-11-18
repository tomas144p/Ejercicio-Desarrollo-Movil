"""
Genera database/tutor_educa_mysql.sql: la base de datos completa (tablas y
datos de demostración) lista para importar en phpMyAdmin.

    python herramientas/generar_sql_mysql.py                 (demostración: con cuentas de prueba)
    python herramientas/generar_sql_mysql.py --produccion    (solo tablas y materia: SIN cuentas ni notas)
    python herramientas/generar_sql_mysql.py --migracion     (pasa una base de la versión 0.3 a la 0.4: colegios)
    python herramientas/generar_sql_mysql.py --migracion-roles  (suma administradores y códigos de invitación)
    python herramientas/generar_sql_mysql.py --migracion-errores (suma el registro de errores de la app)

En phpMyAdmin: pestaña "Importar", elegir el archivo y presionar "Importar".
Se crea la base "tutor_educa". Importarlo de nuevo la deja como nueva.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from models.contenido.datos_iniciales import DatosIniciales  # noqa: E402
from models.datos.esquema import TABLAS, TABLAS_POR_NOMBRE, sentencias_creacion  # noqa: E402


def literal(valor) -> str:
    """Convierte un valor de Python en un literal SQL seguro."""
    if valor is None:
        return "NULL"
    if isinstance(valor, bool):
        return "1" if valor else "0"
    if isinstance(valor, (int, float)):
        return repr(valor)
    texto = str(valor).replace("\\", "\\\\").replace("'", "''").replace("\n", "\\n")
    return f"'{texto}'"


def generar(base_datos: str = "tutor_educa", produccion: bool = False) -> str:
    """
    ``produccion=False``: base de demostración (cuentas de prueba con contraseña conocida).
    ``produccion=True``: solo tablas y materia. No trae cuentas, notas ni nada de personas, y NO borra tablas
    (importarlo por error sobre una base con datos reales no destruye nada).
    """
    datos = DatosIniciales().contenido() if produccion else DatosIniciales().todo()
    lineas = [
        "-- ===============================================================",
        "-- Tutor Educa: base de datos para MySQL / MariaDB" + (" (PRODUCCIÓN)" if produccion else " (phpMyAdmin)"),
        f"-- Generado el {date.today():%d-%m-%Y} con herramientas/generar_sql_mysql.py",
        "--",
    ]
    if produccion:
        lineas += ["-- Solo crea las tablas que falten y carga la materia. Las cuentas se crean con:",
                   "--     python -m backend.crear_usuario ...",
                   "-- No incluye cuentas de prueba."]
    else:
        lineas += ["-- Cómo importarlo: phpMyAdmin > Importar > elegir este archivo > Importar.",
                   "-- Crea la base 'tutor_educa'. Si se importa otra vez, borra y recrea las tablas.",
                   f"-- Todas las cuentas de prueba usan la contraseña: {DatosIniciales.CLAVE_DEMO}",
                   "-- Las contraseñas se guardan cifradas (PBKDF2-SHA256), nunca en texto plano."]
    lineas += [
        "-- ===============================================================",
        "",
        "SET NAMES utf8mb4;",
        "SET FOREIGN_KEY_CHECKS = 0;",
        f"CREATE DATABASE IF NOT EXISTS {base_datos} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
        f"USE {base_datos};",
        "",
    ]
    if not produccion:
        for tabla in reversed([t for t in TABLAS if not t.solo_local]):
            lineas.append(f"DROP TABLE IF EXISTS {tabla.nombre};")
        lineas.append("")
    for sentencia in sentencias_creacion("mysql"):
        if produccion:
            sentencia = sentencia.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ", 1) \
                if "IF NOT EXISTS" not in sentencia.split("(")[0] else sentencia
        lineas.append(sentencia + ";")
        lineas.append("")
    for tabla, filas in datos.items():
        if not filas:
            continue
        columnas = list(filas[0])
        lineas.append(f"-- {tabla}: {len(filas)} fila(s)")
        valores = [f"({', '.join(literal(f[c]) for c in columnas)})" for f in filas]
        lineas.append(f"INSERT {'IGNORE ' if produccion else ''}INTO {tabla} ({', '.join(columnas)}) VALUES\n  " + ",\n  ".join(valores) + ";")
        lineas.append("")
    lineas.append("SET FOREIGN_KEY_CHECKS = 1;")
    return "\n".join(lineas) + "\n"


def generar_migracion(base_datos: str = "tutor_educa") -> str:
    """SQL único para actualizar una base MySQL creada antes de que existieran los colegios."""
    colegios = TABLAS_POR_NOMBRE["colegios"].sentencias("mysql")[0]
    return "\n".join([
        "-- ===============================================================",
        "-- Tutor Educa: migración de la versión 0.3 a la 0.4 (colegios)",
        f"-- Generado el {date.today():%d-%m-%Y} con herramientas/generar_sql_mysql.py --migracion",
        "--",
        "-- Qué hace: crea la tabla colegios, agrega colegio_id a usuarios y cursos, crea UN colegio con el nombre",
        "-- que escribas abajo y le asigna todas las cuentas y cursos que ya existen.",
        "-- Si tu base ya mezclaba varios colegios, asigna cada cuenta y curso con UPDATE antes del último paso.",
        "--",
        "-- IMPORTANTE: haz un respaldo de la base antes. Ejecútalo UNA sola vez.",
        "-- ===============================================================",
        "",
        "SET NAMES utf8mb4;",
        f"USE {base_datos};",
        "",
        colegios + ";",
        "",
        "ALTER TABLE usuarios ADD COLUMN colegio_id INT NULL, ADD KEY idx_usuarios_colegio_id (colegio_id),",
        "  ADD CONSTRAINT fk_usuarios_colegio FOREIGN KEY (colegio_id) REFERENCES colegios (id);",
        "ALTER TABLE cursos ADD COLUMN colegio_id INT NULL, ADD KEY idx_cursos_colegio_id (colegio_id),",
        "  ADD CONSTRAINT fk_cursos_colegio FOREIGN KEY (colegio_id) REFERENCES colegios (id);",
        "",
        "-- >>> CAMBIA ESTE NOMBRE por el de tu colegio <<<",
        "INSERT INTO colegios (nombre, activo, creado_en) VALUES ('NOMBRE DE TU COLEGIO', 1, NOW());",
        "SET @colegio = LAST_INSERT_ID();",
        "UPDATE usuarios SET colegio_id = @colegio WHERE colegio_id IS NULL;",
        "UPDATE cursos SET colegio_id = @colegio WHERE colegio_id IS NULL;",
        "",
        "-- Desde ahora todo curso debe pertenecer a un colegio.",
        "ALTER TABLE cursos MODIFY colegio_id INT NOT NULL;",
        "",
    ])


def generar_migracion_roles(base_datos: str = "tutor_educa") -> str:
    """SQL único para una base que ya tiene colegios: agrega los perfiles administrativos y las invitaciones."""
    perfiles = ", ".join(f"'{o}'" for o in next(c for c in TABLAS_POR_NOMBRE["usuarios"].columnas
                                                  if c.nombre == "rol").opciones)
    invitaciones = TABLAS_POR_NOMBRE["invitaciones"].sentencias("mysql")[0]
    return "\n".join([
        "-- ===============================================================",
        "-- Tutor Educa: migración de colegios a administradores e invitaciones",
        f"-- Generado el {date.today():%d-%m-%Y} con herramientas/generar_sql_mysql.py --migracion-roles",
        "--",
        "-- Qué hace: permite los perfiles «admin» y «superadmin» en la tabla usuarios y crea la tabla invitaciones",
        "-- (códigos de un solo uso para activar cuentas). No cambia ni borra ningún dato existente.",
        "-- Si tu base es de la versión 0.3, ejecuta ANTES database/migracion_colegios.sql.",
        "-- IMPORTANTE: haz un respaldo antes. Ejecútalo UNA sola vez.",
        "-- ===============================================================",
        "",
        "SET NAMES utf8mb4;",
        f"USE {base_datos};",
        "",
        f"ALTER TABLE usuarios MODIFY rol ENUM({perfiles}) NOT NULL;",
        "",
        invitaciones + ";",
        "",
    ])


def generar_migracion_errores(base_datos: str = "tutor_educa") -> str:
    """SQL único para una base que ya tiene administradores: agrega la tabla del registro de errores de la app."""
    tabla = TABLAS_POR_NOMBRE["errores_app"].sentencias("mysql")[0]
    indices = [f"CREATE INDEX idx_errores_app_{c} ON errores_app ({c});" for c in TABLAS_POR_NOMBRE["errores_app"].indices]
    return "\n".join([
        "-- ===============================================================",
        "-- Tutor Educa: migración para el registro de errores de la app",
        f"-- Generado el {date.today():%d-%m-%Y} con herramientas/generar_sql_mysql.py --migracion-errores",
        "--",
        "-- Qué hace: crea la tabla errores_app (errores y cierres inesperados, sin datos personales).",
        "-- No cambia ni borra ningún dato existente. Si tu base es anterior, ejecuta ANTES las otras migraciones.",
        "-- IMPORTANTE: haz un respaldo antes. Ejecútalo UNA sola vez.",
        "-- ===============================================================",
        "",
        "SET NAMES utf8mb4;",
        f"USE {base_datos};",
        "",
        tabla + ";",
        "",
        *indices,
        "",
    ])


if __name__ == "__main__":
    if "--migracion-errores" in sys.argv[1:]:
        destino = RAIZ / "database" / "migracion_errores.sql"
        destino.write_text(generar_migracion_errores(), encoding="utf-8")
        print(f"Listo: {destino.relative_to(RAIZ)}")
        sys.exit(0)
    if "--migracion-roles" in sys.argv[1:]:
        destino = RAIZ / "database" / "migracion_roles.sql"
        destino.write_text(generar_migracion_roles(), encoding="utf-8")
        print(f"Listo: {destino.relative_to(RAIZ)}")
        sys.exit(0)
    if "--migracion" in sys.argv[1:]:
        destino = RAIZ / "database" / "migracion_colegios.sql"
        destino.write_text(generar_migracion(), encoding="utf-8")
        print(f"Listo: {destino.relative_to(RAIZ)}")
        sys.exit(0)
    es_produccion = "--produccion" in sys.argv[1:]
    destino = RAIZ / "database" / ("tutor_educa_produccion.sql" if es_produccion else "tutor_educa_mysql.sql")
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(generar(produccion=es_produccion), encoding="utf-8")
    print(f"Listo: {destino.relative_to(RAIZ)}")

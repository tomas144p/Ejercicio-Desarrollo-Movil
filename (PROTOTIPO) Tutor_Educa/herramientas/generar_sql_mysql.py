"""
Genera database/tutor_educa_mysql.sql: la base de datos completa (tablas y
datos de demostración) lista para importar en phpMyAdmin.

    python herramientas/generar_sql_mysql.py                 (demostración: con cuentas de prueba)
    python herramientas/generar_sql_mysql.py --produccion    (solo tablas y materia: SIN cuentas ni notas)

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
from models.datos.esquema import TABLAS, sentencias_creacion  # noqa: E402


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


if __name__ == "__main__":
    es_produccion = "--produccion" in sys.argv[1:]
    destino = RAIZ / "database" / ("tutor_educa_produccion.sql" if es_produccion else "tutor_educa_mysql.sql")
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(generar(produccion=es_produccion), encoding="utf-8")
    print(f"Listo: {destino.relative_to(RAIZ)}")

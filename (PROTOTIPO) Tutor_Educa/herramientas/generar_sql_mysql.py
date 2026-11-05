"""
Genera database/tutor_educa_mysql.sql: la base de datos completa (tablas y
datos de demostración) lista para importar en phpMyAdmin.

    python herramientas/generar_sql_mysql.py

En phpMyAdmin: pestaña "Importar", elegir el archivo y presionar "Importar".
Se crea la base "tutor_educa". Importarlo de nuevo la deja como nueva.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from tutor_educa.contenido.datos_iniciales import DatosIniciales  # noqa: E402
from tutor_educa.datos.esquema import TABLAS, sentencias_creacion  # noqa: E402


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


def generar(base_datos: str = "tutor_educa") -> str:
    datos = DatosIniciales().todo()
    lineas = [
        "-- ===============================================================",
        "-- Tutor Educa: base de datos para MySQL / MariaDB (phpMyAdmin)",
        f"-- Generado el {date.today():%d-%m-%Y} con herramientas/generar_sql_mysql.py",
        "--",
        "-- Cómo importarlo: phpMyAdmin > Importar > elegir este archivo > Importar.",
        "-- Crea la base 'tutor_educa'. Si se importa otra vez, borra y recrea las tablas.",
        f"-- Todas las cuentas de prueba usan la contraseña: {DatosIniciales.CLAVE_DEMO}",
        "-- Las contraseñas se guardan cifradas (PBKDF2-SHA256), nunca en texto plano.",
        "-- ===============================================================",
        "",
        "SET NAMES utf8mb4;",
        "SET FOREIGN_KEY_CHECKS = 0;",
        f"CREATE DATABASE IF NOT EXISTS {base_datos} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
        f"USE {base_datos};",
        "",
    ]
    for tabla in reversed([t for t in TABLAS if not t.solo_local]):
        lineas.append(f"DROP TABLE IF EXISTS {tabla.nombre};")
    lineas.append("")
    for sentencia in sentencias_creacion("mysql"):
        lineas.append(sentencia + ";")
        lineas.append("")
    for tabla, filas in datos.items():
        if not filas:
            continue
        columnas = list(filas[0])
        lineas.append(f"-- {tabla}: {len(filas)} fila(s)")
        valores = [f"({', '.join(literal(f[c]) for c in columnas)})" for f in filas]
        lineas.append(f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES\n  " + ",\n  ".join(valores) + ";")
        lineas.append("")
    lineas.append("SET FOREIGN_KEY_CHECKS = 1;")
    return "\n".join(lineas) + "\n"


if __name__ == "__main__":
    destino = RAIZ / "database" / "tutor_educa_mysql.sql"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(generar(), encoding="utf-8")
    print(f"Listo: {destino.relative_to(RAIZ)}")

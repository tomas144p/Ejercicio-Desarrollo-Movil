"""
Crea la sentencia SQL para agregar una cuenta nueva (con su contraseña cifrada).

    python herramientas/nuevo_usuario.py correo@colegio.cl "Nombre Apellido" estudiante clave123

Copia el resultado en phpMyAdmin > SQL. Para un estudiante, recuerda también
agregarlo a la tabla "estudiantes" (se imprime un ejemplo).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tutor_educa.modelos import Rol, ahora_iso  # noqa: E402
from tutor_educa.seguridad import GestorClaves  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) != 5 or sys.argv[3] not in Rol.TODOS:
        print(__doc__)
        sys.exit(1)
    correo, nombre, rol, clave = sys.argv[1:]
    huella = GestorClaves.generar_hash(clave)
    nombre_sql = nombre.replace("'", "''")
    print(f"INSERT INTO usuarios (correo, nombre, rol, clave_hash, activo, creado_en) VALUES "
          f"('{correo.lower()}', '{nombre_sql}', '{rol}', '{huella}', 1, '{ahora_iso()}');")
    if rol == Rol.ESTUDIANTE:
        print("-- Luego, para asignarlo a un curso (cambia curso_id y apoderado_id):")
        print(f"INSERT INTO estudiantes (usuario_id, curso_id, apoderado_id, asistencia) "
              f"SELECT id, 1, NULL, 100 FROM usuarios WHERE correo = '{correo.lower()}';")

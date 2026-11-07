"""
Crea cuentas y cursos directamente en la base del servidor (hasta que exista el panel de administración).

    python -m backend.crear_usuario docente  carolina@colegio.cl "Carolina Fuentes" --curso "7° Básico B" --nivel "7° Básico"
    python -m backend.crear_usuario apoderado andres@correo.cl   "Andrés Morales"
    python -m backend.crear_usuario estudiante sofia@correo.cl   "Sofía Morales" --curso-id 1 --apoderado andres@correo.cl

La contraseña se pide por teclado (no queda en el historial de la consola). Mínimo 10 caracteres.
En Docker:  docker compose exec api python -m backend.crear_usuario ...
"""

from __future__ import annotations

import argparse
import getpass
import sys

from models.modelos import Rol, ahora_iso
from services.seguridad import GestorClaves
from services.validaciones import validar_correo

LARGO_MINIMO_CLAVE = 10


class ErrorAlta(Exception):
    """No se pudo crear la cuenta. El mensaje dice por qué."""


def validar_clave_nueva(clave: str) -> str:
    if len(clave) < LARGO_MINIMO_CLAVE:
        raise ErrorAlta(f"La contraseña debe tener al menos {LARGO_MINIMO_CLAVE} caracteres.")
    if clave.isdigit() or clave.lower() == clave.upper():
        raise ErrorAlta("La contraseña no puede ser solo números ni solo símbolos: mezcla letras y números.")
    return clave


def crear_usuario(repo, correo: str, nombre: str, rol: str, clave: str, curso_id: int | None = None,
                  apoderado_correo: str | None = None, curso_nuevo: tuple[str, str] | None = None) -> int:
    """Crea la cuenta y devuelve su id. ``curso_nuevo`` = (nombre, nivel), solo para docentes."""
    try:
        correo = validar_correo(correo).lower()
    except ValueError as error:
        raise ErrorAlta(str(error)) from error
    nombre = (nombre or "").strip()
    if not 3 <= len(nombre) <= 120:
        raise ErrorAlta("El nombre debe tener entre 3 y 120 caracteres.")
    if rol not in Rol.TODOS:
        raise ErrorAlta(f"El perfil debe ser uno de: {', '.join(Rol.TODOS)}.")
    validar_clave_nueva(clave)
    if repo.usuario_por_correo(correo):
        raise ErrorAlta("Ya existe una cuenta con ese correo.")
    if curso_nuevo and rol != Rol.DOCENTE:
        raise ErrorAlta("Solo un docente puede crear un curso.")
    apoderado_id = None
    if rol == Rol.ESTUDIANTE:
        if curso_id is None or repo.curso(curso_id) is None:
            raise ErrorAlta("Para un estudiante indica un curso que exista (--curso-id).")
        if apoderado_correo:
            apoderado = repo.usuario_por_correo(apoderado_correo.strip().lower())
            if not apoderado or apoderado["rol"] != Rol.APODERADO:
                raise ErrorAlta("Ese correo no corresponde a un apoderado existente.")
            apoderado_id = int(apoderado["id"])
    with repo.bd.transaccion():
        nuevo_id = repo.bd.insertar("usuarios", {"correo": correo, "nombre": nombre, "rol": rol,
                                                 "clave_hash": GestorClaves.generar_hash(clave), "activo": 1,
                                                 "creado_en": ahora_iso()})
        if rol == Rol.DOCENTE and curso_nuevo:
            repo.bd.insertar("cursos", {"nombre": curso_nuevo[0], "nivel": curso_nuevo[1], "docente_id": nuevo_id,
                                        "anio": int(ahora_iso()[:4])})
        if rol == Rol.ESTUDIANTE:
            repo.bd.insertar("estudiantes", {"usuario_id": nuevo_id, "curso_id": curso_id,
                                             "apoderado_id": apoderado_id, "asistencia": 100})
    return int(nuevo_id)


def main(argumentos=None) -> int:
    parser = argparse.ArgumentParser(description="Crea una cuenta en el servidor de Tutor Educa.")
    parser.add_argument("rol", choices=Rol.TODOS)
    parser.add_argument("correo")
    parser.add_argument("nombre")
    parser.add_argument("--curso", help="docente: nombre del curso a crear, por ejemplo «7° Básico B»")
    parser.add_argument("--nivel", help="docente: nivel del curso, por ejemplo «7° Básico»")
    parser.add_argument("--curso-id", type=int, help="estudiante: id del curso")
    parser.add_argument("--apoderado", help="estudiante: correo de su apoderado (debe existir)")
    datos = parser.parse_args(argumentos)

    from backend.ajustes import Ajustes, AjustesInvalidos
    from models.datos.servidor import GestorServidor
    try:
        ajustes = Ajustes.desde_entorno()
    except AjustesInvalidos as error:
        print(f"Configuración inválida: {error}")
        return 1
    gestor = GestorServidor(ajustes.bd, ajustes.carpeta_datos).inicializar()
    if gestor.servidor is None:
        print(f"No se pudo conectar a la base de datos. {gestor.diagnostico}")
        return 1
    clave = getpass.getpass("Contraseña de la cuenta nueva: ")
    if getpass.getpass("Repítela: ") != clave:
        print("Las contraseñas no coinciden.")
        return 1
    curso_nuevo = (datos.curso, datos.nivel or datos.curso) if datos.curso else None
    try:
        nuevo_id = crear_usuario(gestor.servidor, datos.correo, datos.nombre, datos.rol, clave, datos.curso_id,
                                 datos.apoderado, curso_nuevo)
    except ErrorAlta as error:
        print(f"No se creó la cuenta: {error}")
        return 1
    print(f"Cuenta creada (id {nuevo_id}): {datos.correo.lower()} · {datos.rol}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

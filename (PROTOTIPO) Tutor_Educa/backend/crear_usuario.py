"""
Crea cuentas directamente en la base del servidor, desde la consola de quien opera el servidor.

Lo normal es crear la cuenta SIN contraseña y entregar el código de invitación que se muestra una sola vez; la persona
elige su propia contraseña en la app (nadie más la conoce):

    python -m backend.crear_colegio "Colegio San Andrés"                      (primero: devuelve el id del colegio)
    python -m backend.crear_usuario admin    directora@colegio.cl "Marta Rojas" --colegio-id 1 --invitacion
    python -m backend.crear_usuario docente  carolina@colegio.cl "Carolina Fuentes" --colegio-id 1 --invitacion \\
                                             --curso "7° Básico B" --nivel "7° Básico"
    python -m backend.crear_usuario apoderado andres@correo.cl "Andrés Morales" --colegio-id 1 --invitacion
    python -m backend.crear_usuario estudiante sofia@correo.cl "Sofía Morales" --curso-id 1 --invitacion \\
                                             --apoderado andres@correo.cl
    python -m backend.crear_usuario superadmin plataforma@tutoreduca.cl "Equipo Tutor Educa" --invitacion

Sin ``--invitacion`` se pide una contraseña por teclado (no queda en el historial). Mínimo 10 caracteres.
Solo para pruebas automáticas se acepta la variable de entorno TUTOR_CLAVE_NUEVA (herramientas/probar_docker.py).

Cada cuenta pertenece a UN colegio (salvo superadmin). Un estudiante toma el colegio de su curso y su apoderado debe ser
del mismo. En Docker:  docker compose exec api python -m backend.crear_usuario ...

El panel y la app hacen lo mismo desde la API (con permisos): este programa es para el primer arranque y emergencias.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from backend.cuentas import Cuentas, ErrorAlta, validar_clave_nueva  # noqa: F401  (se reexportan para las pruebas)
from models.modelos import Rol


def crear_usuario(repo, correo: str, nombre: str, rol: str, clave: str, curso_id: int | None = None,
                  apoderado_correo: str | None = None, curso_nuevo: tuple[str, str] | None = None,
                  colegio_id: int | None = None) -> int:
    """Crea la cuenta con contraseña y devuelve su id. ``curso_nuevo`` = (nombre, nivel), solo para docentes."""
    resultado = Cuentas(repo).crear_cuenta(None, correo, nombre, rol, colegio_id=colegio_id, curso_id=curso_id,
                                           curso_nuevo=curso_nuevo, apoderado_correo=apoderado_correo, clave=clave)
    return int(resultado["usuario"]["id"])


def crear_usuario_con_invitacion(repo, correo: str, nombre: str, rol: str, **opciones) -> dict:
    """Crea la cuenta sin contraseña. Devuelve {"usuario", "codigo", "vence_en", ...} (el código se muestra una vez)."""
    return Cuentas(repo).crear_cuenta(None, correo, nombre, rol, **opciones)


def main(argumentos=None) -> int:
    parser = argparse.ArgumentParser(description="Crea una cuenta en el servidor de Tutor Educa.")
    parser.add_argument("rol", choices=Rol.PERFILES)
    parser.add_argument("correo")
    parser.add_argument("nombre")
    parser.add_argument("--invitacion", action="store_true",
                        help="crear sin contraseña y mostrar un código de invitación (recomendado)")
    parser.add_argument("--colegio-id", type=int, help="el colegio (un estudiante usa el de su curso)")
    parser.add_argument("--curso", help="docente: nombre del curso a crear, por ejemplo «7° Básico B»")
    parser.add_argument("--nivel", help="docente: nivel del curso, por ejemplo «7° Básico»")
    parser.add_argument("--curso-id", type=int, help="estudiante: id del curso")
    parser.add_argument("--apoderado", help="estudiante: correo de su apoderado (debe existir)")
    parser.add_argument("--apoderado-nombre", help="estudiante: si el apoderado no existe, se crea con este nombre")
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

    clave = None
    if not datos.invitacion:
        clave = os.environ.get("TUTOR_CLAVE_NUEVA") or getpass.getpass("Contraseña de la cuenta nueva: ")
        if not os.environ.get("TUTOR_CLAVE_NUEVA") and getpass.getpass("Repítela: ") != clave:
            print("Las contraseñas no coinciden.")
            return 1
    curso_nuevo = (datos.curso, datos.nivel or datos.curso) if datos.curso else None
    try:
        resultado = Cuentas(gestor.servidor).crear_cuenta(
            None, datos.correo, datos.nombre, datos.rol, colegio_id=datos.colegio_id, curso_id=datos.curso_id,
            curso_nuevo=curso_nuevo, apoderado_correo=datos.apoderado, apoderado_nombre=datos.apoderado_nombre,
            clave=clave)
    except (ErrorAlta, Exception) as error:        # ErrorPermiso/ErrorDatos también llegan aquí con su mensaje
        print(f"No se creó la cuenta: {error}")
        return 1
    usuario = resultado["usuario"]
    print(f"Cuenta creada (id {usuario['id']}): {usuario['correo']} · {usuario['rol']}")
    for curso in gestor.servidor.cursos_de_docente(usuario["id"]) if usuario["rol"] == Rol.DOCENTE else []:
        print(f"Curso creado (id {curso.id}): {curso.nombre}")
    if resultado.get("codigo"):
        print(f"CÓDIGO DE INVITACIÓN: {resultado['codigo']}   (vence {resultado['vence_en']}; se muestra solo ahora)")
    apoderado = resultado.get("apoderado")
    if apoderado and not apoderado.get("existente"):
        print(f"Apoderado creado: {apoderado['usuario']['correo']}  CÓDIGO: {apoderado['codigo']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

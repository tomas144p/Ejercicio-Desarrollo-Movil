"""
Crea un colegio (o lista los que hay). Cada colegio es un espacio separado: sus cursos, docentes, estudiantes y
apoderados nunca se mezclan con los de otro.

    python -m backend.crear_colegio "Colegio San Andrés"
    python -m backend.crear_colegio --listar
    python -m backend.crear_colegio --suspender 2      (nadie del colegio 2 puede ingresar ni sincronizar)
    python -m backend.crear_colegio --reactivar 2

En Docker:  docker compose exec api python -m backend.crear_colegio "Colegio San Andrés"
"""

from __future__ import annotations

import argparse
import sys

from models.modelos import ahora_iso


class ErrorColegio(Exception):
    """No se pudo crear o cambiar el colegio. El mensaje dice por qué."""


def crear_colegio(repo, nombre: str) -> int:
    nombre = " ".join((nombre or "").split())
    if not 3 <= len(nombre) <= 120:
        raise ErrorColegio("El nombre del colegio debe tener entre 3 y 120 caracteres.")
    if repo.bd.consultar_uno("SELECT id FROM colegios WHERE nombre = ?", (nombre,)):
        raise ErrorColegio("Ya existe un colegio con ese nombre.")
    return int(repo.bd.insertar("colegios", {"nombre": nombre, "activo": 1, "creado_en": ahora_iso()}))


def cambiar_estado(repo, colegio_id: int, activo: bool) -> None:
    if repo.colegio(colegio_id) is None:
        raise ErrorColegio("Ese colegio no existe.")
    repo.bd.ejecutar("UPDATE colegios SET activo = ? WHERE id = ?", (1 if activo else 0, colegio_id))


def main(argumentos=None) -> int:
    parser = argparse.ArgumentParser(description="Crea o administra colegios de Tutor Educa.")
    parser.add_argument("nombre", nargs="?", help="nombre del colegio nuevo")
    parser.add_argument("--listar", action="store_true")
    parser.add_argument("--suspender", type=int, metavar="ID")
    parser.add_argument("--reactivar", type=int, metavar="ID")
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
    repo = gestor.servidor
    try:
        if datos.listar:
            for colegio in repo.colegios():
                estado = "activo" if int(colegio["activo"]) else "SUSPENDIDO"
                print(f"{colegio['id']:>3}  {colegio['nombre']}  ({estado})")
        elif datos.suspender or datos.reactivar:
            colegio_id = datos.suspender or datos.reactivar
            cambiar_estado(repo, colegio_id, activo=bool(datos.reactivar))
            print(f"Colegio {colegio_id} {'reactivado' if datos.reactivar else 'suspendido'}.")
        elif datos.nombre:
            print(f"Colegio creado (id {crear_colegio(repo, datos.nombre)}): {' '.join(datos.nombre.split())}")
        else:
            parser.print_help()
            return 1
    except ErrorColegio as error:
        print(f"No se pudo: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Reglas de quién puede cambiar qué.

El celular manda cambios (un intento de prueba, un aviso, un tema desbloqueado...). El servidor NO se
fía de lo que dice el celular: cada cambio se revisa aquí contra el usuario del token.

Principios:
- Los campos que identifican a la persona (autor, docente, quien lee) se IGNORAN si vienen del celular
  y se reemplazan por el id del token. Nadie puede actuar "en nombre de" otra persona.
- Solo se aceptan campos conocidos, con tipo y largo válidos.
- Cada persona solo toca datos de sus propios estudiantes o cursos Y de su propio colegio: aunque un dato
  estuviera mal enlazado entre colegios, aquí se rechaza (ver ``_mismo_colegio``).

Python puro (sin FastAPI): se prueba directamente con pruebas unitarias.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from models.modelos import FORMATO_FECHA, EscalaNotas, EstadoRefuerzo, Rol, Usuario
from services.validaciones import validar_aviso

TIPOS_AVISO = ("info", "evaluacion", "refuerzo", "logro")


class ErrorPermiso(Exception):
    """La persona no tiene permiso para hacer este cambio (HTTP 403)."""


class ErrorDatos(Exception):
    """El cambio viene mal formado (HTTP 422). El mensaje está en español simple."""


# ---------------------------------------------------------------------------
# Lectores de campos
# ---------------------------------------------------------------------------
def _entero(datos: dict, campo: str, minimo: int | None = None, maximo: int | None = None) -> int:
    valor = datos.get(campo)
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ErrorDatos(f"«{campo}» debe ser un número entero.")
    if (minimo is not None and valor < minimo) or (maximo is not None and valor > maximo):
        raise ErrorDatos(f"«{campo}» está fuera del rango permitido.")
    return valor


def _texto(datos: dict, campo: str, minimo: int = 1, maximo: int = 200) -> str:
    valor = datos.get(campo)
    if not isinstance(valor, str):
        raise ErrorDatos(f"«{campo}» debe ser texto.")
    valor = valor.strip()
    if not (minimo <= len(valor) <= maximo):
        raise ErrorDatos(f"«{campo}» debe tener entre {minimo} y {maximo} caracteres.")
    return valor


def _fecha(datos: dict, campo: str) -> str:
    texto = _texto(datos, campo, 10, 30)
    try:
        momento = datetime.strptime(texto, FORMATO_FECHA)
    except ValueError as error:
        raise ErrorDatos(f"«{campo}» no tiene un formato de fecha válido.") from error
    if momento > datetime.now() + timedelta(days=1):
        raise ErrorDatos(f"«{campo}» está en el futuro.")
    return texto


def _bool(datos: dict, campo: str) -> bool:
    valor = datos.get(campo)
    if isinstance(valor, bool):
        return valor
    if valor in (0, 1) and not isinstance(valor, bool):
        return bool(valor)
    raise ErrorDatos(f"«{campo}» debe ser verdadero o falso.")


def _exigir_rol(usuario: Usuario, *roles: str) -> None:
    if usuario.rol not in roles:
        raise ErrorPermiso("Tu perfil no puede hacer este cambio.")


# ---------------------------------------------------------------------------
# Quién ve a quién (siempre dentro del mismo colegio)
# ---------------------------------------------------------------------------
def _mismo_colegio(usuario: Usuario, colegio_id) -> bool:
    """Verdadero solo si la persona tiene colegio y el dato es de ese mismo colegio."""
    return usuario.colegio_id is not None and colegio_id is not None and int(colegio_id) == int(usuario.colegio_id)


def _fila_del_colegio(usuario: Usuario, fila: dict | None) -> bool:
    """La fila de un estudiante (usuario y curso) pertenece al colegio de la persona."""
    return bool(fila) and _mismo_colegio(usuario, fila.get("colegio_id")) \
        and _mismo_colegio(usuario, fila.get("curso_colegio_id"))


def cursos_del_docente(repo, docente: Usuario) -> set[int]:
    return {int(c.id) for c in repo.cursos_de_docente(docente.id) if _mismo_colegio(docente, c.colegio_id)}


def estudiantes_de(repo, usuario: Usuario) -> tuple[set[int], set[int]]:
    """(ids de estudiantes, ids de cursos) a los que la persona tiene acceso, solo de su colegio."""
    if usuario.rol == Rol.ESTUDIANTE:
        fila = repo.estudiante(usuario.id)
        return ({usuario.id}, {int(fila["curso_id"])}) if _fila_del_colegio(usuario, fila) else (set(), set())
    if usuario.rol == Rol.APODERADO:
        filas = [f for f in repo.hijos_de_apoderado(usuario.id) if _fila_del_colegio(usuario, f)]
        return {int(f["id"]) for f in filas}, {int(f["curso_id"]) for f in filas}
    cursos = cursos_del_docente(repo, usuario)
    estudiantes: set[int] = set()
    for curso_id in cursos:
        estudiantes |= {int(f["id"]) for f in repo.estudiantes_de_curso(curso_id) if _fila_del_colegio(usuario, f)}
    return estudiantes, cursos


def _estudiante_del_docente(repo, docente: Usuario, estudiante_id: int) -> dict:
    fila = repo.estudiante(estudiante_id)
    if not _fila_del_colegio(docente, fila) or int(fila["curso_id"]) not in cursos_del_docente(repo, docente):
        raise ErrorPermiso("Ese estudiante no es de tus cursos.")
    return fila


def _tema_existente(repo, tema_id: str) -> str:
    if repo.tema(tema_id) is None:
        raise ErrorDatos("Ese tema no existe.")
    return tema_id


# ---------------------------------------------------------------------------
# Un validador por tipo de cambio
# ---------------------------------------------------------------------------
def _intento(repo, usuario: Usuario, datos: dict) -> dict:
    _exigir_rol(usuario, Rol.ESTUDIANTE)
    if _entero(datos, "estudiante_id") != usuario.id or usuario.id not in estudiantes_de(repo, usuario)[0]:
        raise ErrorPermiso("Solo puedes registrar tus propias pruebas.")
    total = _entero(datos, "total", 1, 100)
    correctas = _entero(datos, "correctas", 0, total)
    # El porcentaje y la nota se recalculan aquí: el celular no puede inventar una nota distinta.
    return {"codigo": _texto(datos, "codigo", 8, 40), "estudiante_id": usuario.id,
            "tema_id": _tema_existente(repo, _texto(datos, "tema_id", 1, 40)),
            "correctas": correctas, "total": total, "porcentaje": round(100 * correctas / total),
            "nota": EscalaNotas.nota(correctas, total), "realizado_en": _fecha(datos, "realizado_en"),
            "origen": "app"}


def _estado_refuerzo(repo, usuario: Usuario, datos: dict) -> dict:
    _exigir_rol(usuario, Rol.ESTUDIANTE)
    if _entero(datos, "estudiante_id") != usuario.id or usuario.id not in estudiantes_de(repo, usuario)[0]:
        raise ErrorPermiso("Solo puedes cambiar tus propios temas.")
    estado = _texto(datos, "estado", 1, 20)
    if estado not in EstadoRefuerzo.ORDEN:
        raise ErrorDatos("Estado de tema desconocido.")
    return {"estudiante_id": usuario.id, "tema_id": _tema_existente(repo, _texto(datos, "tema_id", 1, 40)),
            "estado": estado, "fecha": _fecha(datos, "fecha")}


def _desbloqueo(repo, usuario: Usuario, datos: dict) -> dict:
    _exigir_rol(usuario, Rol.DOCENTE)
    estudiante_id = _entero(datos, "estudiante_id")
    _estudiante_del_docente(repo, usuario, estudiante_id)
    mensaje = datos.get("mensaje")
    if mensaje is not None:
        mensaje = _texto({"mensaje": mensaje}, "mensaje", 0, 500)
    return {"estudiante_id": estudiante_id, "tema_id": _tema_existente(repo, _texto(datos, "tema_id", 1, 40)),
            "activo": _bool(datos, "activo"), "mensaje": mensaje, "docente_id": usuario.id,
            "fecha": _fecha(datos, "fecha")}


def _aviso(repo, usuario: Usuario, datos: dict) -> dict:
    _exigir_rol(usuario, Rol.DOCENTE)
    curso_id = _entero(datos, "curso_id")
    if curso_id not in cursos_del_docente(repo, usuario):
        raise ErrorPermiso("Ese curso no es tuyo.")
    estudiante_id = datos.get("estudiante_id")
    if estudiante_id is not None:
        estudiante_id = _entero(datos, "estudiante_id")
        fila = _estudiante_del_docente(repo, usuario, estudiante_id)
        if int(fila["curso_id"]) != curso_id:
            raise ErrorDatos("Ese estudiante no es de ese curso.")
    try:
        titulo, cuerpo = validar_aviso(_texto(datos, "titulo", 0, 120), _texto(datos, "cuerpo", 0, 2000))
    except ValueError as error:
        raise ErrorDatos(str(error)) from error
    tipo = _texto(datos, "tipo", 1, 12)
    if tipo not in TIPOS_AVISO:
        raise ErrorDatos("Tipo de aviso desconocido.")
    return {"codigo": _texto(datos, "codigo", 8, 40), "curso_id": curso_id, "estudiante_id": estudiante_id,
            "autor_id": usuario.id, "titulo": titulo, "cuerpo": cuerpo, "tipo": tipo,
            "creado_en": _fecha(datos, "creado_en")}


def _aviso_leido(repo, usuario: Usuario, datos: dict) -> dict:
    _exigir_rol(usuario, Rol.APODERADO, Rol.ESTUDIANTE)
    aviso = repo.aviso_por_codigo(_texto(datos, "aviso_codigo", 8, 40))
    if aviso is None:
        raise ErrorDatos("Ese aviso no existe.")
    estudiantes, cursos = estudiantes_de(repo, usuario)
    curso = repo.curso(int(aviso["curso_id"]))
    destinado = aviso["estudiante_id"] is None or int(aviso["estudiante_id"]) in estudiantes
    if curso is None or not _mismo_colegio(usuario, curso.colegio_id) or int(aviso["curso_id"]) not in cursos \
            or not destinado:
        raise ErrorPermiso("Ese aviso no es para ti.")
    return {"aviso_codigo": aviso["codigo"], "usuario_id": usuario.id, "fecha": _fecha(datos, "fecha")}


def _error_app(repo, usuario: Usuario, datos: dict) -> dict:
    """Cualquier persona con sesión puede informar un error de SU app. Todo se limpia otra vez aquí: el servidor no
    confía en que el celular haya quitado los datos personales. El colegio y el perfil salen de la sesión, no del celular."""
    from services.registro_errores import limpiar
    huella = _texto(datos, "huella", 6, 16)
    if not all(c in "0123456789abcdef" for c in huella):
        raise ErrorDatos("«huella» no es válida.")

    def libre(campo: str, maximo: int) -> str:
        valor = datos.get(campo)
        return limpiar(valor, maximo) if isinstance(valor, str) else ""

    tipo = limpiar(_texto(datos, "tipo", 1, 80), 80)
    if not tipo:
        raise ErrorDatos("«tipo» no es válido.")
    return {"codigo": _texto(datos, "codigo", 8, 40), "colegio_id": usuario.colegio_id, "rol": usuario.rol,
            "creado_en": _fecha(datos, "creado_en"), "version": libre("version", 20),
            "plataforma": libre("plataforma", 20), "pantalla": libre("pantalla", 40), "tipo": tipo,
            "mensaje": libre("mensaje", 300), "traza": libre("traza", 1500), "huella": huella}


VALIDADORES = {"intento": _intento, "estado_refuerzo": _estado_refuerzo, "desbloqueo": _desbloqueo,
               "aviso": _aviso, "aviso_leido": _aviso_leido, "error_app": _error_app}


def validar_cambio(repo, usuario: Usuario, tipo: str, datos) -> dict:
    """Devuelve el cambio limpio y listo para aplicar, o lanza ``ErrorPermiso`` / ``ErrorDatos``."""
    if tipo not in VALIDADORES:
        raise ErrorDatos("Tipo de cambio desconocido.")
    if not isinstance(datos, dict):
        raise ErrorDatos("Los datos del cambio deben ser un objeto.")
    return VALIDADORES[tipo](repo, usuario, datos)

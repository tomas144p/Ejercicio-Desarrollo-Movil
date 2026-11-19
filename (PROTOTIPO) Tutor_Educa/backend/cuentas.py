"""
Altas, bajas y cambios de colegios, cursos y cuentas, con las reglas de QUIÉN puede hacer QUÉ.

Quién actúa (``actor``):
- ``None``: la persona que opera el servidor desde la consola (``python -m backend.crear_usuario``). Puede todo.
- **superadmin**: administra la plataforma. Crea colegios y sus administradores; ve todos los colegios.
- **admin**: administra UN colegio. Crea docentes, estudiantes y apoderados, cursos, y reinicia contraseñas.
- **docente**: gestiona los estudiantes de SUS cursos y los apoderados de esos estudiantes.
- estudiantes y apoderados no administran nada.

Principios:
- Las cuentas se crean **sin contraseña** y con un código de invitación de un solo uso (ver ``CodigosInvitacion``):
  nadie conoce ni reparte la contraseña de otra persona. El código se muestra una sola vez; solo se guarda su huella.
- Nada se borra: una baja **desactiva** la cuenta (se puede reactivar y se conserva el historial).
- Todo ocurre dentro del colegio de quien actúa. Un administrador o docente nunca toca otro colegio.
- Un docente nunca puede crear ni modificar administradores ni a otros docentes.

Python puro (sin FastAPI): se prueba directamente.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from backend.permisos import ErrorDatos, ErrorPermiso
from models.modelos import FORMATO_FECHA, Rol, Usuario
from services.seguridad import CLAVE_PENDIENTE, CodigosInvitacion, GestorClaves
from services.validaciones import LARGO_MINIMO_CLAVE_NUEVA as LARGO_MINIMO_CLAVE  # noqa: F401
from services.validaciones import validar_clave_nueva as _validar_clave_nueva
from services.validaciones import validar_correo

VIGENCIA_INVITACION_DIAS = 7
MENSAJE_CODIGO = "El código no es válido o venció. Pide uno nuevo a tu colegio."


class ErrorAlta(ErrorDatos):
    """No se pudo crear o cambiar la cuenta. El mensaje dice por qué."""


def validar_clave_nueva(clave: str) -> str:
    """La misma regla que usa la app, expresada como el error del servidor."""
    try:
        return _validar_clave_nueva(clave)
    except ValueError as error:
        raise ErrorAlta(str(error)) from error


def _ahora() -> str:
    return datetime.now().strftime(FORMATO_FECHA)


def _texto(valor, campo: str, minimo: int, maximo: int) -> str:
    if not isinstance(valor, str):
        raise ErrorAlta(f"«{campo}» debe ser texto.")
    limpio = " ".join(valor.split())
    if not minimo <= len(limpio) <= maximo:
        raise ErrorAlta(f"«{campo}» debe tener entre {minimo} y {maximo} caracteres.")
    return limpio


class Cuentas:
    def __init__(self, repo):
        self.repo = repo
        self.bd = repo.bd

    # ==================================================================================================
    # Lectura de apoyo
    # ==================================================================================================
    def _publico(self, fila: dict) -> dict:
        """Lo que se muestra de una cuenta: nunca la huella de la contraseña."""
        return {"id": int(fila["id"]), "correo": fila["correo"], "nombre": fila["nombre"], "rol": fila["rol"],
                "activo": bool(int(fila.get("activo", 1))), "pendiente": fila.get("clave_hash") == CLAVE_PENDIENTE,
                "colegio_id": int(fila["colegio_id"]) if fila.get("colegio_id") is not None else None,
                "creado_en": fila.get("creado_en")}

    def _usuario(self, usuario_id: int) -> dict:
        fila = self.repo.usuario_por_id(int(usuario_id))
        if fila is None:
            raise ErrorAlta("Esa cuenta no existe.")
        return fila

    def _cursos_del_docente(self, docente: Usuario) -> set[int]:
        filas = self.bd.consultar("SELECT id FROM cursos WHERE docente_id = ? AND colegio_id = ?",
                                  (docente.id, docente.colegio_id))
        return {int(f["id"]) for f in filas}

    def _colegio_vigente(self, colegio_id) -> dict:
        colegio = self.repo.colegio(int(colegio_id)) if colegio_id is not None else None
        if colegio is None:
            raise ErrorAlta("Ese colegio no existe. Para crear uno: python -m backend.crear_colegio")
        if not int(colegio.get("activo", 1)):
            raise ErrorAlta("Ese colegio está suspendido.")
        return colegio

    def _puede_gestionar(self, actor: Usuario | None, objetivo: dict) -> bool:
        """¿Puede esta persona ver y cambiar la cuenta del objetivo?"""
        if actor is None:
            return True
        if objetivo["rol"] == Rol.SUPERADMIN:
            return False                      # solo se maneja desde la consola del servidor
        if actor.rol == Rol.SUPERADMIN:
            return True
        if actor.colegio_id is None or objetivo.get("colegio_id") is None \
                or int(objetivo["colegio_id"]) != int(actor.colegio_id):
            return False
        if actor.rol == Rol.ADMIN:
            return objetivo["rol"] in (Rol.DOCENTE, Rol.ESTUDIANTE, Rol.APODERADO)
        if actor.rol == Rol.DOCENTE:
            cursos = self._cursos_del_docente(actor)
            if objetivo["rol"] == Rol.ESTUDIANTE:
                fila = self.bd.consultar_uno("SELECT curso_id FROM estudiantes WHERE usuario_id = ?", (objetivo["id"],))
                return bool(fila) and int(fila["curso_id"]) in cursos
            if objetivo["rol"] == Rol.APODERADO:
                filas = self.bd.consultar("SELECT curso_id FROM estudiantes WHERE apoderado_id = ?", (objetivo["id"],))
                return any(int(f["curso_id"]) in cursos for f in filas)
        return False

    def _exigir_gestion(self, actor: Usuario | None, objetivo: dict) -> None:
        if not self._puede_gestionar(actor, objetivo):
            raise ErrorPermiso("No puedes administrar esa cuenta.")

    def _colegio_del_actor(self, actor: Usuario | None, colegio_id) -> int:
        """El colegio sobre el que se actúa: el propio, salvo superadmin/consola que lo indican."""
        if actor is None or actor.rol == Rol.SUPERADMIN:
            if colegio_id is None:
                raise ErrorAlta("Indica el colegio (colegio_id).")
            self._colegio_vigente(colegio_id)
            return int(colegio_id)
        if actor.colegio_id is None:
            raise ErrorPermiso("Tu cuenta no está asignada a un colegio.")
        if colegio_id is not None and int(colegio_id) != int(actor.colegio_id):
            raise ErrorPermiso("Solo puedes administrar tu colegio.")
        return int(actor.colegio_id)

    # ==================================================================================================
    # Invitaciones y activación
    # ==================================================================================================
    def _nueva_invitacion(self, usuario_id: int, creada_por: int | None) -> tuple[str, str]:
        """Crea un código nuevo y deja sin efecto los anteriores. Devuelve (código, vence_en)."""
        ahora = _ahora()
        vence = (datetime.now() + timedelta(days=VIGENCIA_INVITACION_DIAS)).strftime(FORMATO_FECHA)
        self.bd.ejecutar("UPDATE invitaciones SET usada_en = ? WHERE usuario_id = ? AND usada_en IS NULL",
                         (ahora, usuario_id))
        for _ in range(5):
            codigo = CodigosInvitacion.generar()
            if not self.bd.consultar_uno("SELECT id FROM invitaciones WHERE codigo_hash = ?",
                                         (CodigosInvitacion.huella(codigo),)):
                self.bd.insertar("invitaciones", {"usuario_id": usuario_id,
                                                  "codigo_hash": CodigosInvitacion.huella(codigo),
                                                  "creada_por": creada_por, "creado_en": ahora, "vence_en": vence})
                return codigo, vence
        raise ErrorAlta("No se pudo generar un código. Intenta de nuevo.")

    def activar(self, correo: str, codigo: str, clave: str) -> dict:
        """Activa una cuenta con su código de invitación y le pone contraseña. Devuelve la fila de la cuenta."""
        validar_clave_nueva(clave)           # primero la contraseña: así un error aquí no revela si el código es válido
        fila = self.repo.usuario_por_correo((correo or "").strip().lower())
        if fila is None or not CodigosInvitacion.tiene_formato(codigo):
            raise ErrorAlta(MENSAJE_CODIGO)
        invitacion = self.bd.consultar_uno(
            "SELECT * FROM invitaciones WHERE usuario_id = ? AND codigo_hash = ? AND usada_en IS NULL",
            (fila["id"], CodigosInvitacion.huella(codigo)))
        if invitacion is None or str(invitacion["vence_en"]) < _ahora() or not int(fila.get("activo", 1)):
            raise ErrorAlta(MENSAJE_CODIGO)
        with self.bd.transaccion():
            self.bd.ejecutar("UPDATE usuarios SET clave_hash = ? WHERE id = ?",
                             (GestorClaves.generar_hash(clave), fila["id"]))
            self.bd.ejecutar("UPDATE invitaciones SET usada_en = ? WHERE usuario_id = ? AND usada_en IS NULL",
                             (_ahora(), fila["id"]))
        return self._usuario(fila["id"])

    def emitir_invitacion(self, actor: Usuario | None, usuario_id: int) -> dict:
        """Código nuevo para activar una cuenta o para recuperar el acceso (deja la contraseña anterior sin efecto)."""
        objetivo = self._usuario(usuario_id)
        self._exigir_gestion(actor, objetivo)
        if not int(objetivo.get("activo", 1)):
            raise ErrorAlta("La cuenta está desactivada: reactívala primero.")
        with self.bd.transaccion():
            self.bd.ejecutar("UPDATE usuarios SET clave_hash = ? WHERE id = ?", (CLAVE_PENDIENTE, objetivo["id"]))
            codigo, vence = self._nueva_invitacion(int(objetivo["id"]), actor.id if actor else None)
        return {"usuario": self._publico(self._usuario(usuario_id)), "codigo": codigo, "vence_en": vence}

    # ==================================================================================================
    # Colegios
    # ==================================================================================================
    def listar_colegios(self, actor: Usuario | None) -> list[dict]:
        filas = self.repo.colegios()
        if actor is not None and actor.rol != Rol.SUPERADMIN:
            filas = [f for f in filas if actor.colegio_id is not None and int(f["id"]) == int(actor.colegio_id)]
        return [{"id": int(f["id"]), "nombre": f["nombre"], "activo": bool(int(f["activo"]))} for f in filas]

    def crear_colegio(self, actor: Usuario | None, nombre: str) -> dict:
        if actor is not None and actor.rol != Rol.SUPERADMIN:
            raise ErrorPermiso("Solo la administración de la plataforma puede crear colegios.")
        nombre = _texto(nombre, "nombre", 3, 120)
        if self.bd.consultar_uno("SELECT id FROM colegios WHERE nombre = ?", (nombre,)):
            raise ErrorAlta("Ya existe un colegio con ese nombre.")
        nuevo = self.bd.insertar("colegios", {"nombre": nombre, "activo": 1, "creado_en": _ahora()})
        return {"id": int(nuevo), "nombre": nombre, "activo": True}

    def actualizar_colegio(self, actor: Usuario | None, colegio_id: int, nombre: str | None = None,
                           activo: bool | None = None) -> dict:
        if actor is not None and actor.rol != Rol.SUPERADMIN:
            raise ErrorPermiso("Solo la administración de la plataforma puede cambiar colegios.")
        colegio = self.repo.colegio(int(colegio_id))
        if colegio is None:
            raise ErrorAlta("Ese colegio no existe.")
        if nombre is not None:
            nombre = _texto(nombre, "nombre", 3, 120)
            otro = self.bd.consultar_uno("SELECT id FROM colegios WHERE nombre = ? AND id <> ?", (nombre, colegio["id"]))
            if otro:
                raise ErrorAlta("Ya existe un colegio con ese nombre.")
            self.bd.ejecutar("UPDATE colegios SET nombre = ? WHERE id = ?", (nombre, colegio["id"]))
        if activo is not None:
            self.bd.ejecutar("UPDATE colegios SET activo = ? WHERE id = ?", (1 if activo else 0, colegio["id"]))
        actual = self.repo.colegio(int(colegio_id))
        return {"id": int(actual["id"]), "nombre": actual["nombre"], "activo": bool(int(actual["activo"]))}

    # ==================================================================================================
    # Cuentas
    # ==================================================================================================
    def listar_usuarios(self, actor: Usuario | None, colegio_id: int | None = None, rol: str | None = None,
                        buscar: str | None = None, curso_id: int | None = None, limite: int = 300) -> list[dict]:
        if actor is not None and actor.rol not in Rol.ADMINISTRATIVOS:
            raise ErrorPermiso("Esta lista es solo para administradores.")
        colegio = self._colegio_del_actor(actor, colegio_id)
        condiciones, parametros = ["u.colegio_id = ?", "u.rol <> 'superadmin'"], [colegio]
        if rol:
            if rol not in Rol.PERFILES:
                raise ErrorAlta("Perfil desconocido.")
            condiciones.append("u.rol = ?")
            parametros.append(rol)
        if curso_id is not None:
            condiciones.append("e.curso_id = ?")
            parametros.append(int(curso_id))
        if buscar:
            condiciones.append("(u.nombre LIKE ? OR u.correo LIKE ?)")
            patron = f"%{buscar.strip()[:60]}%"
            parametros += [patron, patron]
        filas = self.bd.consultar(
            "SELECT u.id, u.correo, u.nombre, u.rol, u.activo, u.colegio_id, u.creado_en, u.clave_hash, "
            "e.curso_id, e.apoderado_id FROM usuarios u LEFT JOIN estudiantes e ON e.usuario_id = u.id "
            f"WHERE {' AND '.join(condiciones)} ORDER BY u.rol, u.nombre LIMIT {max(1, min(int(limite), 1000))}",
            parametros)
        resultado = []
        for fila in filas:
            dato = self._publico(fila)
            if fila["rol"] == Rol.ESTUDIANTE:
                dato["curso_id"] = int(fila["curso_id"]) if fila["curso_id"] is not None else None
                dato["apoderado_id"] = int(fila["apoderado_id"]) if fila["apoderado_id"] is not None else None
            resultado.append(dato)
        return resultado

    def crear_cuenta(self, actor: Usuario | None, correo: str, nombre: str, rol: str, *,
                     colegio_id: int | None = None, curso_id: int | None = None,
                     curso_nuevo: tuple[str, str] | None = None, apoderado_correo: str | None = None,
                     apoderado_nombre: str | None = None, clave: str | None = None) -> dict:
        """
        Crea una cuenta. Sin ``clave`` (lo normal) queda pendiente y se devuelve un código de invitación.
        ``clave`` solo la usa la consola del servidor (``actor=None``).
        """
        try:
            correo = validar_correo(correo).lower()
        except ValueError as error:
            raise ErrorAlta(str(error)) from error
        nombre = _texto(nombre, "nombre", 3, 120)
        if rol not in Rol.PERFILES:
            raise ErrorAlta(f"El perfil debe ser uno de: {', '.join(Rol.PERFILES)}.")
        if clave is not None:
            if actor is not None:
                raise ErrorPermiso("Las contraseñas no se entregan: usa un código de invitación.")
            validar_clave_nueva(clave)
        if rol == Rol.SUPERADMIN and actor is not None:
            raise ErrorPermiso("Los superadministradores solo se crean desde la consola del servidor.")
        if self.repo.usuario_por_correo(correo):
            raise ErrorAlta("Ya existe una cuenta con ese correo.")
        if curso_nuevo and rol != Rol.DOCENTE:
            raise ErrorAlta("Solo un docente puede tener un curso nuevo.")

        # --- permisos y colegio ---------------------------------------------------------------------
        curso = None
        if rol == Rol.ESTUDIANTE:
            curso = self.repo.curso(int(curso_id)) if curso_id is not None else None
            if curso is None:
                raise ErrorAlta("Para un estudiante indica un curso que exista (curso_id).")
            colegio = self._colegio_del_actor(actor, curso.colegio_id) if actor is not None \
                and actor.rol != Rol.SUPERADMIN else int(curso.colegio_id)
            if colegio_id is not None and int(colegio_id) != int(curso.colegio_id):
                raise ErrorAlta("Ese curso es de otro colegio.")
            self._colegio_vigente(colegio)
        elif rol == Rol.SUPERADMIN:
            colegio = None
        else:
            colegio = self._colegio_del_actor(actor, colegio_id)
        if actor is not None:
            self._exigir_derecho_a_crear(actor, rol, curso)
        if rol == Rol.ADMIN and colegio is None:
            raise ErrorAlta("Un administrador de colegio necesita un colegio.")

        # --- apoderado del estudiante ---------------------------------------------------------------
        apoderado = None
        if rol == Rol.ESTUDIANTE and apoderado_correo:
            apoderado = self._buscar_o_preparar_apoderado(apoderado_correo, apoderado_nombre, int(colegio))

        # --- se guarda todo junto o nada -------------------------------------------------------------
        with self.bd.transaccion():
            nuevo_id = self._insertar_usuario(correo, nombre, rol, colegio, clave)
            codigo = vence = None
            if clave is None:
                codigo, vence = self._nueva_invitacion(nuevo_id, actor.id if actor else None)
            if rol == Rol.DOCENTE and curso_nuevo:
                self.bd.insertar("cursos", {"nombre": _texto(curso_nuevo[0], "curso", 1, 60),
                                            "nivel": _texto(curso_nuevo[1], "nivel", 1, 40), "docente_id": nuevo_id,
                                            "anio": int(_ahora()[:4]), "colegio_id": int(colegio)})
            apoderado_resultado = None
            if rol == Rol.ESTUDIANTE:
                apoderado_resultado = self._vincular_o_crear(apoderado, actor)
                self.bd.insertar("estudiantes", {"usuario_id": nuevo_id, "curso_id": int(curso.id),
                                                 "apoderado_id": apoderado_resultado["id"] if apoderado_resultado else None,
                                                 "asistencia": 100})
        resultado = {"usuario": self._publico(self._usuario(nuevo_id)), "codigo": codigo, "vence_en": vence}
        if apoderado_resultado:
            resultado["apoderado"] = apoderado_resultado["detalle"]
        return resultado

    def _exigir_derecho_a_crear(self, actor: Usuario, rol: str, curso) -> None:
        if actor.rol == Rol.SUPERADMIN:
            return
        if actor.rol == Rol.ADMIN and rol in (Rol.DOCENTE, Rol.ESTUDIANTE, Rol.APODERADO):
            return
        if actor.rol == Rol.DOCENTE and rol == Rol.ESTUDIANTE and curso is not None \
                and int(curso.id) in self._cursos_del_docente(actor):
            return
        raise ErrorPermiso("No puedes crear ese tipo de cuenta.")

    def _insertar_usuario(self, correo, nombre, rol, colegio, clave) -> int:
        return int(self.bd.insertar("usuarios", {
            "correo": correo, "nombre": nombre, "rol": rol,
            "clave_hash": GestorClaves.generar_hash(clave) if clave else CLAVE_PENDIENTE,
            "activo": 1, "creado_en": _ahora(), "colegio_id": colegio}))

    def _buscar_o_preparar_apoderado(self, correo: str, nombre: str | None, colegio: int) -> dict:
        """Decide si el apoderado ya existe (se vincula) o hay que crearlo (se necesita su nombre)."""
        try:
            correo = validar_correo(correo).lower()
        except ValueError as error:
            raise ErrorAlta(str(error)) from error
        existente = self.repo.usuario_por_correo(correo)
        if existente is None:
            if not (nombre or "").strip():
                raise ErrorAlta("Ese apoderado aún no tiene cuenta: escribe también su nombre para crearla.")
            return {"nuevo": True, "correo": correo, "nombre": _texto(nombre, "nombre del apoderado", 3, 120),
                    "colegio": colegio}
        if existente["rol"] != Rol.APODERADO:
            raise ErrorAlta("Ese correo corresponde a una cuenta que no es de apoderado.")
        if existente.get("colegio_id") is None or int(existente["colegio_id"]) != colegio:
            raise ErrorAlta("Ese correo ya existe en otro colegio.")
        if not int(existente.get("activo", 1)):
            raise ErrorAlta("La cuenta de ese apoderado está desactivada.")
        return {"nuevo": False, "fila": existente}

    def _vincular_o_crear(self, apoderado: dict | None, actor: Usuario | None) -> dict | None:
        """Dentro de la transacción: crea al apoderado si hacía falta. Devuelve {id, detalle}."""
        if apoderado is None:
            return None
        if not apoderado["nuevo"]:
            return {"id": int(apoderado["fila"]["id"]),
                    "detalle": {"usuario": self._publico(apoderado["fila"]), "codigo": None, "existente": True}}
        nuevo_id = self._insertar_usuario(apoderado["correo"], apoderado["nombre"], Rol.APODERADO,
                                          apoderado["colegio"], None)
        codigo, vence = self._nueva_invitacion(nuevo_id, actor.id if actor else None)
        return {"id": nuevo_id, "detalle": {"usuario": self._publico(self._usuario(nuevo_id)), "codigo": codigo,
                                            "vence_en": vence, "existente": False}}

    def cambiar_cuenta(self, actor: Usuario | None, usuario_id: int, nombre: str | None = None,
                       activo: bool | None = None) -> dict:
        """Cambia el nombre o da de baja / reactiva una cuenta. Nunca se borra nada."""
        objetivo = self._usuario(usuario_id)
        self._exigir_gestion(actor, objetivo)
        if actor is not None and int(objetivo["id"]) == actor.id and activo is False:
            raise ErrorAlta("No puedes desactivar tu propia cuenta.")
        if nombre is not None:
            self.bd.ejecutar("UPDATE usuarios SET nombre = ? WHERE id = ?",
                             (_texto(nombre, "nombre", 3, 120), objetivo["id"]))
        advertencias = []
        if activo is not None:
            self.bd.ejecutar("UPDATE usuarios SET activo = ? WHERE id = ?", (1 if activo else 0, objetivo["id"]))
            if activo is False and objetivo["rol"] == Rol.DOCENTE:
                cursos = self.bd.consultar("SELECT nombre FROM cursos WHERE docente_id = ?", (objetivo["id"],))
                if cursos:
                    advertencias.append("Tiene cursos a cargo (" + ", ".join(c["nombre"] for c in cursos)
                                        + "): asígnalos a otra persona.")
        return {"usuario": self._publico(self._usuario(usuario_id)), "advertencias": advertencias}

    def listar_bajas(self, actor: Usuario) -> list[dict]:
        """Estudiantes dados de baja de los cursos de la docente (para poder reactivarlos). Solo se ven sus datos básicos."""
        if actor.rol != Rol.DOCENTE:
            raise ErrorPermiso("Esta lista es solo para docentes.")
        filas = self.bd.consultar(
            "SELECT u.id, u.nombre, u.correo, e.curso_id, c.nombre AS curso FROM estudiantes e "
            "JOIN usuarios u ON u.id = e.usuario_id JOIN cursos c ON c.id = e.curso_id "
            "WHERE c.docente_id = ? AND c.colegio_id = ? AND u.colegio_id = ? AND u.activo = 0 ORDER BY u.nombre",
            (actor.id, actor.colegio_id, actor.colegio_id))
        return [{"id": int(f["id"]), "nombre": f["nombre"], "correo": f["correo"], "curso_id": int(f["curso_id"]),
                 "curso": f["curso"]} for f in filas]

    # ==================================================================================================
    # Estudiantes: curso y apoderado
    # ==================================================================================================
    def cambiar_estudiante(self, actor: Usuario | None, estudiante_id: int, *, curso_id: int | None = None,
                           apoderado_correo: str | None = None, apoderado_nombre: str | None = None,
                           quitar_apoderado: bool = False) -> dict:
        objetivo = self._usuario(estudiante_id)
        if objetivo["rol"] != Rol.ESTUDIANTE:
            raise ErrorAlta("Esa cuenta no es de un estudiante.")
        self._exigir_gestion(actor, objetivo)
        colegio = int(objetivo["colegio_id"])
        cambios: dict = {}
        if curso_id is not None:
            curso = self.repo.curso(int(curso_id))
            if curso is None or int(curso.colegio_id) != colegio:
                raise ErrorAlta("Ese curso no existe en el colegio del estudiante.")
            if actor is not None and actor.rol == Rol.DOCENTE and int(curso.id) not in self._cursos_del_docente(actor):
                raise ErrorPermiso("Solo puedes mover estudiantes entre tus cursos.")
            cambios["curso_id"] = int(curso.id)
        apoderado = None
        if apoderado_correo:
            apoderado = self._buscar_o_preparar_apoderado(apoderado_correo, apoderado_nombre, colegio)
        if apoderado is None and not cambios and not quitar_apoderado:
            raise ErrorAlta("No indicaste ningún cambio.")
        with self.bd.transaccion():
            resultado_apoderado = self._vincular_o_crear(apoderado, actor)
            if resultado_apoderado:
                cambios["apoderado_id"] = resultado_apoderado["id"]
            elif quitar_apoderado:
                cambios["apoderado_id"] = None
            if cambios:
                asignaciones = ", ".join(f"{columna} = ?" for columna in cambios)
                self.bd.ejecutar(f"UPDATE estudiantes SET {asignaciones} WHERE usuario_id = ?",
                                 [*cambios.values(), objetivo["id"]])
        respuesta = {"usuario": self._publico(self._usuario(estudiante_id))}
        if resultado_apoderado:
            respuesta["apoderado"] = resultado_apoderado["detalle"]
        return respuesta

    # ==================================================================================================
    # Cursos
    # ==================================================================================================
    def listar_cursos(self, actor: Usuario | None, colegio_id: int | None = None) -> list[dict]:
        if actor is not None and actor.rol not in Rol.ADMINISTRATIVOS:
            raise ErrorPermiso("Esta lista es solo para administradores.")
        colegio = self._colegio_del_actor(actor, colegio_id)
        filas = self.bd.consultar(
            "SELECT c.id, c.nombre, c.nivel, c.anio, c.docente_id, d.nombre AS docente, "
            "(SELECT COUNT(*) FROM estudiantes e JOIN usuarios u ON u.id = e.usuario_id "
            " WHERE e.curso_id = c.id AND u.activo = 1) AS estudiantes "
            "FROM cursos c JOIN usuarios d ON d.id = c.docente_id WHERE c.colegio_id = ? ORDER BY c.nivel, c.nombre",
            (colegio,))
        return [{"id": int(f["id"]), "nombre": f["nombre"], "nivel": f["nivel"], "anio": int(f["anio"]),
                 "docente_id": int(f["docente_id"]), "docente": f["docente"], "estudiantes": int(f["estudiantes"])}
                for f in filas]

    # ==================================================================================================
    # Errores de la app
    # ==================================================================================================
    def listar_errores(self, actor: Usuario | None, colegio_id: int | None = None, dias: int = 30) -> dict:
        """Errores recientes agrupados por causa. El admin ve solo los de su colegio; la superadmin, los del colegio
        que indique o, sin indicarlo, los de todos (sirve para corregir fallas de la app)."""
        if actor is not None and actor.rol not in Rol.ADMINISTRATIVOS:
            raise ErrorPermiso("Esta lista es solo para administradores.")
        if actor is not None and actor.rol == Rol.ADMIN:
            colegio = self._colegio_del_actor(actor, colegio_id)
        else:
            colegio = int(colegio_id) if colegio_id is not None else None
        resultado = self.repo.errores_agrupados(colegio, dias)
        resultado["colegio_id"] = colegio
        return resultado

    def _docente_del_colegio(self, docente_id: int, colegio: int) -> dict:
        fila = self.repo.usuario_por_id(int(docente_id))
        if fila is None or fila["rol"] != Rol.DOCENTE or fila.get("colegio_id") is None \
                or int(fila["colegio_id"]) != colegio:
            raise ErrorAlta("Esa persona no es una docente de este colegio.")
        if not int(fila.get("activo", 1)):
            raise ErrorAlta("Esa docente está desactivada.")
        return fila

    def crear_curso(self, actor: Usuario | None, nombre: str, nivel: str, docente_id: int,
                    colegio_id: int | None = None) -> dict:
        if actor is not None and actor.rol not in Rol.ADMINISTRATIVOS:
            raise ErrorPermiso("Solo un administrador puede crear cursos.")
        colegio = self._colegio_del_actor(actor, colegio_id)
        self._colegio_vigente(colegio)
        self._docente_del_colegio(docente_id, colegio)
        nuevo = self.bd.insertar("cursos", {"nombre": _texto(nombre, "nombre", 1, 60),
                                            "nivel": _texto(nivel, "nivel", 1, 40), "docente_id": int(docente_id),
                                            "anio": int(_ahora()[:4]), "colegio_id": colegio})
        return next(c for c in self.listar_cursos(actor, colegio) if c["id"] == int(nuevo))

    def actualizar_curso(self, actor: Usuario | None, curso_id: int, nombre: str | None = None,
                         nivel: str | None = None, docente_id: int | None = None) -> dict:
        if actor is not None and actor.rol not in Rol.ADMINISTRATIVOS:
            raise ErrorPermiso("Solo un administrador puede cambiar cursos.")
        curso = self.repo.curso(int(curso_id))
        if curso is None:
            raise ErrorAlta("Ese curso no existe.")
        colegio = self._colegio_del_actor(actor, curso.colegio_id)
        if int(curso.colegio_id) != colegio:
            raise ErrorPermiso("Ese curso es de otro colegio.")
        cambios: dict = {}
        if nombre is not None:
            cambios["nombre"] = _texto(nombre, "nombre", 1, 60)
        if nivel is not None:
            cambios["nivel"] = _texto(nivel, "nivel", 1, 40)
        if docente_id is not None:
            self._docente_del_colegio(docente_id, colegio)
            cambios["docente_id"] = int(docente_id)
        if not cambios:
            raise ErrorAlta("No indicaste ningún cambio.")
        asignaciones = ", ".join(f"{columna} = ?" for columna in cambios)
        self.bd.ejecutar(f"UPDATE cursos SET {asignaciones} WHERE id = ?", [*cambios.values(), curso.id])
        return next(c for c in self.listar_cursos(actor, colegio) if c["id"] == int(curso.id))

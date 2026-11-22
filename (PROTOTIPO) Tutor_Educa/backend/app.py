"""
La API de Tutor Educa (FastAPI).

Rutas:
    GET  /salud      ¿está vivo el servidor y la base de datos? (sin sesión)
    POST /login      correo + contraseña  ->  tokens y datos básicos de la persona
    POST /renovar    token de renovación  ->  token de acceso nuevo
    GET  /paquete    los datos que le corresponden a la persona según su perfil
    POST /cambios    un cambio hecho en el celular (intento, aviso, desbloqueo...), revisado antes de aplicarse
    POST /ia/chat    pregunta al tutor IA (la clave de la IA vive solo aquí)
    GET  /panel      el panel web de administración (página estática; ver backend/panel.py)

Todo lo demás se rechaza. Las respuestas con datos nunca se guardan en caché.
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from backend import VERSION
from backend.ajustes import Ajustes
from backend.cuentas import MENSAJE_CODIGO, Cuentas, ErrorAlta
from backend.ia import ErrorUsoIA, ServicioIAServidor
from backend.panel import montar_panel
from backend.permisos import ErrorDatos, ErrorPermiso, validar_cambio
from backend.reloj import ErrorReloj, VigilanteReloj
from backend.seguridad_api import LimitadorVentana, ServicioTokens, TokenInvalido
from models.datos.conexiones import ErrorConexion
from models.datos.servidor import GestorServidor
from models.modelos import Rol, Usuario
from services.seguridad import GestorClaves

auditoria = logging.getLogger("tutor.auditoria")

# Para que "correo que no existe" tarde lo mismo que "contraseña incorrecta" (evita adivinar qué correos existen).
_HASH_FALSO = GestorClaves.generar_hash("clave-que-nadie-tiene")
MENSAJE_CREDENCIALES = "Correo o contraseña incorrectos."


class LoginIn(BaseModel):
    correo: str = Field(min_length=3, max_length=120)
    clave: str = Field(min_length=1, max_length=200)


class Estricto(BaseModel):
    """Rechaza campos que no existen: un error de escritura no se ignora en silencio."""
    model_config = ConfigDict(extra="forbid")


class ActivarIn(Estricto):
    correo: str = Field(min_length=3, max_length=120)
    codigo: str = Field(min_length=4, max_length=30)
    clave: str = Field(min_length=1, max_length=200)


class ColegioIn(Estricto):
    nombre: str = Field(min_length=3, max_length=120)


class ColegioPatch(Estricto):
    nombre: str | None = Field(default=None, max_length=120)
    activo: bool | None = None


class CursoNuevoIn(Estricto):
    nombre: str = Field(min_length=1, max_length=60)
    nivel: str = Field(min_length=1, max_length=40)


class CuentaIn(Estricto):
    correo: str = Field(min_length=3, max_length=120)
    nombre: str = Field(min_length=3, max_length=120)
    rol: str = Field(max_length=20)
    colegio_id: int | None = None
    curso_id: int | None = None
    curso_nuevo: CursoNuevoIn | None = None
    apoderado_correo: str | None = Field(default=None, max_length=120)
    apoderado_nombre: str | None = Field(default=None, max_length=120)


class CuentaPatch(Estricto):
    nombre: str | None = Field(default=None, max_length=120)
    activo: bool | None = None


class EstudiantePatch(Estricto):
    activo: bool | None = None
    nombre: str | None = Field(default=None, max_length=120)
    curso_id: int | None = None
    apoderado_correo: str | None = Field(default=None, max_length=120)
    apoderado_nombre: str | None = Field(default=None, max_length=120)
    quitar_apoderado: bool = False


class CursoIn(Estricto):
    nombre: str = Field(min_length=1, max_length=60)
    nivel: str = Field(min_length=1, max_length=40)
    docente_id: int
    colegio_id: int | None = None


class CursoPatch(Estricto):
    nombre: str | None = Field(default=None, max_length=60)
    nivel: str | None = Field(default=None, max_length=40)
    docente_id: int | None = None
    clases_sabado: bool | None = None


class EventoIn(Estricto):
    titulo: str = Field(min_length=1, max_length=120)
    tipo: str = Field(max_length=12)
    fecha_inicio: str = Field(min_length=10, max_length=10)
    fecha_fin: str | None = Field(default=None, min_length=10, max_length=10)
    curso_id: int | None = None
    descripcion: str = Field(default="", max_length=500)
    hay_clases: bool | None = None
    colegio_id: int | None = None


class FeriadosIn(Estricto):
    anio: int = Field(ge=2020, le=2100)
    colegio_id: int | None = None


class EstudianteNuevoIn(Estricto):
    correo: str = Field(min_length=3, max_length=120)
    nombre: str = Field(min_length=3, max_length=120)
    curso_id: int
    apoderado_correo: str | None = Field(default=None, max_length=120)
    apoderado_nombre: str | None = Field(default=None, max_length=120)


class RenovarIn(BaseModel):
    token_renovacion: str = Field(min_length=10, max_length=2000)


class CambioIn(BaseModel):
    tipo: str = Field(min_length=1, max_length=30)
    datos: dict


class MensajeIA(BaseModel):
    role: str = Field(max_length=12)
    content: str = Field(max_length=4_000)


class ChatIn(BaseModel):
    sistema: str = Field(min_length=1, max_length=12_000)
    mensajes: list[MensajeIA] = Field(min_length=1, max_length=20)


def _error(codigo: int, mensaje: str, espera: int = 0) -> HTTPException:
    cabeceras = {"Retry-After": str(espera)} if espera else None
    return HTTPException(status_code=codigo, detail=mensaje, headers=cabeceras)


def crear_app(ajustes: Ajustes | None = None, proveedor_ia=None, reloj=None) -> FastAPI:
    """``proveedor_ia`` y ``reloj`` existen para poder probar sin llamar a la IA real ni esperar minutos."""
    ajustes = (ajustes or Ajustes.desde_entorno()).validado()
    ajustes.carpeta_datos.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="Tutor Educa API", version=VERSION,
                  docs_url=None if ajustes.es_produccion else "/docs",
                  redoc_url=None, openapi_url=None if ajustes.es_produccion else "/openapi.json")
    gestor = GestorServidor(ajustes.bd, ajustes.carpeta_datos).inicializar()
    kwargs_reloj = {"reloj": reloj} if reloj else {}
    tokens = ServicioTokens(ajustes.jwt_secreto, ajustes.minutos_acceso, ajustes.dias_renovacion, **kwargs_reloj)
    fallos_correo = LimitadorVentana(ajustes.login_max_fallos, ajustes.login_ventana_seg, **kwargs_reloj)
    fallos_ip = LimitadorVentana(ajustes.login_max_fallos_ip, ajustes.login_ventana_seg, **kwargs_reloj)
    ia = ServicioIAServidor(ajustes, proveedor_ia)
    app.state.ajustes, app.state.gestor, app.state.tokens, app.state.ia = ajustes, gestor, tokens, ia

    # --- Protecciones generales -----------------------------------------------------------------
    @app.middleware("http")
    async def proteger(request: Request, siguiente):
        largo = request.headers.get("content-length")
        if largo and largo.isdigit() and int(largo) > ajustes.max_cuerpo_bytes:
            return JSONResponse({"detail": "La petición es demasiado grande."}, status_code=413)
        respuesta = await siguiente(request)
        respuesta.headers["Cache-Control"] = "no-store"
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        return respuesta

    def ip_de(request: Request) -> str:
        if ajustes.confiar_proxy:
            reenviada = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            if reenviada:
                return reenviada
        return request.client.host if request.client else "desconocida"

    def servidor():
        """La base de datos, o un 503 si no responde."""
        if gestor.servidor is None:
            gestor.disponible()      # reintenta conectar a MySQL cada 20 s
        if gestor.servidor is None:
            raise _error(503, "El servidor no puede conectarse a la base de datos.")
        return gestor.servidor

    vigilante = VigilanteReloj(lambda: servidor())

    def usuario_actual(authorization: str | None = Header(default=None)) -> Usuario:
        esquema, _, token = (authorization or "").partition(" ")
        if esquema.lower() != "bearer" or not token:
            raise _error(401, "Falta iniciar sesión.")
        try:
            datos = tokens.leer(token.strip(), "acceso")
        except TokenInvalido:
            raise _error(401, "La sesión venció. Vuelve a ingresar.")
        usuario = _usuario_vigente(datos)
        vigilante.anotar()                  # recuerda la hora más reciente que vio el reloj del servidor
        return usuario

    def _usuario_vigente(datos: dict) -> Usuario:
        # Se consulta en cada petición: si desactivan la cuenta o cambian su perfil, el token deja de servir.
        try:
            fila = servidor().usuario_por_id(datos["usuario_id"])
        except ErrorConexion:
            raise _error(503, "El servidor no puede conectarse a la base de datos.")
        if fila is None or not int(fila.get("activo", 1)) or fila["rol"] != datos.get("rol"):
            raise _error(401, "La sesión no es válida. Vuelve a ingresar.")
        usuario = Usuario.desde_fila(fila)
        if usuario.colegio_id != datos.get("col"):      # la persona cambió de colegio: la sesión anterior no sirve
            raise _error(401, "La sesión no es válida. Vuelve a ingresar.")
        _exigir_colegio_activo(usuario)
        return usuario

    def _exigir_colegio_activo(usuario: Usuario) -> None:
        """Sin colegio asignado, o con el colegio suspendido, la persona no recibe ni cambia nada."""
        if usuario.rol == Rol.SUPERADMIN:
            return                      # administra la plataforma: no pertenece a ningún colegio
        if usuario.colegio_id is None:
            raise _error(403, "Tu cuenta aún no está asignada a un colegio. Habla con la administración.")
        colegio = servidor().colegio(usuario.colegio_id)
        if colegio is None or not int(colegio.get("activo", 1)):
            raise _error(403, "El acceso de tu colegio está suspendido. Habla con la administración.")

    # --- Rutas ------------------------------------------------------------------------------------
    @app.get("/salud")
    def salud():
        # disponible() reintenta conectar a MySQL (cada 20 s) si la API arrancó antes que la base de datos,
        # algo normal cuando se reinicia todo junto. Sin esto, /salud quedaba en 503 hasta que otra ruta reintentara.
        if not gestor.disponible():
            raise _error(503, "Sin conexión con la base de datos.")
        return {"estado": "ok", "version": VERSION}

    @app.post("/login")
    def login(datos: LoginIn, request: Request):
        correo, ip = datos.correo.strip().lower(), ip_de(request)
        espera = max(fallos_correo.espera(f"correo:{correo}"), fallos_ip.espera(f"ip:{ip}"))
        if espera:
            auditoria.warning("login bloqueado correo=%s ip=%s", correo, ip)
            raise _error(429, "Demasiados intentos. Espera unos minutos y vuelve a probar.", espera)
        try:
            fila = servidor().usuario_por_correo(correo)
        except ErrorConexion:
            raise _error(503, "El servidor no puede conectarse a la base de datos.")
        clave_ok = GestorClaves.verificar(datos.clave, fila["clave_hash"] if fila else _HASH_FALSO)
        if fila is None or not clave_ok:
            fallos_correo.registrar(f"correo:{correo}")
            fallos_ip.registrar(f"ip:{ip}")
            auditoria.info("login fallido correo=%s ip=%s", correo, ip)
            raise _error(401, MENSAJE_CREDENCIALES)
        if not int(fila.get("activo", 1)):
            raise _error(403, "Esta cuenta está desactivada. Habla con tu colegio.")
        fallos_correo.limpiar(f"correo:{correo}")
        usuario = Usuario.desde_fila(fila)
        _exigir_colegio_activo(usuario)
        auditoria.info("login ok usuario=%s rol=%s colegio=%s ip=%s", usuario.id, usuario.rol, usuario.colegio_id, ip)
        return _sesion(usuario)

    def _sesion(usuario: Usuario) -> dict:
        """Los tokens y los datos básicos que recibe la app al ingresar (por contraseña o por código)."""
        colegio = servidor().colegio(usuario.colegio_id) if usuario.colegio_id is not None else None
        return {"token_acceso": tokens.crear_acceso(usuario.id, usuario.rol, usuario.colegio_id),
                "token_renovacion": tokens.crear_renovacion(usuario.id, usuario.rol, usuario.colegio_id),
                "expira_en": ajustes.minutos_acceso * 60,
                "usuario": {"id": usuario.id, "correo": usuario.correo, "nombre": usuario.nombre,
                            "rol": usuario.rol, "colegio_id": usuario.colegio_id,
                            "colegio": colegio["nombre"] if colegio else None}}

    @app.post("/activar")
    def activar(datos: ActivarIn, request: Request):
        """Activa una cuenta nueva (o recupera el acceso) con el código de invitación y deja a la persona dentro."""
        correo, ip = datos.correo.strip().lower(), ip_de(request)
        espera = max(fallos_correo.espera(f"correo:{correo}"), fallos_ip.espera(f"ip:{ip}"))
        if espera:
            raise _error(429, "Demasiados intentos. Espera unos minutos y vuelve a probar.", espera)
        try:
            fila = Cuentas(servidor()).activar(correo, datos.codigo, datos.clave)
        except ErrorAlta as error:
            if str(error) == MENSAJE_CODIGO:        # adivinar códigos cuenta como intento fallido (igual que las contraseñas)
                fallos_correo.registrar(f"correo:{correo}")
                fallos_ip.registrar(f"ip:{ip}")
                auditoria.info("activación fallida correo=%s ip=%s", correo, ip)
            raise _error(422, str(error))
        except ErrorConexion:
            raise _error(503, "El servidor no puede conectarse a la base de datos.")
        fallos_correo.limpiar(f"correo:{correo}")
        usuario = Usuario.desde_fila(fila)
        _exigir_colegio_activo(usuario)
        auditoria.info("activación ok usuario=%s rol=%s ip=%s", usuario.id, usuario.rol, ip)
        return _sesion(usuario)

    @app.post("/renovar")
    def renovar(datos: RenovarIn):
        try:
            info = tokens.leer(datos.token_renovacion, "renovacion")
        except TokenInvalido:
            raise _error(401, "La sesión venció. Vuelve a ingresar con tu contraseña.")
        usuario = _usuario_vigente(info)
        return {"token_acceso": tokens.crear_acceso(usuario.id, usuario.rol, usuario.colegio_id),
                "expira_en": ajustes.minutos_acceso * 60}

    @app.get("/paquete")
    def paquete(usuario: Usuario = Depends(usuario_actual)):
        if usuario.rol in Rol.ADMINISTRATIVOS:
            raise _error(403, "Tu perfil se administra desde el panel web, no desde la app.")
        try:
            return asdict(servidor().paquete_para(usuario))
        except ErrorConexion:
            raise _error(503, "El servidor no puede conectarse a la base de datos.")

    @app.post("/cambios")
    def cambios(cambio: CambioIn, usuario: Usuario = Depends(usuario_actual)):
        repo = servidor()
        try:
            if cambio.tipo == "asistencia_dia":
                vigilante.exigir_confiable()            # con el reloj atrasado no se registra asistencia
            limpio = validar_cambio(repo, usuario, cambio.tipo, cambio.datos)
            repo.aplicar_cambio(cambio.tipo, limpio)
        except ErrorPermiso as error:
            auditoria.warning("cambio denegado usuario=%s tipo=%s", usuario.id, cambio.tipo)
            raise _error(403, str(error))
        except ErrorReloj as error:
            auditoria.error("reloj atrasado: no se registró %s (usuario=%s)", cambio.tipo, usuario.id)
            raise _error(503, str(error))               # 503: el teléfono lo deja en su cola y reintenta solo
        except ErrorDatos as error:
            raise _error(422, str(error))
        except ErrorConexion:
            raise _error(503, "El servidor no puede conectarse a la base de datos.")
        auditoria.info("cambio ok usuario=%s tipo=%s", usuario.id, cambio.tipo)
        return {"ok": True}

    @app.post("/ia/chat")
    def chat(datos: ChatIn, usuario: Usuario = Depends(usuario_actual)):
        try:
            texto = ia.responder(usuario, datos.sistema, [m.model_dump() for m in datos.mensajes])
        except ErrorUsoIA as error:
            raise _error(error.codigo, str(error), error.espera)
        auditoria.info("ia usuario=%s", usuario.id)
        return {"texto": texto}


    # --- Administración de colegios, cuentas y cursos ---------------------------------------------------
    def administrador(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.rol not in Rol.ADMINISTRATIVOS:
            raise _error(403, "Esta función es solo para administradores.")
        return usuario

    def docente(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.rol != Rol.DOCENTE:
            raise _error(403, "Esta función es solo para docentes.")
        return usuario

    def gestionar(actor: Usuario, accion: str, funcion):
        """Ejecuta una operación de cuentas con el mapeo de errores y el registro de auditoría."""
        try:
            resultado = funcion(Cuentas(servidor()))
        except ErrorPermiso as error:
            auditoria.warning("cuentas denegado actor=%s accion=%s", actor.id, accion)
            raise _error(403, str(error))
        except ErrorDatos as error:
            raise _error(422, str(error))
        except ErrorConexion:
            raise _error(503, "El servidor no puede conectarse a la base de datos.")
        auditoria.info("cuentas ok actor=%s accion=%s", actor.id, accion)       # nunca se registran los códigos
        return resultado

    # --- Hora del servidor ----------------------------------------------------------------------------
    @app.get("/admin/servidor/hora")
    def admin_hora_servidor(actor: Usuario = Depends(administrador)):
        """La hora que cree tener el servidor y si su reloj parece atrasado (el panel la muestra)."""
        try:
            return vigilante.estado()
        except ErrorConexion:
            raise _error(503, "El servidor no puede conectarse a la base de datos.")

    @app.post("/admin/servidor/hora/confirmar")
    def admin_confirmar_hora(actor: Usuario = Depends(administrador)):
        """Solo el superadministrador: confirma que la hora ACTUAL del servidor es la correcta (por ejemplo, después
        de haber corregido un reloj que estaba adelantado)."""
        if actor.rol != Rol.SUPERADMIN:
            auditoria.warning("cuentas denegado actor=%s accion=reloj.confirmar", actor.id)
            raise _error(403, "Solo el superadministrador puede confirmar la hora del servidor.")
        try:
            estado = vigilante.restablecer()
        except ErrorConexion:
            raise _error(503, "El servidor no puede conectarse a la base de datos.")
        auditoria.warning("reloj confirmado por actor=%s hora=%s", actor.id, estado["ahora"])
        return estado

    @app.get("/admin/errores")
    def admin_errores(colegio_id: int | None = None, dias: int = Query(default=30, ge=1, le=365),
                      actor: Usuario = Depends(administrador)):
        return gestionar(actor, "errores.listar", lambda c: c.listar_errores(actor, colegio_id, dias))

    @app.get("/admin/colegios")
    def admin_colegios(actor: Usuario = Depends(administrador)):
        return gestionar(actor, "colegios.listar", lambda c: c.listar_colegios(actor))

    @app.post("/admin/colegios", status_code=201)
    def admin_crear_colegio(datos: ColegioIn, actor: Usuario = Depends(administrador)):
        return gestionar(actor, "colegios.crear", lambda c: c.crear_colegio(actor, datos.nombre))

    @app.patch("/admin/colegios/{colegio_id}")
    def admin_cambiar_colegio(colegio_id: int, datos: ColegioPatch, actor: Usuario = Depends(administrador)):
        return gestionar(actor, "colegios.cambiar", lambda c: c.actualizar_colegio(actor, colegio_id, datos.nombre,
                                                                                    datos.activo))

    @app.get("/admin/usuarios")
    def admin_usuarios(colegio_id: int | None = None, rol: str | None = None, buscar: str | None = None,
                       curso_id: int | None = None, limite: int = Query(default=300, ge=1, le=1000),
                       actor: Usuario = Depends(administrador)):
        return gestionar(actor, "usuarios.listar",
                         lambda c: c.listar_usuarios(actor, colegio_id, rol, buscar, curso_id, limite))

    @app.post("/admin/usuarios", status_code=201)
    def admin_crear_usuario(datos: CuentaIn, actor: Usuario = Depends(administrador)):
        return gestionar(actor, "usuarios.crear", lambda c: c.crear_cuenta(
            actor, datos.correo, datos.nombre, datos.rol, colegio_id=datos.colegio_id, curso_id=datos.curso_id,
            curso_nuevo=(datos.curso_nuevo.nombre, datos.curso_nuevo.nivel) if datos.curso_nuevo else None,
            apoderado_correo=datos.apoderado_correo, apoderado_nombre=datos.apoderado_nombre))

    @app.patch("/admin/usuarios/{usuario_id}")
    def admin_cambiar_usuario(usuario_id: int, datos: CuentaPatch, actor: Usuario = Depends(administrador)):
        return gestionar(actor, "usuarios.cambiar",
                         lambda c: c.cambiar_cuenta(actor, usuario_id, datos.nombre, datos.activo))

    @app.post("/admin/usuarios/{usuario_id}/invitacion")
    def admin_invitar(usuario_id: int, actor: Usuario = Depends(administrador)):
        return gestionar(actor, "usuarios.invitacion", lambda c: c.emitir_invitacion(actor, usuario_id))

    @app.patch("/admin/estudiantes/{estudiante_id}")
    def admin_cambiar_estudiante(estudiante_id: int, datos: EstudiantePatch, actor: Usuario = Depends(administrador)):
        return gestionar(actor, "estudiantes.cambiar", lambda c: _cambiar_estudiante(c, actor, estudiante_id, datos))

    @app.get("/admin/cursos")
    def admin_cursos(colegio_id: int | None = None, actor: Usuario = Depends(administrador)):
        return gestionar(actor, "cursos.listar", lambda c: c.listar_cursos(actor, colegio_id))

    @app.post("/admin/cursos", status_code=201)
    def admin_crear_curso(datos: CursoIn, actor: Usuario = Depends(administrador)):
        return gestionar(actor, "cursos.crear", lambda c: c.crear_curso(actor, datos.nombre, datos.nivel,
                                                                         datos.docente_id, datos.colegio_id))

    @app.patch("/admin/cursos/{curso_id}")
    def admin_cambiar_curso(curso_id: int, datos: CursoPatch, actor: Usuario = Depends(administrador)):
        return gestionar(actor, "cursos.cambiar", lambda c: c.actualizar_curso(
            actor, curso_id, datos.nombre, datos.nivel, datos.docente_id, datos.clases_sabado))

    # --- Calendario: eventos y feriados del colegio (la docente maneja los de sus cursos desde la app) ----------
    @app.get("/admin/eventos")
    def admin_eventos(colegio_id: int | None = None, anio: int | None = Query(default=None, ge=2020, le=2100),
                      actor: Usuario = Depends(administrador)):
        return gestionar(actor, "eventos.listar", lambda c: c.listar_eventos(actor, colegio_id, anio))

    @app.post("/admin/eventos", status_code=201)
    def admin_crear_evento(datos: EventoIn, actor: Usuario = Depends(administrador)):
        return gestionar(actor, "eventos.crear", lambda c: c.crear_evento(
            actor, datos.titulo, datos.tipo, datos.fecha_inicio, datos.fecha_fin, datos.curso_id, datos.descripcion,
            datos.hay_clases, datos.colegio_id))

    @app.delete("/admin/eventos/{evento_id}")
    def admin_baja_evento(evento_id: int, actor: Usuario = Depends(administrador)):
        return gestionar(actor, "eventos.baja", lambda c: c.dar_de_baja_evento(actor, evento_id))

    @app.post("/admin/eventos/feriados")
    def admin_cargar_feriados(datos: FeriadosIn, actor: Usuario = Depends(administrador)):
        return gestionar(actor, "eventos.feriados", lambda c: c.cargar_feriados(actor, datos.anio, datos.colegio_id))

    # --- Lo que puede hacer una docente con SUS estudiantes y apoderados (la app la usa desde el celular) -----
    @app.post("/docente/estudiantes", status_code=201)
    def docente_crear_estudiante(datos: EstudianteNuevoIn, actor: Usuario = Depends(docente)):
        return gestionar(actor, "estudiantes.crear", lambda c: c.crear_cuenta(
            actor, datos.correo, datos.nombre, Rol.ESTUDIANTE, curso_id=datos.curso_id,
            apoderado_correo=datos.apoderado_correo, apoderado_nombre=datos.apoderado_nombre))

    @app.get("/docente/estudiantes/bajas")
    def docente_bajas(actor: Usuario = Depends(docente)):
        return gestionar(actor, "estudiantes.bajas", lambda c: c.listar_bajas(actor))

    @app.patch("/docente/estudiantes/{estudiante_id}")
    def docente_cambiar_estudiante(estudiante_id: int, datos: EstudiantePatch, actor: Usuario = Depends(docente)):
        return gestionar(actor, "estudiantes.cambiar", lambda c: _cambiar_estudiante(c, actor, estudiante_id, datos))

    @app.post("/docente/usuarios/{usuario_id}/invitacion")
    def docente_invitar(usuario_id: int, actor: Usuario = Depends(docente)):
        return gestionar(actor, "usuarios.invitacion", lambda c: c.emitir_invitacion(actor, usuario_id))

    def _cambiar_estudiante(cuentas: Cuentas, actor: Usuario, estudiante_id: int, datos: EstudiantePatch) -> dict:
        """Nombre, baja/alta, curso y apoderado de un estudiante: todo junto o nada."""
        with cuentas.bd.transaccion():
            resultado: dict = {}
            if datos.nombre is not None or datos.activo is not None:
                resultado = cuentas.cambiar_cuenta(actor, estudiante_id, datos.nombre, datos.activo)
            if datos.curso_id is not None or datos.apoderado_correo or datos.quitar_apoderado:
                resultado = {**resultado, **cuentas.cambiar_estudiante(
                    actor, estudiante_id, curso_id=datos.curso_id, apoderado_correo=datos.apoderado_correo,
                    apoderado_nombre=datos.apoderado_nombre, quitar_apoderado=datos.quitar_apoderado)}
            if not resultado:
                raise ErrorAlta("No indicaste ningún cambio.")
        return resultado

    if ajustes.panel_activo:
        montar_panel(app)

    return app

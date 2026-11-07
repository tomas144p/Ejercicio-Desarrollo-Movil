"""
La API de Tutor Educa (FastAPI).

Rutas:
    GET  /salud      ¿está vivo el servidor y la base de datos? (sin sesión)
    POST /login      correo + contraseña  ->  tokens y datos básicos de la persona
    POST /renovar    token de renovación  ->  token de acceso nuevo
    GET  /paquete    los datos que le corresponden a la persona según su perfil
    POST /cambios    un cambio hecho en el celular (intento, aviso, desbloqueo...), revisado antes de aplicarse
    POST /ia/chat    pregunta al tutor IA (la clave de la IA vive solo aquí)

Todo lo demás se rechaza. Las respuestas con datos nunca se guardan en caché.
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend import VERSION
from backend.ajustes import Ajustes
from backend.ia import ErrorUsoIA, ServicioIAServidor
from backend.permisos import ErrorDatos, ErrorPermiso, validar_cambio
from backend.seguridad_api import LimitadorVentana, ServicioTokens, TokenInvalido
from models.datos.conexiones import ErrorConexion
from models.datos.servidor import GestorServidor
from models.modelos import Usuario
from services.seguridad import GestorClaves

auditoria = logging.getLogger("tutor.auditoria")

# Para que "correo que no existe" tarde lo mismo que "contraseña incorrecta" (evita adivinar qué correos existen).
_HASH_FALSO = GestorClaves.generar_hash("clave-que-nadie-tiene")
MENSAJE_CREDENCIALES = "Correo o contraseña incorrectos."


class LoginIn(BaseModel):
    correo: str = Field(min_length=3, max_length=120)
    clave: str = Field(min_length=1, max_length=200)


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

    def usuario_actual(authorization: str | None = Header(default=None)) -> Usuario:
        esquema, _, token = (authorization or "").partition(" ")
        if esquema.lower() != "bearer" or not token:
            raise _error(401, "Falta iniciar sesión.")
        try:
            datos = tokens.leer(token.strip(), "acceso")
        except TokenInvalido:
            raise _error(401, "La sesión venció. Vuelve a ingresar.")
        return _usuario_vigente(datos)

    def _usuario_vigente(datos: dict) -> Usuario:
        # Se consulta en cada petición: si desactivan la cuenta o cambian su perfil, el token deja de servir.
        try:
            fila = servidor().usuario_por_id(datos["usuario_id"])
        except ErrorConexion:
            raise _error(503, "El servidor no puede conectarse a la base de datos.")
        if fila is None or not int(fila.get("activo", 1)) or fila["rol"] != datos.get("rol"):
            raise _error(401, "La sesión no es válida. Vuelve a ingresar.")
        return Usuario.desde_fila(fila)

    # --- Rutas ------------------------------------------------------------------------------------
    @app.get("/salud")
    def salud():
        if gestor.servidor is None or not gestor.servidor.probar():
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
        auditoria.info("login ok usuario=%s rol=%s ip=%s", usuario.id, usuario.rol, ip)
        return {"token_acceso": tokens.crear_acceso(usuario.id, usuario.rol),
                "token_renovacion": tokens.crear_renovacion(usuario.id, usuario.rol),
                "expira_en": ajustes.minutos_acceso * 60,
                "usuario": {"id": usuario.id, "correo": usuario.correo, "nombre": usuario.nombre,
                            "rol": usuario.rol}}

    @app.post("/renovar")
    def renovar(datos: RenovarIn):
        try:
            info = tokens.leer(datos.token_renovacion, "renovacion")
        except TokenInvalido:
            raise _error(401, "La sesión venció. Vuelve a ingresar con tu contraseña.")
        usuario = _usuario_vigente(info)
        return {"token_acceso": tokens.crear_acceso(usuario.id, usuario.rol), "expira_en": ajustes.minutos_acceso * 60}

    @app.get("/paquete")
    def paquete(usuario: Usuario = Depends(usuario_actual)):
        try:
            return asdict(servidor().paquete_para(usuario))
        except ErrorConexion:
            raise _error(503, "El servidor no puede conectarse a la base de datos.")

    @app.post("/cambios")
    def cambios(cambio: CambioIn, usuario: Usuario = Depends(usuario_actual)):
        repo = servidor()
        try:
            limpio = validar_cambio(repo, usuario, cambio.tipo, cambio.datos)
            repo.aplicar_cambio(cambio.tipo, limpio)
        except ErrorPermiso as error:
            auditoria.warning("cambio denegado usuario=%s tipo=%s", usuario.id, cambio.tipo)
            raise _error(403, str(error))
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

    return app

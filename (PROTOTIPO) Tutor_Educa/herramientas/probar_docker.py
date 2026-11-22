"""
Prueba el despliegue completo (API + MySQL) como lo vería la app. Usa solo la biblioteca estándar de Python.

Con Docker Desktop (lo normal):

    python herramientas/probar_docker.py

  Supone que ya levantaste todo con:
    docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build

Sin Docker (sirve para probar el script mismo contra un servidor que ya corre, con las variables TUTOR_* puestas):

    python herramientas/probar_docker.py --sin-docker --url http://127.0.0.1:8000

Qué comprueba: que la API responde y habla con MySQL; que en producción no expone la documentación; que se pueden
crear colegios y cuentas; que el ingreso, el bloqueo por intentos y los permisos funcionan; que un colegio NO ve ni
cambia datos de otro; que las cuentas se activan con códigos de invitación (superadmin -> administrador -> docente ->
estudiante y apoderado, cada uno creando al siguiente con la API); y (con Docker) que los datos sobreviven a un
reinicio de los contenedores.

Crea colegios y cuentas de PRUEBA con un sufijo al azar (se puede repetir). Para empezar de cero:
    docker compose -f docker-compose.yml -f docker-compose.local.yml down -v
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"
COMPOSE = ["docker", "compose", "-f", "docker-compose.yml", "-f", "docker-compose.local.yml"]
CLAVE_PRUEBA = "Prueba-Docker-2026"


class Informe:
    def __init__(self):
        self.fallas: list[str] = []
        self.total = 0

    def paso(self, titulo: str, ok: bool, detalle: str = "") -> bool:
        self.total += 1
        print(f"  [{'OK' if ok else 'FALLA'}] {titulo}" + (f"  ->  {detalle}" if detalle and not ok else ""))
        if not ok:
            self.fallas.append(titulo)
        return ok

    def info(self, texto: str) -> None:
        print(f"  [info] {texto}")


def titulo(texto: str) -> None:
    print(f"\n== {texto}")


# ---------------------------------------------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------------------------------------------
class Api:
    def __init__(self, url: str):
        self.url = url.rstrip("/")

    def pedir(self, metodo: str, ruta: str, cuerpo: dict | None = None, token: str = "") -> tuple[int, dict]:
        cabeceras = {"accept": "application/json"}
        datos = None
        if cuerpo is not None:
            datos = json.dumps(cuerpo).encode("utf-8")
            cabeceras["content-type"] = "application/json"
        if token:
            cabeceras["authorization"] = f"Bearer {token}"
        solicitud = urllib.request.Request(self.url + ruta, data=datos, method=metodo, headers=cabeceras)
        try:
            with urllib.request.urlopen(solicitud, timeout=20) as respuesta:
                return respuesta.status, self._json(respuesta.read())
        except urllib.error.HTTPError as error:
            return error.code, self._json(error.read())
        except (urllib.error.URLError, OSError):
            return 0, {}

    @staticmethod
    def _json(crudo: bytes) -> dict:
        try:
            datos = json.loads(crudo.decode("utf-8") or "{}")
            return datos if isinstance(datos, dict) else {"lista": datos}
        except ValueError:
            return {}

    def ingresar(self, correo: str, clave: str = CLAVE_PRUEBA) -> tuple[int, dict]:
        return self.pedir("POST", "/login", {"correo": correo, "clave": clave})

    def esperar_salud(self, segundos: int = 120) -> bool:
        limite = time.time() + segundos
        while time.time() < limite:
            estado, datos = self.pedir("GET", "/salud")
            if estado == 200 and datos.get("estado") == "ok":
                return True
            time.sleep(2)
        return False


# ---------------------------------------------------------------------------------------------------------------
# Herramientas de alta (dentro del contenedor, o en este mismo PC con --sin-docker)
# ---------------------------------------------------------------------------------------------------------------
def ejecutar(sin_docker: bool, modulo: str, *argumentos: str) -> tuple[bool, str]:
    entorno = dict(os.environ, TUTOR_CLAVE_NUEVA=CLAVE_PRUEBA)
    if sin_docker:
        orden = [sys.executable, "-m", modulo, *argumentos]
    else:
        orden = [*COMPOSE, "exec", "-T", "-e", f"TUTOR_CLAVE_NUEVA={CLAVE_PRUEBA}", "api", "python", "-m", modulo,
                 *argumentos]
    resultado = subprocess.run(orden, cwd=RAIZ, env=entorno, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=120)
    return resultado.returncode == 0, (resultado.stdout + resultado.stderr).strip()


def codigo_de(texto: str) -> str | None:
    """El primer código de invitación (ABCDE-FGHJK) que aparece en la salida de las herramientas."""
    coincidencia = re.search(r"\b([0-9A-Z]{5}-[0-9A-Z]{5})\b", texto)
    return coincidencia.group(1) if coincidencia else None


def numero(texto: str, patron: str) -> int | None:
    coincidencia = re.search(patron, texto)
    return int(coincidencia.group(1)) if coincidencia else None


# ---------------------------------------------------------------------------------------------------------------
def preparar(informe: Informe, sin_docker: bool) -> bool:
    titulo("0. Antes de empezar")
    if sin_docker:
        informe.info("Modo sin Docker: se usan las variables TUTOR_* de esta consola.")
        return True
    try:
        version = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True, timeout=30)
        informe.paso("Docker Compose está instalado", version.returncode == 0,
                     "Instala Docker Desktop: https://www.docker.com/products/docker-desktop")
        demonio = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=60)
        informe.paso("Docker Desktop está abierto y corriendo", demonio.returncode == 0,
                     "Abre Docker Desktop y espera a que diga «Engine running».")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        informe.paso("Docker está disponible", False, "No se encontró el comando «docker». Instala Docker Desktop.")
        return False
    informe.paso("Existe el archivo .env", (RAIZ / ".env").exists(),
                 "Copia backend/.env.ejemplo como .env y complétalo (TUTOR_DOMINIO=localhost sirve en tu PC).")
    sql = RAIZ / "database" / "tutor_educa_produccion.sql"
    informe.paso("Existe database/tutor_educa_produccion.sql", sql.is_file(),
                 "Genéralo con: python herramientas/generar_sql_mysql.py --produccion")
    return not informe.fallas


def probar(url: str, sin_docker: bool, reiniciar: bool) -> int:
    informe, api = Informe(), Api(url)
    if not preparar(informe, sin_docker):
        return resumen(informe)

    titulo("1. La API y la base de datos responden")
    if not informe.paso(f"GET {url}/salud responde «ok» (esperando hasta 2 min)", api.esperar_salud(),
                        "Revisa los registros con: docker compose logs api db"):
        return resumen(informe)
    informe.paso("La documentación automática está apagada (modo producción)",
                 api.pedir("GET", "/docs")[0] == 404 and api.pedir("GET", "/openapi.json")[0] == 404)

    titulo("2. Crear colegios y cuentas de prueba")
    sufijo = secrets.token_hex(2)
    correos = {n: f"{n}.{sufijo}@prueba.local" for n in ("doc.a", "apo.a", "est.a", "doc.b", "apo.b")}
    ok, salida_a = ejecutar(sin_docker, "backend.crear_colegio", f"Colegio Prueba A {sufijo}")
    colegio_a = numero(salida_a, r"id (\d+)")
    ok_b, salida_b = ejecutar(sin_docker, "backend.crear_colegio", f"Colegio Prueba B {sufijo}")
    colegio_b = numero(salida_b, r"id (\d+)")
    if not informe.paso("Se crearon dos colegios", ok and ok_b and colegio_a is not None and colegio_b is not None,
                        f"{salida_a} | {salida_b}"):
        return resumen(informe)

    def alta(rol, clave_correo, nombre, *extra) -> tuple[bool, str]:
        return ejecutar(sin_docker, "backend.crear_usuario", rol, correos[clave_correo], nombre, *extra)

    ok1, s1 = alta("docente", "doc.a", "Docente A", "--colegio-id", str(colegio_a), "--curso", "7° B", "--nivel", "7°")
    curso_a = numero(s1, r"Curso creado \(id (\d+)\)")
    ok2, s2 = alta("docente", "doc.b", "Docente B", "--colegio-id", str(colegio_b), "--curso", "5° A", "--nivel", "5°")
    curso_b = numero(s2, r"Curso creado \(id (\d+)\)")
    ok3, s3 = alta("apoderado", "apo.a", "Apoderado A", "--colegio-id", str(colegio_a))
    ok4, s4 = alta("apoderado", "apo.b", "Apoderado B", "--colegio-id", str(colegio_b))
    ok5, s5 = alta("estudiante", "est.a", "Estudiante A", "--curso-id", str(curso_a), "--apoderado", correos["apo.a"])
    informe.paso("Se crearon docentes, apoderados y un estudiante", all((ok1, ok2, ok3, ok4, ok5)),
                 " | ".join(s for s in (s1, s2, s3, s4, s5) if "creada" not in s))
    if informe.fallas:
        return resumen(informe)
    ok6, s6 = alta("estudiante", "est.a", "Estudiante Repetido", "--curso-id", str(curso_a))
    informe.paso("No deja crear dos cuentas con el mismo correo", not ok6)

    titulo("3. Ingreso")
    estado, datos_a = api.ingresar(correos["doc.a"])
    informe.paso("La docente A ingresa y ve su colegio", estado == 200 and f"Prueba A {sufijo}" in str(datos_a),
                 f"estado {estado}")
    estado_b, datos_b = api.ingresar(correos["doc.b"])
    informe.paso("La docente B ingresa en el otro colegio", estado_b == 200 and f"Prueba B {sufijo}" in str(datos_b))
    mala = api.ingresar(correos["doc.a"], "otra-clave-larga-1")
    inexistente = api.ingresar(f"fantasma.{sufijo}@prueba.local")
    informe.paso("Contraseña mala y correo inexistente dan el mismo error",
                 mala[0] == 401 and inexistente[0] == 401 and mala[1].get("detail") == inexistente[1].get("detail"))
    informe.paso("Sin sesión o con un token falso se rechaza",
                 api.pedir("GET", "/paquete")[0] == 401 and api.pedir("GET", "/paquete", token="falso.falso.falso")[0] == 401)
    señuelo = f"bloqueo.{sufijo}@prueba.local"
    estados = [api.ingresar(señuelo, "mala-clave-larga-1")[0] for _ in range(6)]
    informe.paso("Tras 5 intentos fallidos se bloquea (429)", estados[:5] == [401] * 5 and estados[5] == 429,
                 str(estados))

    titulo("4. Cada colegio ve solo lo suyo")
    token_a, token_b = datos_a.get("token_acceso", ""), datos_b.get("token_acceso", "")
    paquete_a = api.pedir("GET", "/paquete", token=token_a)[1]
    paquete_b = api.pedir("GET", "/paquete", token=token_b)[1]
    informe.paso("El paquete del colegio A trae su estudiante y sus datos",
                 "Estudiante A" in str(paquete_a) and f"Prueba A {sufijo}" in str(paquete_a))
    informe.paso("El paquete del colegio B NO trae nada del colegio A",
                 "Estudiante A" not in str(paquete_b) and "Prueba A" not in str(paquete_b) and correos["doc.a"] not in str(paquete_b))
    informe.paso("Ningún paquete incluye contraseñas", "clave_hash" not in str(paquete_a) + str(paquete_b))
    ahora = datetime.now().strftime(FORMATO_FECHA)
    aviso = {"codigo": f"aviso-{sufijo}-0001", "curso_id": curso_a, "estudiante_id": None, "titulo": "Hola",
             "cuerpo": "Aviso de prueba", "tipo": "info", "creado_en": ahora}
    informe.paso("La docente A publica un aviso en su curso (200)",
                 api.pedir("POST", "/cambios", {"tipo": "aviso", "datos": aviso}, token_a)[0] == 200)
    informe.paso("La docente B NO puede publicar en el curso de A (403)",
                 api.pedir("POST", "/cambios", {"tipo": "aviso", "datos": dict(aviso, codigo=f"aviso-{sufijo}-0002")},
                           token_b)[0] == 403)
    _, apo_a = api.ingresar(correos["apo.a"])
    _, apo_b = api.ingresar(correos["apo.b"])
    leido = {"aviso_codigo": aviso["codigo"], "fecha": ahora}
    informe.paso("El apoderado de B NO puede confirmar un aviso del colegio A (403)",
                 api.pedir("POST", "/cambios", {"tipo": "aviso_leido", "datos": leido}, apo_b.get("token_acceso", ""))[0] == 403)
    informe.paso("El apoderado de A confirma «Recibido» (200)",
                 api.pedir("POST", "/cambios", {"tipo": "aviso_leido", "datos": leido}, apo_a.get("token_acceso", ""))[0] == 200)

    titulo("5. Administración y códigos de invitación")
    super_correo = f"super.{sufijo}@prueba.local"
    ok_s, salida_s = ejecutar(sin_docker, "backend.crear_usuario", "superadmin", super_correo, "Super Prueba",
                              "--invitacion")
    codigo_s = codigo_de(salida_s)
    informe.paso("La consola crea a la superadministradora con un código de invitación", ok_s and bool(codigo_s), salida_s)
    if not (ok_s and codigo_s):
        return resumen(informe)
    estado, sesion_s = api.pedir("POST", "/activar", {"correo": super_correo, "codigo": codigo_s, "clave": CLAVE_PRUEBA})
    informe.paso("Ella activa su cuenta con el código y elige su propia contraseña", estado == 200, f"estado {estado}")
    informe.paso("El mismo código no sirve una segunda vez",
                 api.pedir("POST", "/activar", {"correo": super_correo, "codigo": codigo_s, "clave": CLAVE_PRUEBA})[0] == 422)
    tok_s = sesion_s.get("token_acceso", "")
    informe.paso("Los administradores no usan /paquete (es solo para la app)", api.pedir("GET", "/paquete", token=tok_s)[0] == 403)

    estado, colegio_c = api.pedir("POST", "/admin/colegios", {"nombre": f"Colegio Prueba C {sufijo}"}, tok_s)
    informe.paso("La superadministradora crea un colegio por la API (201)", estado == 201, f"estado {estado}")
    id_c = colegio_c.get("id")
    admin_correo = f"admin.c.{sufijo}@prueba.local"
    estado, admin_c = api.pedir("POST", "/admin/usuarios", {"correo": admin_correo, "nombre": "Admin Colegio C",
                                                            "rol": "admin", "colegio_id": id_c}, tok_s)
    informe.paso("Ella crea al administrador de ese colegio (recibe un código, no una contraseña)",
                 estado == 201 and bool(admin_c.get("codigo")) and "clave" not in str(admin_c), f"estado {estado}")
    _, sesion_admin = api.pedir("POST", "/activar", {"correo": admin_correo, "codigo": admin_c.get("codigo", ""),
                                                     "clave": CLAVE_PRUEBA})
    tok_admin = sesion_admin.get("token_acceso", "")
    informe.paso("El administrador activa su cuenta y ve su colegio",
                 f"Prueba C {sufijo}" in str(sesion_admin) and bool(tok_admin))
    informe.paso("El administrador NO puede crear colegios (403)",
                 api.pedir("POST", "/admin/colegios", {"nombre": f"Intruso {sufijo}"}, tok_admin)[0] == 403)
    informe.paso("El administrador de C NO puede mirar el colegio A (403)",
                 api.pedir("GET", f"/admin/usuarios?colegio_id={colegio_a}", token=tok_admin)[0] == 403)
    doc_correo = f"doc.c.{sufijo}@prueba.local"
    estado, doc_c = api.pedir("POST", "/admin/usuarios", {"correo": doc_correo, "nombre": "Docente Colegio C",
                                                          "rol": "docente", "curso_nuevo": {"nombre": "6° C", "nivel": "6°"}},
                              tok_admin)
    informe.paso("El administrador crea a una docente con su curso (201)", estado == 201, f"estado {estado}")
    _, sesion_doc = api.pedir("POST", "/activar", {"correo": doc_correo, "codigo": doc_c.get("codigo", ""),
                                                   "clave": CLAVE_PRUEBA})
    tok_doc = sesion_doc.get("token_acceso", "")
    informe.paso("La docente activa su cuenta", bool(tok_doc))
    informe.paso("La docente NO puede usar las rutas de administración (403)",
                 api.pedir("GET", "/admin/usuarios", token=tok_doc)[0] == 403)
    curso_c = api.pedir("GET", "/paquete", token=tok_doc)[1].get("curso_ids", [None])[0]
    est_correo, apo_correo = f"est.c.{sufijo}@prueba.local", f"apo.c.{sufijo}@prueba.local"
    estado, est_c = api.pedir("POST", "/docente/estudiantes", {
        "correo": est_correo, "nombre": "Estudiante Colegio C", "curso_id": curso_c, "apoderado_correo": apo_correo,
        "apoderado_nombre": "Apoderado Colegio C"}, tok_doc)
    informe.paso("La docente agrega a un estudiante con su apoderado (201, dos códigos)",
                 estado == 201 and bool(est_c.get("codigo")) and bool(est_c.get("apoderado", {}).get("codigo")),
                 f"estado {estado}")
    informe.paso("La docente NO puede agregar estudiantes al curso de otro colegio (403)",
                 api.pedir("POST", "/docente/estudiantes", {"correo": f"x.{sufijo}@prueba.local", "nombre": "Intruso Uno",
                                                            "curso_id": curso_a}, tok_doc)[0] == 403)
    _, sesion_apo = api.pedir("POST", "/activar", {"correo": apo_correo, "codigo": est_c.get("apoderado", {}).get("codigo", ""),
                                                   "clave": CLAVE_PRUEBA})
    paquete_apo = api.pedir("GET", "/paquete", token=sesion_apo.get("token_acceso", ""))[1]
    informe.paso("El apoderado activa su cuenta y ve a su hijo/a", "Estudiante Colegio C" in str(paquete_apo))
    informe.paso("…y no ve nada de otros colegios", "Estudiante A" not in str(paquete_apo) and "Prueba A" not in str(paquete_apo))
    estado, _ = api.pedir("PATCH", f"/docente/estudiantes/{est_c['usuario']['id']}", {"activo": False}, tok_doc)
    paquete_doc = api.pedir("GET", "/paquete", token=tok_doc)[1]
    informe.paso("La baja de un estudiante lo saca de la lista de la docente (sin borrar nada)",
                 estado == 200 and "Estudiante Colegio C" not in str(paquete_doc))
    informe.paso("El estudiante dado de baja ya no puede ingresar",
                 api.ingresar(est_correo)[0] in (401, 403))
    estado, reinicio = api.pedir("POST", f"/admin/usuarios/{doc_c['usuario']['id']}/invitacion", token=tok_admin)
    informe.paso("El administrador reinicia el acceso de una docente: su contraseña anterior deja de servir",
                 estado == 200 and api.ingresar(doc_correo)[0] == 401)
    informe.paso("…y con el código nuevo recupera el acceso",
                 api.pedir("POST", "/activar", {"correo": doc_correo, "codigo": reinicio.get("codigo", ""),
                                                "clave": CLAVE_PRUEBA})[0] == 200)

    titulo("6. Tutor IA")
    chat = {"sistema": "Eres tutor de matemáticas.", "mensajes": [{"role": "user", "content": "¿Qué es una potencia?"}]}
    estado_ia = api.pedir("POST", "/ia/chat", chat, apo_a.get("token_acceso", ""))[0]
    informe.paso("El tutor IA responde 200 (con clave) o 503 (sin clave); nunca un error 500", estado_ia in (200, 503),
                 f"estado {estado_ia}")
    informe.info("IA con clave configurada." if estado_ia == 200 else "IA sin clave (TUTOR_IA_API_KEY vacío): es lo esperado en pruebas.")
    informe.paso("Un docente no puede usar el tutor IA (403)", api.pedir("POST", "/ia/chat", chat, token_a)[0] == 403)

    if not sin_docker and reiniciar:
        titulo("7. Los datos sobreviven a un reinicio")
        reinicio = subprocess.run([*COMPOSE, "restart", "api", "db"], cwd=RAIZ, capture_output=True, text=True,
                                  timeout=300)
        informe.paso("Se reiniciaron los contenedores", reinicio.returncode == 0, reinicio.stderr[-200:])
        informe.paso("La API vuelve a responder", api.esperar_salud())
        estado, datos = api.ingresar(correos["doc.a"])
        informe.paso("Las cuentas siguen existiendo después del reinicio", estado == 200)
        informe.paso("La sesión anterior sigue siendo válida (mismo secreto)",
                     api.pedir("GET", "/paquete", token=token_a)[0] == 200)
        informe.paso("El aviso publicado sigue guardado",
                     "Aviso de prueba" in str(api.pedir("GET", "/paquete", token=datos.get("token_acceso", ""))[1]))
    return resumen(informe)


def resumen(informe: Informe) -> int:
    print("\n" + "=" * 60)
    if informe.fallas:
        print(f"RESULTADO: {len(informe.fallas)} de {informe.total} comprobaciones FALLARON:")
        for falla in informe.fallas:
            print(f"   - {falla}")
        print("Pistas: docker compose logs api db  (muestra qué pasó dentro de los contenedores)")
        return 1
    print(f"RESULTADO: las {informe.total} comprobaciones pasaron. El despliegue funciona.")
    return 0


def main() -> int:
    for flujo in (sys.stdout, sys.stderr):      # que una consola con otra codificación no rompa los acentos
        try:
            flujo.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description="Prueba el despliegue de Tutor Educa (API + MySQL).")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="dirección de la API (por defecto, tu PC)")
    parser.add_argument("--sin-docker", action="store_true", help="no usar docker: correr las herramientas en este PC")
    parser.add_argument("--rapido", action="store_true", help="omitir la prueba de reinicio de contenedores")
    datos = parser.parse_args()
    return probar(datos.url, datos.sin_docker, reiniciar=not datos.rapido)


if __name__ == "__main__":
    sys.exit(main())

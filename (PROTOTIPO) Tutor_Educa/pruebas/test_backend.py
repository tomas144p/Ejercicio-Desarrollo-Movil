"""
Pruebas del backend (API). Ejecutar:  python -m unittest discover pruebas -v

Usan la base de demostración en una carpeta temporal y una IA falsa: no tocan datos reales ni gastan créditos.
Lo más importante que verifican: cada perfil solo ve y cambia lo suyo.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from fastapi.testclient import TestClient
    HAY_API = True
except ImportError:   # la app del celular no necesita FastAPI: estas pruebas se omiten si no está instalado
    HAY_API = False

if HAY_API:
    from backend.ajustes import Ajustes, AjustesInvalidos
    from backend.app import crear_app
    from backend.crear_usuario import ErrorAlta, crear_usuario
    from herramientas.generar_sql_mysql import generar
    from backend.crear_usuario import crear_usuario
    from backend.permisos import ErrorDatos, ErrorPermiso, validar_cambio
    from backend.seguridad_api import LimitadorVentana, ServicioTokens, TokenInvalido
    from models.contenido.datos_iniciales import DatosIniciales
    from models.modelos import FORMATO_FECHA
    from services.ia.proveedores import ErrorIA, ProveedorIA

CLAVE = DatosIniciales.CLAVE_DEMO
DOMINIO = DatosIniciales.DOMINIO


def ahora() -> str:
    return datetime.now().strftime(FORMATO_FECHA)


def correo(usuario: str) -> str:
    return f"{usuario}@{DOMINIO}"


if HAY_API:
    class IAFalsa(ProveedorIA):
        nombre = "IA falsa"

        def __init__(self):
            super().__init__("falso")
            self.llamadas = []

        def responder(self, sistema, mensajes):
            self.llamadas.append((sistema, mensajes))
            return "Respuesta de prueba."

    class IACaida(ProveedorIA):
        def responder(self, sistema, mensajes):
            raise ErrorIA("La IA tardó demasiado en responder.")


@unittest.skipUnless(HAY_API, "FastAPI no está instalado (pip install -r backend/requirements.txt)")
class BaseApi(unittest.TestCase):
    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp())
        self._sesiones: dict = {}
        self.ia = IAFalsa()
        self.ajustes = Ajustes(carpeta_datos=self.carpeta, ia_por_minuto=3, ia_cuota_diaria=5).validado()
        self.app = crear_app(self.ajustes, proveedor_ia=self.ia)
        self.cliente = TestClient(self.app)
        self.repo = self.app.state.gestor.servidor

    def tearDown(self):
        self.cliente.close()
        self.app.state.gestor.servidor.bd.cerrar()
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def ingresar(self, usuario: str, clave: str = CLAVE):
        return self.cliente.post("/login", json={"correo": correo(usuario), "clave": clave})

    def cabeceras(self, usuario: str) -> dict:
        if usuario not in self._sesiones:      # cada ingreso cuesta ~0,1 s (hash de contraseña): se reutiliza
            respuesta = self.ingresar(usuario)
            self.assertEqual(respuesta.status_code, 200, respuesta.text)
            self._sesiones[usuario] = {"Authorization": f"Bearer {respuesta.json()['token_acceso']}"}
        return self._sesiones[usuario]

    def cambio(self, usuario: str, tipo: str, datos: dict):
        return self.cliente.post("/cambios", json={"tipo": tipo, "datos": datos}, headers=self.cabeceras(usuario))

    def id_de(self, usuario: str) -> int:
        return int(self.repo.usuario_por_correo(correo(usuario))["id"])


class PruebasIngreso(BaseApi):
    def test_salud_no_pide_sesion(self):
        self.assertEqual(self.cliente.get("/salud").json()["estado"], "ok")

    def test_ingreso_correcto_devuelve_tokens_y_perfil(self):
        datos = self.ingresar("carolina.fuentes").json()
        self.assertEqual(datos["usuario"]["rol"], "docente")
        self.assertTrue(datos["token_acceso"] and datos["token_renovacion"])
        self.assertNotIn("clave_hash", str(datos))

    def test_contrasena_mala_y_correo_inexistente_dan_el_mismo_mensaje(self):
        mala = self.ingresar("carolina.fuentes", "otra-clave")
        inexistente = self.ingresar("no.existe")
        self.assertEqual((mala.status_code, inexistente.status_code), (401, 401))
        self.assertEqual(mala.json()["detail"], inexistente.json()["detail"])   # no se puede adivinar qué correos existen

    def test_bloqueo_tras_varios_intentos_fallidos(self):
        for _ in range(self.ajustes.login_max_fallos):
            self.assertEqual(self.ingresar("andres.morales", "mala").status_code, 401)
        bloqueado = self.ingresar("andres.morales", CLAVE)     # ni la clave correcta pasa mientras dura el bloqueo
        self.assertEqual(bloqueado.status_code, 429)
        self.assertIn("Retry-After", bloqueado.headers)
        self.assertEqual(self.ingresar("carolina.fuentes").status_code, 200)   # otras cuentas no se afectan

    def test_cuenta_desactivada_no_ingresa_ni_conserva_su_token(self):
        cabeceras = self.cabeceras("andres.morales")
        self.assertEqual(self.cliente.get("/paquete", headers=cabeceras).status_code, 200)
        self.repo.bd.ejecutar("UPDATE usuarios SET activo = 0 WHERE correo = ?", (correo("andres.morales"),))
        self.assertEqual(self.cliente.get("/paquete", headers=cabeceras).status_code, 401)   # el token deja de servir
        self.assertEqual(self.ingresar("andres.morales").status_code, 403)

    def test_renovar_sesion(self):
        datos = self.ingresar("sofia.morales").json()
        nuevo = self.cliente.post("/renovar", json={"token_renovacion": datos["token_renovacion"]})
        self.assertEqual(nuevo.status_code, 200)
        cabeceras = {"Authorization": f"Bearer {nuevo.json()['token_acceso']}"}
        self.assertEqual(self.cliente.get("/paquete", headers=cabeceras).status_code, 200)
        # un token de acceso NO sirve para renovar, ni uno de renovación para pedir datos
        self.assertEqual(self.cliente.post("/renovar", json={"token_renovacion": datos["token_acceso"]}).status_code, 401)
        cabeceras = {"Authorization": f"Bearer {datos['token_renovacion']}"}
        self.assertEqual(self.cliente.get("/paquete", headers=cabeceras).status_code, 401)


class PruebasPaquete(BaseApi):
    def test_sin_sesion_o_con_token_falso(self):
        self.assertEqual(self.cliente.get("/paquete").status_code, 401)
        malo = {"Authorization": "Bearer abc.def.ghi"}
        self.assertEqual(self.cliente.get("/paquete", headers=malo).status_code, 401)

    def test_apoderado_solo_ve_a_su_estudiante_y_nunca_contrasenas(self):
        respuesta = self.cliente.get("/paquete", headers=self.cabeceras("andres.morales"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn("clave_hash", respuesta.text)
        paquete = respuesta.json()
        self.assertEqual(paquete["estudiante_ids"], [self.id_de("sofia.morales")])
        self.assertNotIn(self.id_de("camila.perez"), [e["usuario_id"] for e in paquete["estudiantes"]])
        self.assertNotIn(self.id_de("camila.perez"), {c["estudiante_id"] for c in paquete["calificaciones"]})

    def test_docente_ve_su_curso(self):
        paquete = self.cliente.get("/paquete", headers=self.cabeceras("carolina.fuentes")).json()
        self.assertGreaterEqual(len(paquete["estudiante_ids"]), 2)

    def test_respuestas_sin_cache(self):
        self.assertEqual(self.cliente.get("/salud").headers["Cache-Control"], "no-store")


class PruebasCambios(BaseApi):
    def intento(self, estudiante_id, **extra):
        datos = {"codigo": "intento-prueba-0001", "estudiante_id": estudiante_id, "tema_id": "mat-potencias",
                 "correctas": 4, "total": 5, "porcentaje": 80, "nota": 5.5, "realizado_en": ahora(), "origen": "app"}
        datos.update(extra)
        return datos

    def test_estudiante_registra_su_intento_y_la_nota_se_recalcula(self):
        sofia = self.id_de("sofia.morales")
        # el celular "miente": dice nota 7,0 con 1 de 5 correctas
        r = self.cambio("sofia.morales", "intento", self.intento(sofia, correctas=1, nota=7.0, porcentaje=100))
        self.assertEqual(r.status_code, 200, r.text)
        fila = self.repo.bd.consultar_uno("SELECT * FROM intentos WHERE codigo = ?", ("intento-prueba-0001",))
        self.assertEqual((fila["correctas"], fila["porcentaje"]), (1, 20))
        self.assertLess(float(fila["nota"]), 3.0)

    def test_estudiante_no_registra_intentos_de_otro(self):
        r = self.cambio("sofia.morales", "intento", self.intento(self.id_de("camila.perez")))
        self.assertEqual(r.status_code, 403)

    def test_docente_y_apoderado_no_registran_intentos(self):
        sofia = self.id_de("sofia.morales")
        self.assertEqual(self.cambio("carolina.fuentes", "intento", self.intento(sofia)).status_code, 403)
        self.assertEqual(self.cambio("andres.morales", "intento", self.intento(sofia)).status_code, 403)

    def test_datos_mal_formados(self):
        sofia = self.id_de("sofia.morales")
        for malo in (self.intento(sofia, correctas=9), self.intento(sofia, tema_id="no-existe"),
                     self.intento(sofia, realizado_en="ayer"), self.intento(sofia, total="5"),
                     self.intento(sofia, codigo="x")):
            self.assertEqual(self.cambio("sofia.morales", "intento", malo).status_code, 422, malo)
        self.assertEqual(self.cambio("sofia.morales", "inventado", {}).status_code, 422)

    def test_docente_desbloquea_solo_a_sus_estudiantes(self):
        camila = self.id_de("camila.perez")
        datos = {"estudiante_id": camila, "tema_id": "mat-potencias", "activo": True, "mensaje": "A estudiar",
                 "docente_id": 999, "fecha": ahora()}     # docente_id falso: se ignora
        self.assertEqual(self.cambio("carolina.fuentes", "desbloqueo", datos).status_code, 200)
        fila = self.repo.bd.consultar_uno("SELECT * FROM refuerzos WHERE estudiante_id = ? AND tema_id = ?",
                                          (camila, "mat-potencias"))
        self.assertEqual(int(fila["desbloqueado_por"]), self.id_de("carolina.fuentes"))
        # otra docente, con otro curso, no puede tocar a Camila
        self._segunda_docente()
        self.assertEqual(self.cambio("otra.docente", "desbloqueo", datos).status_code, 403)

    def test_estudiante_y_apoderado_no_desbloquean_temas(self):
        datos = {"estudiante_id": self.id_de("sofia.morales"), "tema_id": "mat-potencias", "activo": True,
                 "fecha": ahora()}
        self.assertEqual(self.cambio("sofia.morales", "desbloqueo", datos).status_code, 403)
        self.assertEqual(self.cambio("andres.morales", "desbloqueo", datos).status_code, 403)

    def test_aviso_solo_del_curso_propio_y_autor_forzado(self):
        curso = int(self.repo.cursos_de_docente(self.id_de("carolina.fuentes"))[0].id)
        aviso = {"codigo": "aviso-prueba-0001", "curso_id": curso, "estudiante_id": None, "autor_id": 999,
                 "titulo": "Reunión", "cuerpo": "Habrá reunión el viernes.", "tipo": "info", "creado_en": ahora()}
        self.assertEqual(self.cambio("carolina.fuentes", "aviso", aviso).status_code, 200)
        fila = self.repo.aviso_por_codigo("aviso-prueba-0001")
        self.assertEqual(int(fila["autor_id"]), self.id_de("carolina.fuentes"))   # no 999
        self._segunda_docente()
        ajeno = dict(aviso, codigo="aviso-prueba-0002")
        self.assertEqual(self.cambio("otra.docente", "aviso", ajeno).status_code, 403)
        self.assertEqual(self.cambio("andres.morales", "aviso", ajeno).status_code, 403)
        self.assertEqual(self.cambio("carolina.fuentes", "aviso", dict(aviso, codigo="aviso-prueba-0003",
                                                                       tipo="spam")).status_code, 422)

    def test_confirmar_recibido_solo_avisos_propios(self):
        curso = int(self.repo.cursos_de_docente(self.id_de("carolina.fuentes"))[0].id)
        camila, sofia = self.id_de("camila.perez"), self.id_de("sofia.morales")
        base = {"curso_id": curso, "autor_id": 1, "titulo": "Hola", "cuerpo": "Mensaje de prueba", "tipo": "info",
                "creado_en": ahora()}
        self.cambio("carolina.fuentes", "aviso", dict(base, codigo="aviso-para-camila", estudiante_id=camila))
        self.cambio("carolina.fuentes", "aviso", dict(base, codigo="aviso-para-todos", estudiante_id=None))
        # Andrés (apoderado de Sofía) NO puede confirmar un aviso dirigido a Camila
        r = self.cambio("andres.morales", "aviso_leido", {"aviso_codigo": "aviso-para-camila", "fecha": ahora()})
        self.assertEqual(r.status_code, 403)
        # sí el de todo el curso, y el celular no puede decir que lo leyó otra persona
        r = self.cambio("andres.morales", "aviso_leido", {"aviso_codigo": "aviso-para-todos", "usuario_id": 999,
                                                          "fecha": ahora()})
        self.assertEqual(r.status_code, 200, r.text)
        aviso = self.repo.aviso_por_codigo("aviso-para-todos")
        lecturas = self.repo.lecturas([int(aviso["id"])])
        self.assertEqual([int(x["usuario_id"]) for x in lecturas], [self.id_de("andres.morales")])
        # el docente no confirma avisos
        r = self.cambio("carolina.fuentes", "aviso_leido", {"aviso_codigo": "aviso-para-todos", "fecha": ahora()})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(sofia, self.id_de("sofia.morales"))

    def _segunda_docente(self):
        """Crea otra docente con su propio curso (para probar que no puede tocar el curso de Carolina)."""
        from services.seguridad import GestorClaves
        bd = self.repo.bd
        nuevo_id = int(bd.valor("SELECT MAX(id) FROM usuarios", defecto=0)) + 1
        bd.insertar("usuarios", {"id": nuevo_id, "correo": correo("otra.docente"), "nombre": "Otra Docente",
                                 "rol": "docente", "clave_hash": GestorClaves.generar_hash(CLAVE), "activo": 1,
                                 "creado_en": ahora()})
        bd.insertar("cursos", {"nombre": "8° Básico A", "nivel": "8° Básico", "docente_id": nuevo_id, "anio": 2026})
        self._sesiones.pop("otra.docente", None)


class PruebasIA(BaseApi):
    CUERPO = {"sistema": "Eres tutor de matemáticas.", "mensajes": [{"role": "user", "content": "¿Qué es una potencia?"}]}

    def post(self, usuario, cuerpo=None):
        return self.cliente.post("/ia/chat", json=cuerpo or self.CUERPO, headers=self.cabeceras(usuario))

    def test_necesita_sesion(self):
        self.assertEqual(self.cliente.post("/ia/chat", json=self.CUERPO).status_code, 401)

    def test_responde_y_agrega_reglas_del_servidor(self):
        r = self.post("sofia.morales")
        self.assertEqual((r.status_code, r.json()["texto"]), (200, "Respuesta de prueba."))
        self.assertIn("Tutor Educa", self.ia.llamadas[0][0])
        self.assertIn("Eres tutor de matemáticas.", self.ia.llamadas[0][0])

    def test_docente_no_usa_el_tutor(self):
        self.assertEqual(self.post("carolina.fuentes").status_code, 403)

    def test_limite_por_minuto(self):
        for _ in range(3):
            self.assertEqual(self.post("andres.morales").status_code, 200)
        r = self.post("andres.morales")
        self.assertEqual(r.status_code, 429)
        self.assertIn("Retry-After", r.headers)

    def test_historial_invalido(self):
        malo = {"sistema": "x", "mensajes": [{"role": "assistant", "content": "hola"}]}
        self.assertEqual(self.post("sofia.morales", malo).status_code, 422)

    def test_sin_clave_de_ia_responde_503_y_si_la_ia_falla_502(self):
        self.app.state.ia.proveedor = None
        self.assertEqual(self.post("sofia.morales").status_code, 503)
        self.app.state.ia.proveedor = IACaida("x")
        self.assertEqual(self.post("sofia.morales").status_code, 502)


class PruebasAltaDeCuentas(BaseApi):
    def test_alta_de_docente_con_curso_estudiante_y_apoderado(self):
        repo = self.repo
        crear_usuario(repo, "nuevo.docente@colegio.cl", "Nuevo Docente", "docente", "clave-segura-123",
                      curso="5° Básico A", nivel="5° Básico")
        curso_id = int(repo.cursos_de_docente(self.id_de_correo("nuevo.docente@colegio.cl"))[0].id)
        crear_usuario(repo, "pap@correo.cl", "Papá Nuevo", "apoderado", "clave-segura-123")
        crear_usuario(repo, "alumno@colegio.cl", "Alumno Nuevo", "estudiante", "clave-segura-123",
                      curso_id=curso_id, apoderado="pap@correo.cl")
        # la cuenta nueva ingresa por la API y el apoderado ve a su hijo
        r = self.cliente.post("/login", json={"correo": "pap@correo.cl", "clave": "clave-segura-123"})
        self.assertEqual(r.status_code, 200, r.text)
        cabeceras = {"Authorization": f"Bearer {r.json()['token_acceso']}"}
        paquete = self.cliente.get("/paquete", headers=cabeceras).json()
        self.assertEqual([e["usuario_id"] for e in paquete["estudiantes"]], [self.id_de_correo("alumno@colegio.cl")])

    def test_rechaza_datos_invalidos(self):
        malos = [("a@b.cl", "Ana Pérez", "docente", "corta1"),                  # contraseña corta
                 ("a@b.cl", "Ana Pérez", "docente", "sololetrasaqui"),           # sin números
                 ("a@b.cl", "Ana Pérez", "director", "clave-segura-123"),        # perfil inexistente
                 ("no-es-correo", "Ana Pérez", "docente", "clave-segura-123"),
                 (correo("sofia.morales"), "Otra Sofía", "docente", "clave-segura-123"),   # correo repetido
                 ("al@b.cl", "Alumno", "estudiante", "clave-segura-123")]        # estudiante sin curso
        for caso in malos:
            with self.assertRaises(ValueError, msg=caso):
                crear_usuario(self.repo, *caso)
        antes = self.repo.bd.valor("SELECT COUNT(*) FROM usuarios")
        with self.assertRaises(ValueError):       # el apoderado indicado no existe: no debe quedar nada a medias
            crear_usuario(self.repo, "al@b.cl", "Alumno Nuevo", "estudiante", "clave-segura-123", curso_id=1,
                          apoderado="fantasma@correo.cl")
        self.assertEqual(self.repo.bd.valor("SELECT COUNT(*) FROM usuarios"), antes)

    def id_de_correo(self, c: str) -> int:
        return int(self.repo.usuario_por_correo(c)["id"])


class PruebasAltaDeCuentas(BaseApi):
    CLAVE_NUEVA = "Clave-larga-2026"

    def test_docente_con_curso_y_luego_estudiante_con_apoderado_pueden_ingresar(self):
        docente = crear_usuario(self.repo, "nueva.docente@colegio.cl", "Nueva Docente", "docente", self.CLAVE_NUEVA,
                                curso_nuevo=("5° Básico A", "5° Básico"))
        curso = self.repo.cursos_de_docente(docente)[0]
        apoderado = crear_usuario(self.repo, "apoderado.nuevo@correo.cl", "Apoderado Nuevo", "apoderado",
                                  self.CLAVE_NUEVA)
        estudiante = crear_usuario(self.repo, "estudiante.nuevo@correo.cl", "Estudiante Nuevo", "estudiante",
                                   self.CLAVE_NUEVA, curso_id=int(curso.id), apoderado_correo="apoderado.nuevo@correo.cl")
        r = self.cliente.post("/login", json={"correo": "apoderado.nuevo@correo.cl", "clave": self.CLAVE_NUEVA})
        self.assertEqual(r.status_code, 200)
        cabeceras = {"Authorization": f"Bearer {r.json()['token_acceso']}"}
        paquete = self.cliente.get("/paquete", headers=cabeceras).json()
        self.assertEqual(paquete["estudiante_ids"], [estudiante])
        self.assertEqual((docente > 0, apoderado > 0), (True, True))

    def test_rechaza_cuentas_mal_formadas(self):
        casos = [
            dict(correo="sin-arroba", nombre="Nombre Ok", rol="docente", clave=self.CLAVE_NUEVA),
            dict(correo="a@b.cl", nombre="N", rol="docente", clave=self.CLAVE_NUEVA),
            dict(correo="a@b.cl", nombre="Nombre Ok", rol="director", clave=self.CLAVE_NUEVA),
            dict(correo="a@b.cl", nombre="Nombre Ok", rol="docente", clave="corta1"),
            dict(correo="a@b.cl", nombre="Nombre Ok", rol="docente", clave="12345678901234"),
            dict(correo=correo("sofia.morales"), nombre="Repetida", rol="docente", clave=self.CLAVE_NUEVA),
            dict(correo="e@b.cl", nombre="Sin Curso", rol="estudiante", clave=self.CLAVE_NUEVA),
            dict(correo="e@b.cl", nombre="Curso Falso", rol="estudiante", clave=self.CLAVE_NUEVA, curso_id=999),
            dict(correo="e@b.cl", nombre="Apod Falso", rol="estudiante", clave=self.CLAVE_NUEVA, curso_id=1,
                 apoderado_correo=correo("carolina.fuentes")),     # ese correo es de una docente, no de un apoderado
            dict(correo="a@b.cl", nombre="Nombre Ok", rol="apoderado", clave=self.CLAVE_NUEVA, curso_nuevo=("X", "Y")),
        ]
        for caso in casos:
            with self.assertRaises(ErrorAlta, msg=caso):
                crear_usuario(self.repo, **caso)
        self.assertIsNone(self.repo.usuario_por_correo("a@b.cl"))      # nada quedó a medias


class PruebasSqlDeProduccion(unittest.TestCase):
    @unittest.skipUnless(HAY_API, "FastAPI no está instalado")
    def test_produccion_no_trae_cuentas_ni_borra_tablas(self):
        produccion, demo = generar(produccion=True), generar()
        self.assertNotIn(DatosIniciales.CLAVE_DEMO, produccion)
        self.assertNotIn("INSERT INTO usuarios", produccion)
        self.assertNotIn("DROP TABLE", produccion)
        self.assertIn("INSERT IGNORE INTO temas", produccion)
        self.assertIn("CREATE TABLE IF NOT EXISTS usuarios", produccion)
        self.assertIn("INSERT INTO usuarios", demo)                    # la versión de demostración no cambió
        self.assertIn("DROP TABLE", demo)


@unittest.skipUnless(HAY_API, "FastAPI no está instalado")
class PruebasPiezas(unittest.TestCase):
    def test_tokens_vencen_y_no_se_pueden_alterar(self):
        reloj = [1_000_000.0]
        servicio = ServicioTokens("secreto-de-prueba-muy-largo-123456", 30, 30, reloj=lambda: reloj[0])
        token = servicio.crear_acceso(7, "docente")
        self.assertEqual(servicio.leer(token, "acceso")["usuario_id"], 7)
        with self.assertRaises(TokenInvalido):
            servicio.leer(token, "renovacion")
        with self.assertRaises(TokenInvalido):
            servicio.leer(token[:-3] + "abc", "acceso")
        reloj[0] += 31 * 60
        with self.assertRaises(TokenInvalido):
            servicio.leer(token, "acceso")
        otro = ServicioTokens("otro-secreto-muy-largo-1234567890", 30, 30, reloj=lambda: 1_000_000.0)
        with self.assertRaises(TokenInvalido):
            otro.leer(servicio.crear_acceso(7, "docente"), "acceso")

    def test_limitador_de_ventana(self):
        reloj = [0.0]
        limite = LimitadorVentana(2, 60, reloj=lambda: reloj[0])
        self.assertEqual(limite.intentar("a"), 0)
        self.assertEqual(limite.intentar("a"), 0)
        self.assertGreater(limite.intentar("a"), 0)
        self.assertEqual(limite.intentar("b"), 0)       # cada clave tiene su propio cupo
        reloj[0] = 61
        self.assertEqual(limite.intentar("a"), 0)

    def test_ajustes_de_produccion_exigen_configuracion_segura(self):
        with self.assertRaises(AjustesInvalidos):
            Ajustes.desde_entorno({"TUTOR_ENTORNO": "produccion"})
        base = {"TUTOR_ENTORNO": "produccion", "TUTOR_JWT_SECRETO": "x" * 40, "TUTOR_DB_CLAVE": "clave-larga"}
        self.assertTrue(Ajustes.desde_entorno(base).es_produccion)
        with self.assertRaises(AjustesInvalidos):
            Ajustes.desde_entorno({**base, "TUTOR_JWT_SECRETO": "corto"})
        with self.assertRaises(AjustesInvalidos):
            Ajustes.desde_entorno({**base, "TUTOR_DB_USUARIO": "root"})
        with self.assertRaises(AjustesInvalidos):
            Ajustes.desde_entorno({**base, "TUTOR_DB_MOTOR": "demo"})
        self.assertFalse(Ajustes.desde_entorno({}).es_produccion)   # desarrollo funciona sin configurar nada


if __name__ == "__main__":
    unittest.main()

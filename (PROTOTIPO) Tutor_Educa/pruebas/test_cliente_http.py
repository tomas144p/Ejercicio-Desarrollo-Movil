"""
Pruebas de punta a punta: la app (cliente HTTP, autenticación, sincronización, IA) contra un backend real que
se levanta en un hilo, con la base de demostración y una IA falsa.

Comprueban lo que de verdad importa para el piloto: la app funciona SIN claves de base de datos, cada persona solo
envía lo suyo, y el modo sin conexión sigue funcionando.
"""

from __future__ import annotations

import shutil
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import uvicorn
    HAY_API = True
except ImportError:
    HAY_API = False

if HAY_API:
    from backend.ajustes import Ajustes
    from backend.app import crear_app
    from models.contenido.datos_iniciales import DatosIniciales
    from models.datos.conexiones import ErrorConexion
    from models.datos.local import BaseDatosLocal
    from models.datos.servidor import GestorServidor
    from models.datos.servidor_http import ErrorCambio, ErrorSesion, ServidorHTTP, validar_url
    from models.modelos import EstadoRefuerzo, Intento
    from services.autenticacion import ServicioAutenticacion
    from services.configuracion import ConfigServidor
    from services.datos_app import ServicioDatos
    from services.gestion_docente import ServicioGestion, mensaje_invitacion
    from services.ia.proveedor_servidor import ProveedorServidor
    from services.ia.proveedores import ErrorIA, ProveedorIA
    from services.sincronizacion import ServicioSincronizacion

CLAVE = DatosIniciales.CLAVE_DEMO


def secrets_hex() -> str:
    import secrets
    return secrets.token_hex(3)


def correo(usuario: str) -> str:
    return f"{usuario}@{DatosIniciales.DOMINIO}"


class MonitorFalso:
    forzado_sin_conexion = False


if HAY_API:
    class IAFalsa(ProveedorIA):
        nombre = "IA falsa"

        def responder(self, sistema, mensajes):
            return "Respuesta de prueba."


class _ServidorEnVivo:
    """Levanta un backend real (en un hilo) con su propia base de datos, y la app conectada a él."""

    @classmethod
    def setUpClass(cls):
        cls.carpeta_servidor = Path(tempfile.mkdtemp())
        ajustes = Ajustes(carpeta_datos=cls.carpeta_servidor).validado()
        cls.app = crear_app(ajustes, proveedor_ia=IAFalsa("falso"))
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            puerto = s.getsockname()[1]
        cls.url = f"http://127.0.0.1:{puerto}"
        cls.servidor = uvicorn.Server(uvicorn.Config(cls.app, host="127.0.0.1", port=puerto, log_level="error"))
        cls.hilo = threading.Thread(target=cls.servidor.run, daemon=True)
        cls.hilo.start()
        for _ in range(100):
            if cls.servidor.started:
                break
            time.sleep(0.05)
        else:
            raise RuntimeError("El servidor de pruebas no arrancó.")

    @classmethod
    def tearDownClass(cls):
        cls.servidor.should_exit = True
        cls.hilo.join(timeout=5)
        cls.app.state.gestor.servidor.bd.cerrar()
        shutil.rmtree(cls.carpeta_servidor, ignore_errors=True)

    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp())
        self.gestor = GestorServidor(ConfigServidor(motor="http", url=self.url), self.carpeta).inicializar()
        self.local = BaseDatosLocal(self.carpeta / "local.db")
        self.sinc = ServicioSincronizacion(self.local, self.gestor)
        self.monitor = MonitorFalso()
        self.auth = ServicioAutenticacion(self.local, self.gestor, self.sinc, self.monitor)
        self.gestion = ServicioGestion(self.gestor, self.sinc, self.monitor, self.local)
        self.datos = ServicioDatos(self.local)

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)


@unittest.skipUnless(HAY_API, "uvicorn/FastAPI no están instalados (pip install -r backend/requirements.txt)")
class PruebasClienteHTTP(_ServidorEnVivo, unittest.TestCase):
    # ------------------------------------------------------------------
    def test_la_app_no_necesita_claves_de_base_de_datos(self):
        self.assertTrue(self.gestor.usa_backend)
        self.assertIsInstance(self.gestor.servidor, ServidorHTTP)
        self.assertFalse(hasattr(self.gestor.servidor, "bd"))      # no hay conexión directa a ninguna base
        self.assertTrue(self.gestor.servidor.probar())

    def test_url_solo_https_salvo_red_local(self):
        self.assertEqual(validar_url("https://api.colegio.cl/"), "https://api.colegio.cl")
        for permitida in ("http://127.0.0.1:8000", "http://localhost:8000", "http://10.0.2.2:8000",
                          "http://192.168.1.20:8000"):
            validar_url(permitida)
        for mala in ("http://api.colegio.cl", "ftp://api.colegio.cl", "api.colegio.cl", "", "https://"):
            with self.assertRaises(ValueError, msg=mala):
                validar_url(mala)
        mal_configurado = GestorServidor(ConfigServidor(motor="http", url="http://api.colegio.cl"),
                                         self.carpeta).inicializar()
        self.assertIsNone(mal_configurado.servidor)
        self.assertFalse(mal_configurado.disponible())
        self.assertIn("https://", mal_configurado.diagnostico)

    def test_ingreso_y_descarga_de_datos(self):
        resultado = self.auth.ingresar(correo("andres.morales"), CLAVE)
        self.assertTrue(resultado.exito and resultado.en_linea, resultado.mensaje)
        self.datos.iniciar_sesion(resultado.usuario)
        hijos = self.datos.hijos()
        self.assertEqual([h.estudiante.nombre for h in hijos], ["Sofía Morales"])
        self.assertEqual([c["nombre"] for c in self.local.colegios()], ["Colegio Demo"])    # el colegio llegó al teléfono
        self.assertEqual(resultado.usuario.colegio_id, 1)
        # lo que quedó en el teléfono no incluye la huella de ninguna contraseña ajena
        huellas = self.local.bd.consultar("SELECT * FROM usuarios")
        self.assertTrue(all("clave_hash" not in f or not f["clave_hash"] for f in huellas))

    def test_los_administradores_no_ingresan_a_la_app(self):
        from services.seguridad import GestorClaves
        repo = self.app.state.gestor.servidor
        repo.bd.insertar("usuarios", {"correo": correo("admin.app"), "nombre": "Admin App", "rol": "admin",
                                      "clave_hash": GestorClaves.generar_hash(CLAVE), "activo": 1, "colegio_id": 1})
        resultado = self.auth.ingresar(correo("admin.app"), CLAVE)
        self.assertFalse(resultado.exito)
        self.assertIn("panel web", resultado.mensaje)
        self.assertEqual(self.local.cantidad_pendientes(), 0)         # nada se descargó ni quedó guardado en el teléfono

    def test_ingreso_fallido_mensajes(self):
        mala = self.auth.ingresar(correo("andres.morales"), "otra")
        self.assertEqual((mala.exito, mala.en_linea, mala.mensaje), (False, True, "Correo o contraseña incorrectos."))
        inexistente = self.auth.ingresar(correo("fantasma"), "otra")
        self.assertEqual(inexistente.mensaje, "Correo o contraseña incorrectos.")

    def test_intento_viaja_al_servidor_y_no_se_duplica(self):
        sofia = self.auth.ingresar(correo("sofia.morales"), CLAVE).usuario
        self.datos.iniciar_sesion(sofia)
        self.assertTrue(self.datos.registrar_intento(Intento.nuevo(sofia.id, "mat-ecuaciones", 5, 5)))
        self.assertEqual(self.local.cantidad_pendientes(), 2)
        resultado = self.sinc.sincronizar(sofia)
        self.assertEqual((resultado.enviados, resultado.fallidos, resultado.descargado), (2, 0, True))
        self.assertEqual(self.local.cantidad_pendientes(), 0)
        servidor = self.app.state.gestor.servidor
        estados = {r.tema_id: r.estado for r in servidor.refuerzos([sofia.id])}
        self.assertEqual(estados["mat-ecuaciones"], EstadoRefuerzo.LOGRADO)
        antes = len(servidor.intentos([sofia.id]))
        self.sinc.sincronizar(sofia)
        self.assertEqual(len(servidor.intentos([sofia.id])), antes)

    def test_los_cambios_de_otra_persona_esperan_su_turno(self):
        """Dos personas comparten el teléfono: lo de Sofía no se envía con la sesión de su apoderado."""
        sofia = self.auth.ingresar(correo("sofia.morales"), CLAVE).usuario
        self.datos.iniciar_sesion(sofia)
        self.datos.registrar_intento(Intento.nuevo(sofia.id, "mat-ecuaciones", 5, 5, origen="app"))
        pendientes = self.local.cantidad_pendientes()
        self.gestor.cerrar_sesion()
        andres = self.auth.ingresar(correo("andres.morales"), CLAVE).usuario
        resultado = self.sinc.sincronizar(andres)
        self.assertEqual((resultado.enviados, resultado.fallidos), (0, 0))
        self.assertEqual(self.local.cantidad_pendientes(), pendientes)     # nada se perdió ni se descartó
        self.gestor.cerrar_sesion()
        sofia = self.auth.ingresar(correo("sofia.morales"), CLAVE).usuario
        self.assertEqual(self.local.cantidad_pendientes(), 0)              # al ingresar Sofía, se enviaron sus cambios

    def test_sin_conexion_y_regreso(self):
        self.auth.ingresar(correo("sofia.morales"), CLAVE, recordar=True)
        self.monitor.forzado_sin_conexion = True
        sofia = self.auth.ingresar(correo("sofia.morales"), CLAVE).usuario
        self.assertTrue(self.gestor.servidor.sesion_activa)                # retomó su sesión guardada
        self.datos.iniciar_sesion(sofia)
        self.datos.registrar_intento(Intento.nuevo(sofia.id, "mat-ecuaciones", 4, 5))
        self.monitor.forzado_sin_conexion = False                          # vuelve la conexión
        resultado = self.sinc.sincronizar(sofia)
        self.assertGreaterEqual(resultado.enviados, 1)
        self.assertEqual(self.local.cantidad_pendientes(), 0)

    def test_otra_persona_sin_sesion_guardada_no_hereda_la_anterior(self):
        self.auth.ingresar(correo("sofia.morales"), CLAVE, recordar=True)
        self.auth.ingresar(correo("andres.morales"), CLAVE, recordar=False)   # no guarda sesión
        self.gestor.cerrar_sesion()
        self.monitor.forzado_sin_conexion = True
        self.auth.ingresar(correo("andres.morales"), CLAVE)                  # sin credencial: no entra
        self.assertFalse(self.gestor.servidor.sesion_activa)

    def test_token_vencido_se_renueva_solo_y_sesion_perdida_avisa(self):
        servidor = self.gestor.servidor
        servidor.verificar_ingreso(correo("sofia.morales"), CLAVE)
        servidor._vence = 0.0                                              # el token de acceso "venció"
        self.assertTrue(servidor.paquete_para(None).estudiante_ids)       # se renovó sin molestar a nadie
        servidor._acceso, servidor._vence = "", 0.0
        servidor.token_renovacion = "token-roto-token-roto"
        with self.assertRaises(ErrorSesion):
            servidor.paquete_para(None)
        self.assertIsInstance(ErrorSesion("x"), ErrorConexion)            # la cola de cambios se conserva
        self.assertFalse(servidor.sesion_activa)

    def test_cambio_rechazado_no_se_reintenta_como_si_fuera_red(self):
        servidor = self.gestor.servidor
        servidor.verificar_ingreso(correo("andres.morales"), CLAVE)
        with self.assertRaises(ErrorCambio):
            servidor.aplicar_cambio("desbloqueo", {"estudiante_id": 3, "tema_id": "mat-potencias", "activo": True,
                                                   "fecha": "2026-01-01 10:00:00"})

    def test_ia_pasa_por_el_servidor(self):
        self.auth.ingresar(correo("sofia.morales"), CLAVE)
        proveedor = ProveedorServidor(self.gestor)
        self.assertEqual(proveedor.responder("Eres tutor.", [{"role": "user", "content": "Hola"}]),
                         "Respuesta de prueba.")
        self.app.state.ia.proveedor = None                                  # el servidor no tiene IA configurada
        try:
            with self.assertRaises(ErrorIA):
                proveedor.responder("Eres tutor.", [{"role": "user", "content": "Hola"}])
        finally:
            self.app.state.ia.proveedor = IAFalsa("falso")

    def test_servidor_caido(self):
        malo = GestorServidor(ConfigServidor(motor="http", url="http://127.0.0.1:1", tiempo_http=1),
                              self.carpeta).inicializar()
        self.assertFalse(malo.disponible())
        sinc = ServicioSincronizacion(self.local, malo)
        self.assertTrue(sinc.sincronizar(None).sin_conexion)
        auth = ServicioAutenticacion(self.local, malo, sinc, self.monitor)
        self.assertFalse(auth.ingresar(correo("sofia.morales"), CLAVE).exito)   # nunca había ingresado: pide conexión


@unittest.skipUnless(HAY_API, "uvicorn/FastAPI no están instalados (pip install -r backend/requirements.txt)")
class PruebasGestionDesdeLaApp(_ServidorEnVivo, unittest.TestCase):
    """La docente gestiona a sus estudiantes y las familias activan sus cuentas, todo desde la app.

    Tiene su propio servidor porque estas pruebas CAMBIAN datos (agregan estudiantes, dan de baja...)."""

    # ------------------------------------------------------------------ gestión de estudiantes y activación
    def docente(self):
        return self.auth.ingresar(correo("carolina.fuentes"), CLAVE).usuario

    def curso(self, docente) -> int:
        return int(self.datos_de(docente).cursos_docente()[0].id)

    def datos_de(self, usuario):
        self.datos.iniciar_sesion(usuario)
        return self.datos

    def test_la_docente_agrega_un_estudiante_y_la_familia_activa_sus_cuentas_desde_la_app(self):
        docente = self.docente()
        sufijo = secrets_hex()
        est, apo = f"luis.{sufijo}@correo.cl", f"rosa.{sufijo}@correo.cl"
        r = self.gestion.agregar_estudiante(docente, self.curso(docente), "  Luis   Pérez ", est, apo, "Rosa Pérez")
        self.assertTrue(r.exito, r.mensaje)
        self.assertEqual([c.rol for c in r.codigos], ["estudiante", "apoderado"])
        self.assertIn(r.codigos[0].codigo, r.codigos[0].mensaje)                  # el texto listo para enviar trae el código
        self.assertIn(est, r.codigos[0].mensaje)
        self.assertIn("Colegio Demo", r.codigos[0].mensaje)
        self.assertIn("Luis Pérez", [f.estudiante.nombre for f in self.datos.fichas_curso(self.curso(docente))])   # ya está en su lista

        self.gestor.cerrar_sesion()
        malo = self.auth.activar_cuenta(apo, "ZZZZZ-ZZZZZ", "Clave-larga-2026")
        self.assertFalse(malo.exito)
        self.assertIn("código", malo.mensaje)
        entra = self.auth.activar_cuenta(apo, r.codigos[1].codigo.lower(), "Clave-larga-2026")
        self.assertTrue(entra.exito, entra.mensaje)
        self.assertEqual(entra.usuario.rol, "apoderado")
        self.assertEqual([h.estudiante.nombre for h in self.datos_de(entra.usuario).hijos()], ["Luis Pérez"])
        self.assertEqual(self.auth.ingresar(apo, "Clave-larga-2026").exito, True)   # y puede volver a entrar con su contraseña
        reuso = self.auth.activar_cuenta(apo, r.codigos[1].codigo, "Otra-clave-larga-1")
        self.assertFalse(reuso.exito)                                               # el código no sirve dos veces

    def test_apoderado_existente_solo_se_vincula(self):
        docente = self.docente()
        r = self.gestion.agregar_estudiante(docente, self.curso(docente), "Pedro Pérez", f"pedro.{secrets_hex()}@correo.cl",
                                            correo("andres.morales"))
        self.assertTrue(r.exito, r.mensaje)
        self.assertEqual([c.rol for c in r.codigos], ["estudiante"])                # a Andrés no se le toca la contraseña
        self.assertEqual(r.apoderado_existente, "Andrés Morales")

    def test_mensajes_claros_cuando_algo_falla(self):
        docente = self.docente()
        curso = self.curso(docente)
        self.assertIn("correo", self.gestion.agregar_estudiante(docente, curso, "Ana Díaz", "no-es-correo").mensaje.lower())
        self.assertIn("nombre", self.gestion.agregar_estudiante(docente, curso, "A", "a@b.cl").mensaje.lower())
        sin_nombre = self.gestion.agregar_estudiante(docente, curso, "Ana Díaz", f"ana.{secrets_hex()}@b.cl",
                                                     f"mama.{secrets_hex()}@b.cl")
        self.assertFalse(sin_nombre.exito)
        self.assertIn("nombre", sin_nombre.mensaje)                                  # el apoderado nuevo necesita nombre
        otro_curso = self.gestion.agregar_estudiante(docente, 99999, "Ana Díaz", f"ana.{secrets_hex()}@b.cl")
        self.assertFalse(otro_curso.exito)
        self.monitor.forzado_sin_conexion = True
        sin_red = self.gestion.agregar_estudiante(docente, curso, "Ana Díaz", f"ana.{secrets_hex()}@b.cl")
        self.assertFalse(sin_red.exito)
        self.assertIn("conexión", sin_red.mensaje)
        self.assertEqual(self.local.cantidad_pendientes(), 0)                        # no se encola: las cuentas las crea el servidor

    def test_baja_reactivar_y_lista_de_bajas(self):
        docente = self.docente()
        sofia = [f for f in self.datos.fichas_curso(self.curso(docente)) if f.estudiante.nombre == "Sofía Morales"][0]
        r = self.gestion.dar_de_baja(docente, sofia.estudiante.id)
        self.assertTrue(r.exito, r.mensaje)
        self.assertNotIn("Sofía Morales", [f.estudiante.nombre for f in self.datos.fichas_curso(self.curso(docente))])
        bajas = self.gestion.dados_de_baja(docente)
        self.assertEqual([b["nombre"] for b in bajas.datos], ["Sofía Morales"])
        self.assertTrue(self.gestion.reactivar(docente, sofia.estudiante.id).exito)
        self.assertEqual(self.gestion.dados_de_baja(docente).datos, [])
        self.assertIn("Sofía Morales", [f.estudiante.nombre for f in self.datos.fichas_curso(self.curso(docente))])

    def test_codigo_nuevo_para_quien_olvido_su_contrasena(self):
        docente = self.docente()
        id_andres = int(self.app.state.gestor.servidor.usuario_por_correo(correo("andres.morales"))["id"])
        andres = self.gestion.codigo_nuevo(docente, id_andres, "apoderado")
        self.assertTrue(andres.exito, andres.mensaje)
        self.assertEqual(self.auth.ingresar(correo("andres.morales"), CLAVE).exito, False)   # la anterior ya no sirve
        self.gestor.cerrar_sesion()
        self.assertTrue(self.auth.activar_cuenta(correo("andres.morales"), andres.codigos[0].codigo, "Clave-larga-2026").exito)

    def test_sin_servidor_del_colegio_se_explica_que_falta_configurarlo(self):
        (self.carpeta / "demo").mkdir()
        demo = GestorServidor(ConfigServidor(motor="demo"), self.carpeta / "demo").inicializar()
        gestion = ServicioGestion(demo, ServicioSincronizacion(self.local, demo), self.monitor, self.local)
        self.assertFalse(gestion.disponible)
        r = gestion.agregar_estudiante(type("U", (), {"nombre": "X", "colegio_id": 1})(), 1, "Ana Díaz", "ana@b.cl")
        self.assertFalse(r.exito)
        self.assertIn("servidor del colegio", r.mensaje)
        auth = ServicioAutenticacion(self.local, demo, ServicioSincronizacion(self.local, demo), self.monitor)
        self.assertIn("servidor del colegio", auth.activar_cuenta("ana@b.cl", "ABCDE-FGHJK", "Clave-larga-2026").mensaje)

    def test_el_texto_para_enviar_a_la_familia(self):
        texto = mensaje_invitacion("Rosa Pérez", "rosa@correo.cl", "ABCDE-FGHJK", "2026-11-15 10:00:00",
                                   "Colegio San Andrés", "Carolina Fuentes")
        for esperado in ("Hola Rosa", "Carolina Fuentes", "Colegio San Andrés", "rosa@correo.cl", "ABCDE-FGHJK",
                         "15-11-2026", "una sola vez", "Tengo un código"):
            self.assertIn(esperado, texto)


if __name__ == "__main__":
    unittest.main()

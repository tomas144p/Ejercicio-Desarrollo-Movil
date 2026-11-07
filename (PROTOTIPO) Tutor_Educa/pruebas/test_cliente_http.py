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
    from services.ia.proveedor_servidor import ProveedorServidor
    from services.ia.proveedores import ErrorIA, ProveedorIA
    from services.sincronizacion import ServicioSincronizacion

CLAVE = DatosIniciales.CLAVE_DEMO


def correo(usuario: str) -> str:
    return f"{usuario}@{DatosIniciales.DOMINIO}"


class MonitorFalso:
    forzado_sin_conexion = False


if HAY_API:
    class IAFalsa(ProveedorIA):
        nombre = "IA falsa"

        def responder(self, sistema, mensajes):
            return "Respuesta de prueba."


@unittest.skipUnless(HAY_API, "uvicorn/FastAPI no están instalados (pip install -r backend/requirements.txt)")
class PruebasClienteHTTP(unittest.TestCase):
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
        self.datos = ServicioDatos(self.local)

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

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
        # lo que quedó en el teléfono no incluye la huella de ninguna contraseña ajena
        huellas = self.local.bd.consultar("SELECT * FROM usuarios")
        self.assertTrue(all("clave_hash" not in f or not f["clave_hash"] for f in huellas))

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


if __name__ == "__main__":
    unittest.main()

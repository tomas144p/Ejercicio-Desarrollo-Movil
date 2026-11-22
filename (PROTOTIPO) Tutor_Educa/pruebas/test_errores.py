"""
Registro de errores de la app («crasheos»): limpieza de datos personales, huella de la causa, cola local,
cierres inesperados, y el viaje hasta el servidor con sus permisos.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI))

from models.datos.local import BaseDatosLocal  # noqa: E402
from services.registro_errores import (MAX_PENDIENTES, SEGUNDOS_ENTRE_IGUALES, TIPO_CIERRE, RegistroErrores,  # noqa: E402
                                       construir_registro, limpiar)
from test_backend import HAY_API, BaseApi, ahora, correo  # noqa: E402


class LocalFalso:
    """Lo mínimo que usa RegistroErrores del teléfono, en memoria."""

    def __init__(self):
        self.errores, self.prefs = [], {}

    def encolar_error(self, datos, maximo=50):
        self.errores.append(datos)

    def preferencia(self, clave, defecto=None):
        return self.prefs.get(clave, defecto)

    def guardar_preferencia(self, clave, valor):
        self.prefs[clave] = valor


def lanzar(excepcion):
    try:
        raise excepcion
    except Exception as e:
        return sys.exc_info()[0], e, e.__traceback__


def falla_a(mensaje):
    raise KeyError(mensaje)


def falla_b(mensaje):
    raise KeyError(mensaje)


def capturar(funcion, mensaje):
    try:
        funcion(mensaje)
    except Exception:
        return sys.exc_info()


class PruebasLimpieza(unittest.TestCase):
    def test_quita_lo_que_identifica_a_una_persona(self):
        texto = ("Falló para sofia.diaz@colegio.cl con clave=hunter2 y Bearer abc.def.ghi, RUT 12.345.678-9, "
                 "fono 56912345678, token: eyJhbGciOi.eyJzdWIiOi.firma123 en C:\\Users\\Rodrigo\\app y /home/rodrigo/app")
        limpio = limpiar(texto)
        for secreto in ("sofia.diaz", "colegio.cl", "hunter2", "abc.def.ghi", "12.345.678", "56912345678",
                        "eyJhbGci", "Rodrigo", "rodrigo"):
            self.assertNotIn(secreto, limpio, secreto)

    def test_oculta_textos_entre_comillas_que_podrian_ser_nombres(self):
        self.assertEqual(limpiar("KeyError: 'Sofía Pérez'"), "KeyError: '<texto>'")
        self.assertEqual(limpiar("KeyError: 'curso_id'"), "KeyError: 'curso_id'")      # un nombre de campo se conserva

    def test_recorta(self):
        self.assertEqual(len(limpiar("a" * 1000)), 300)

    def test_el_registro_no_lleva_datos_personales(self):
        tipo, error, tb = lanzar(ValueError("No se pudo enviar a sofia@colegio.cl: 'Sofía Pérez' (RUT 12.345.678-9)"))
        registro = construir_registro(tipo, error, tb, "docente", "0.1.0", "android")
        texto = " ".join(str(v) for v in registro.values())
        for dato in ("sofia@colegio.cl", "Sofía Pérez", "12.345.678"):
            self.assertNotIn(dato, texto)
        self.assertEqual((registro["tipo"], registro["pantalla"], registro["version"], registro["plataforma"]),
                         ("ValueError", "docente", "0.1.0", "android"))
        self.assertRegex(registro["traza"], r"test_errores\.py:\d+ en lanzar")      # solo archivo, línea y función
        self.assertNotIn("raise excepcion", registro["traza"])                      # nunca el código fuente


class PruebasHuella(unittest.TestCase):
    def test_misma_causa_misma_huella_aunque_cambie_el_mensaje(self):
        a1 = construir_registro(*capturar(falla_a, "uno"))
        a2 = construir_registro(*capturar(falla_a, "otro"))
        self.assertEqual(a1["huella"], a2["huella"])

    def test_distinto_lugar_distinta_huella(self):
        a = construir_registro(*capturar(falla_a, "x"))
        b = construir_registro(*capturar(falla_b, "x"))
        self.assertNotEqual(a["huella"], b["huella"])

    def test_distinto_tipo_distinta_huella(self):
        a = construir_registro(*lanzar(ValueError("x")))
        b = construir_registro(*lanzar(KeyError("x")))
        self.assertNotEqual(a["huella"], b["huella"])


class PruebasRegistro(unittest.TestCase):
    def setUp(self):
        self.local, self.hora = LocalFalso(), [0.0]
        self.registro = RegistroErrores(self.local, "0.1.0", "android", lambda: "docente", reloj=lambda: self.hora[0])

    def test_guarda_el_error_con_la_pantalla(self):
        guardado = self.registro.registrar(*lanzar(ValueError("x")))
        self.assertEqual(len(self.local.errores), 1)
        self.assertEqual(guardado["pantalla"], "docente")

    def test_el_mismo_error_seguido_se_guarda_una_vez(self):
        for _ in range(5):
            self.registro.registrar(*capturar(falla_a, "x"))
        self.assertEqual((len(self.local.errores), self.registro.repetidos), (1, 4))
        self.hora[0] += SEGUNDOS_ENTRE_IGUALES + 1
        self.registro.registrar(*capturar(falla_a, "x"))
        self.assertEqual(len(self.local.errores), 2)

    def test_detecta_una_app_que_falla_en_bucle(self):
        for _ in range(5):
            self.registro.registrar(*capturar(falla_a, "x"))
        self.assertFalse(self.registro.en_bucle())              # 5 en poco tiempo todavía es tolerable
        self.registro.registrar(*capturar(falla_a, "x"))
        self.assertTrue(self.registro.en_bucle())                # el sexto: la app está en bucle
        self.hora[0] += 60
        self.assertFalse(self.registro.en_bucle())              # pasado el tiempo, vuelve a la normalidad

    def test_registrar_un_error_nunca_lanza_otro(self):
        class Roto(LocalFalso):
            def encolar_error(self, datos, maximo=50):
                raise RuntimeError("disco lleno")
        registro = RegistroErrores(Roto(), pantalla=lambda: 1 / 0)
        self.assertIsNone(registro.registrar(*lanzar(ValueError("x"))))

    def test_los_ganchos_registran_errores_de_otros_hilos(self):
        anterior = threading.excepthook
        silencio = lambda args: None
        threading.excepthook = silencio                         # para que la prueba no imprima la traza
        self.registro._previos = (sys.excepthook, silencio)
        self.registro.instalar_ganchos()
        try:
            hilo = threading.Thread(target=lambda: falla_a("en un hilo"))
            hilo.start(); hilo.join()
        finally:
            self.registro.desinstalar_ganchos()
            threading.excepthook = anterior
        self.assertEqual([e["tipo"] for e in self.local.errores], ["KeyError"])


class PruebasCierreInesperado(unittest.TestCase):
    def setUp(self):
        self.local = LocalFalso()

    def abrir(self):
        return RegistroErrores(self.local, "0.1.0", "android").revisar_cierre_anterior()

    def test_la_primera_vez_no_hay_nada_que_reportar(self):
        self.assertIsNone(self.abrir())
        self.assertEqual(self.local.prefs["sesion_estado"], "activa")

    def test_si_la_app_quedo_activa_fue_un_cierre_inesperado(self):
        self.abrir()
        self.local.prefs["ultima_pantalla"] = "leccion"
        registro = self.abrir()
        self.assertEqual((registro["tipo"], registro["pantalla"]), (TIPO_CIERRE, "leccion"))
        self.assertEqual(len(self.local.errores), 1)

    def test_cerrar_bien_o_pausar_no_es_un_cierre_inesperado(self):
        for estado in ("cerrada", "pausa"):
            self.local = LocalFalso()                       # cada caso parte de un teléfono nuevo
            self.abrir()
            RegistroErrores(self.local).marcar_estado(estado)
            self.assertIsNone(self.abrir(), estado)
            self.assertEqual(self.local.errores, [])


class PruebasColaLocal(unittest.TestCase):
    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp())
        self.local = BaseDatosLocal(self.carpeta / "local.db")

    def tearDown(self):
        self.local.bd.cerrar()
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def error(self, n):
        return {"codigo": f"codigo-{n:04d}", "tipo": "ValueError"}

    def test_se_guardan_como_maximo_los_ultimos(self):
        for n in range(MAX_PENDIENTES + 10):
            self.local.encolar_error(self.error(n), MAX_PENDIENTES)
        filas = [f for f in self.local.pendientes() if f["tipo"] == "error_app"]
        self.assertEqual(len(filas), MAX_PENDIENTES)
        self.assertIn(f"codigo-{MAX_PENDIENTES + 9:04d}", filas[-1]["datos"])           # se conservan los más nuevos
        self.assertNotIn("codigo-0000", " ".join(f["datos"] for f in filas))

    def test_los_errores_no_cuentan_como_cambios_pendientes(self):
        self.local.encolar_error(self.error(1))
        self.assertEqual(self.local.cantidad_pendientes(), 0)
        self.local.encolar("aviso", {"x": 1})
        self.assertEqual(self.local.cantidad_pendientes(), 1)


try:
    import os
    os.environ.setdefault("KIVY_NO_ARGS", "1")
    os.environ.setdefault("KIVY_LOG_MODE", "PYTHON")      # que Kivy no se apodere de la salida de las pruebas
    from kivy.base import ExceptionManager
    from controladores.errores import MENSAJE, ManejadorErrores
    HAY_KIVY = True
except Exception:                                   # sin Kivy instalado esta prueba se omite
    HAY_KIVY = False


@unittest.skipUnless(HAY_KIVY, "Kivy no está instalado")
class PruebasManejadorKivy(unittest.TestCase):
    def setUp(self):
        self.local, self.hora, self.avisos = LocalFalso(), [0.0], []
        registro = RegistroErrores(self.local, "0.1.0", "linux", lambda: "docente", reloj=lambda: self.hora[0])
        self.app = SimpleNamespace(registro_errores=registro,
                                   notificador=SimpleNamespace(mostrar=lambda texto, tipo="info": self.avisos.append((texto, tipo))))
        self.manejador = ManejadorErrores(self.app)

    def test_registra_avisa_con_amabilidad_y_deja_seguir(self):
        self.assertEqual(self.manejador.handle_exception(ValueError("x")), ExceptionManager.PASS)
        self.assertEqual(len(self.local.errores), 1)
        self.assertEqual(self.avisos, [(MENSAJE, "error")])

    def test_si_falla_en_bucle_deja_que_se_cierre(self):
        resultados = [self.manejador.handle_exception(ValueError(str(n))) for n in range(8)]
        self.assertEqual(resultados[0], ExceptionManager.PASS)
        self.assertEqual(resultados[-1], ExceptionManager.RAISE)

    def test_si_el_aviso_falla_no_provoca_otro_error(self):
        def roto(texto, tipo="info"):
            raise RuntimeError("sin pantalla")
        self.app.notificador.mostrar = roto
        self.assertEqual(self.manejador.handle_exception(ValueError("x")), ExceptionManager.RAISE)


@unittest.skipUnless(HAY_API, "FastAPI no está instalado")
class PruebasServidor(BaseApi):
    def setUp(self):
        super().setUp()
        self.persona("admin.a", "admin", 1)
        self.persona("super", "superadmin", None)
        self.persona("alumno.error", "estudiante", 1)
        self.persona("docente.error", "docente", 1)

    def datos(self, **cambios):
        base = {"codigo": f"err-{len(self.repo.bd.consultar('SELECT id FROM errores_app')):06d}", "creado_en": ahora(),
                "version": "0.1.0", "plataforma": "android", "pantalla": "leccion", "tipo": "KeyError",
                "mensaje": "curso_id", "traza": "views/leccion_screen.py:10 en abrir", "huella": "abc123def456"}
        base.update(cambios)
        return base

    def enviar(self, usuario, **cambios):
        return self.cambio(usuario, "error_app", self.datos(**cambios))

    def test_cualquier_perfil_puede_informar_un_error(self):
        for usuario in ("alumno.error", "docente.error", "admin.a"):
            self.assertEqual(self.enviar(usuario, codigo=f"cod-{usuario}-0001").status_code, 200, usuario)

    def test_el_servidor_limpia_otra_vez_y_toma_el_colegio_de_la_sesion(self):
        # El celular intenta decir que es de otro colegio y de otro perfil: el servidor lo ignora y usa la sesión.
        r = self.enviar("alumno.error", mensaje="falló para sofia@colegio.cl con clave=hunter2 'Sofía Pérez'",
                        traza="views/x.py:1 en f\ntoken=zxqsecreto99", colegio_id=2, rol="superadmin")
        self.assertEqual(r.status_code, 200)
        fila = self.repo.bd.consultar_uno("SELECT * FROM errores_app ORDER BY id DESC LIMIT 1")
        texto = " ".join(str(v) for v in fila.values())
        for dato in ("sofia@colegio.cl", "hunter2", "Sofía Pérez", "zxqsecreto99"):
            self.assertNotIn(dato, texto)
        self.assertEqual((fila["colegio_id"], fila["rol"]), (1, "estudiante"))

    def test_no_se_duplica_el_mismo_codigo(self):
        self.enviar("alumno.error", codigo="mismo-codigo-1")
        self.enviar("alumno.error", codigo="mismo-codigo-1")
        self.assertEqual(self.repo.bd.valor("SELECT COUNT(*) FROM errores_app WHERE codigo = 'mismo-codigo-1'"), 1)

    def test_datos_invalidos_se_rechazan(self):
        self.assertEqual(self.enviar("alumno.error", huella="no-es-hex!").status_code, 422)
        self.assertEqual(self.enviar("alumno.error", tipo="").status_code, 422)
        self.assertEqual(self.enviar("alumno.error", codigo="corto").status_code, 422)
        self.assertEqual(self.enviar("alumno.error", creado_en="ayer").status_code, 422)
        self.assertEqual(self.enviar("alumno.error", mensaje=123).status_code, 200)       # un tipo raro no rompe: queda vacío

    def test_tope_diario_por_colegio(self):
        self.repo.MAX_ERRORES_POR_COLEGIO_AL_DIA = 3
        for n in range(6):
            self.enviar("alumno.error", codigo=f"tope-{n:04d}-codigo")
        self.assertEqual(self.repo.bd.valor("SELECT COUNT(*) FROM errores_app WHERE colegio_id = 1"), 3)

    def test_se_borran_los_errores_antiguos(self):
        self.repo.bd.insertar("errores_app", {"codigo": "viejo-0001", "colegio_id": 1, "rol": "estudiante",
                                              "creado_en": "2025-01-01 10:00:00", "recibido_en": "2025-01-01 10:00:00",
                                              "tipo": "KeyError", "huella": "abc123def456"})
        self.enviar("alumno.error", codigo="nuevo-0001-ok")
        self.assertEqual(self.repo.bd.valor("SELECT COUNT(*) FROM errores_app WHERE codigo = 'viejo-0001'"), 0)

    def test_la_administradora_ve_los_errores_agrupados_de_su_colegio(self):
        for n in range(3):
            self.enviar("alumno.error", codigo=f"grupo-{n:04d}-a", huella="aaaaaaaaaaaa", tipo="KeyError")
        self.enviar("docente.error", codigo="grupo-0000-b", huella="bbbbbbbbbbbb", tipo="ValueError", pantalla="docente")
        r = self.cliente.get("/admin/errores", headers=self.cabeceras("admin.a"))
        self.assertEqual(r.status_code, 200, r.text)
        datos = r.json()
        self.assertEqual((datos["total"], datos["colegio_id"]), (4, 1))
        self.assertEqual([(g["huella"], g["veces"]) for g in datos["grupos"]], [("aaaaaaaaaaaa", 3), ("bbbbbbbbbbbb", 1)])
        self.assertEqual(datos["grupos"][0]["pantalla"], "leccion")
        self.assertIn("traza", datos["grupos"][0])

    def test_otro_colegio_no_ve_los_errores_de_este(self):
        otro = self.colegio_b()
        self.persona("admin.b", "admin", otro["colegio"])
        self.enviar("alumno.error", codigo="privado-0001-a")
        propio = self.cliente.get("/admin/errores", headers=self.cabeceras("admin.b")).json()
        self.assertEqual(propio["total"], 0)
        # ni pidiéndolo por el colegio ajeno
        ajeno = self.cliente.get("/admin/errores?colegio_id=1", headers=self.cabeceras("admin.b"))
        self.assertEqual(ajeno.status_code, 403)

    def test_la_superadmin_ve_todos_o_los_de_un_colegio(self):
        otro = self.colegio_b()
        self.enviar("alumno.error", codigo="todos-0001-a")
        self.cambio("docente.b", "error_app", self.datos(codigo="todos-0002-b", huella="cccccccccccc"))
        todos = self.cliente.get("/admin/errores", headers=self.cabeceras("super")).json()
        self.assertEqual((todos["total"], todos["colegio_id"]), (2, None))
        solo = self.cliente.get(f"/admin/errores?colegio_id={otro['colegio']}", headers=self.cabeceras("super")).json()
        self.assertEqual(solo["total"], 1)

    def test_docentes_estudiantes_y_visitas_no_ven_la_lista(self):
        self.assertEqual(self.cliente.get("/admin/errores", headers=self.cabeceras("docente.error")).status_code, 403)
        self.assertEqual(self.cliente.get("/admin/errores", headers=self.cabeceras("alumno.error")).status_code, 403)
        self.assertEqual(self.cliente.get("/admin/errores").status_code, 401)

    def test_limite_de_dias_acotado(self):
        cab = self.cabeceras("admin.a")
        self.assertEqual(self.cliente.get("/admin/errores?dias=0", headers=cab).status_code, 422)
        self.assertEqual(self.cliente.get("/admin/errores?dias=366", headers=cab).status_code, 422)

    def test_sin_sesion_no_se_aceptan_errores(self):
        r = self.cliente.post("/cambios", json={"tipo": "error_app", "datos": self.datos()})
        self.assertEqual(r.status_code, 401)


if __name__ == "__main__":
    unittest.main()

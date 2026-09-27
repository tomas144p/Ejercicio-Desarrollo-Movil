"""
Pruebas automáticas del núcleo de Tutor Educa (sin interfaz gráfica).

Ejecutar desde la carpeta del proyecto:

    python -m unittest discover pruebas -v

Si hay un MySQL/MariaDB local (XAMPP) con usuario root sin contraseña, también
se prueba el camino MySQL en una base temporal "tutor_educa_pruebas".
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tutor_educa.configuracion import ConfigServidor, Configuracion  # noqa: E402
from tutor_educa.contenido.datos_iniciales import DatosIniciales  # noqa: E402
from tutor_educa.datos.conexiones import ConexionMySQL, ErrorConexion  # noqa: E402
from tutor_educa.datos.esquema import crear_esquema  # noqa: E402
from tutor_educa.datos.local import BaseDatosLocal  # noqa: E402
from tutor_educa.datos.servidor import GestorServidor, ServidorRemoto  # noqa: E402
from tutor_educa.evaluacion import CorrectorRespuestas, SesionPrueba  # noqa: E402
from tutor_educa.modelos import (Aviso, EscalaNotas, EstadoRefuerzo, Intento, Pregunta,  # noqa: E402
                                 Usuario)
from tutor_educa.seguridad import GestorClaves  # noqa: E402
from tutor_educa.servicios.autenticacion import ServicioAutenticacion  # noqa: E402
from tutor_educa.servicios.datos_app import ServicioDatos  # noqa: E402
from tutor_educa.servicios.ia.conversacion import ContextoConversacion, ServicioTutorIA  # noqa: E402
from tutor_educa.servicios.sincronizacion import ServicioSincronizacion  # noqa: E402

CLAVE = DatosIniciales.CLAVE_DEMO


class MonitorFalso:
    """Reemplaza al monitor real: permite simular "sin conexión"."""
    forzado_sin_conexion = False


def pregunta(respuesta: str, tipo: str = "numerica", alternativas: str = "") -> Pregunta:
    return Pregunta(1, "t", 1, "¿?", tipo, alternativas, respuesta)


class PruebasBasicas(unittest.TestCase):
    def test_claves(self):
        huella = GestorClaves.generar_hash("secreto")
        self.assertTrue(GestorClaves.verificar("secreto", huella))
        self.assertFalse(GestorClaves.verificar("Secreto", huella))
        self.assertNotIn("secreto", huella)
        self.assertNotEqual(huella, GestorClaves.generar_hash("secreto"))  # sal distinta

    def test_corrector_acepta_variantes(self):
        c = CorrectorRespuestas()
        casos = [("5", ["5", "x = 5", "x=5", " 5 ", "5.", "5 cm"]),
                 ("-10", ["-10", "−10", "x = −10", "–10"]),
                 ("0.75", ["0,75", "0.75", "3/4", "6/8"]),
                 ("32000", ["32000", "32.000", "$32.000", "32 000", "$ 32.000"]),
                 ("5/6", ["5/6", "10/12", "0,83", "0.833"]),
                 ("20", ["20", "20%", "20 %"])]
        for esperada, respuestas in casos:
            for r in respuestas:
                self.assertTrue(c.es_correcta(pregunta(esperada), r), f"{r!r} debería valer {esperada}")
        self.assertFalse(c.es_correcta(pregunta("5/6"), "0,8"))
        self.assertFalse(c.es_correcta(pregunta("32000"), "8000"))
        self.assertFalse(c.es_correcta(pregunta("5"), ""))
        self.assertTrue(c.es_correcta(pregunta("x = 6", "alternativas", "x = 13|x = 6"), "x = 6"))

    def test_escala_notas(self):
        self.assertEqual(EscalaNotas.nota(5, 5), 7.0)
        self.assertEqual(EscalaNotas.nota(3, 5), 4.0)
        self.assertEqual(EscalaNotas.nota(4, 5), 5.5)
        self.assertEqual(EscalaNotas.nota(0, 5), 1.0)
        self.assertEqual(EscalaNotas.formatear(5.25), "5,3")

    def test_contenido_coherente(self):
        """Cada respuesta guardada debe ser aceptada por el corrector (evita errores en la materia)."""
        datos = DatosIniciales().contenido()
        self.assertEqual(len(datos["temas"]), 7)
        c = CorrectorRespuestas()
        for fila in datos["preguntas"]:
            p = Pregunta(fila["id"], fila["tema_id"], fila["orden"], fila["enunciado"], fila["tipo"],
                         fila["alternativas"], fila["respuesta"])
            self.assertTrue(c.es_correcta(p, p.respuesta_para_mostrar), f"Pregunta {fila['id']}: {fila['enunciado']}")
            if p.es_alternativas:
                self.assertIn(p.respuesta, p.alternativas)

    def test_sesion_prueba(self):
        preguntas = [pregunta("1"), pregunta("2"), pregunta("3"), pregunta("4"), pregunta("5")]
        sesion = SesionPrueba(preguntas)
        for respuesta in ["1", "2", "3", "0", "0"]:
            sesion.responder(respuesta)
            sesion.siguiente()
        self.assertTrue(sesion.terminada)
        self.assertEqual((sesion.correctas, sesion.porcentaje, sesion.nota, sesion.logrado), (3, 60, 4.0, True))


class PruebasConServidor(unittest.TestCase):
    """Usa el servidor de demostración (SQLite) para probar ingreso y sincronización."""

    @classmethod
    def setUpClass(cls):
        cls.plantilla = Path(tempfile.mkdtemp())
        GestorServidor(ConfigServidor(motor="demo"), cls.plantilla).inicializar()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.plantilla, ignore_errors=True)

    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp())
        shutil.copy(self.plantilla / "servidor_demo.db", self.carpeta / "servidor_demo.db")
        self.gestor = GestorServidor(ConfigServidor(motor="demo"), self.carpeta).inicializar()
        self.local = BaseDatosLocal(self.carpeta / "local.db")
        self.sinc = ServicioSincronizacion(self.local, self.gestor)
        self.monitor = MonitorFalso()
        self.auth = ServicioAutenticacion(self.local, self.gestor, self.sinc, self.monitor)
        self.datos = ServicioDatos(self.local)

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def correo(self, usuario):
        return f"{usuario}@{DatosIniciales.DOMINIO}"

    def test_materia_disponible_antes_del_primer_ingreso(self):
        self.assertEqual(len(self.local.temas()), 7)
        self.assertEqual(len(self.local.preguntas("mat-ecuaciones")), 5)

    def test_rol_segun_correo(self):
        for usuario, rol in (("sofia.morales", "estudiante"), ("carolina.fuentes", "docente"),
                             ("andres.morales", "apoderado")):
            resultado = self.auth.ingresar(self.correo(usuario), CLAVE)
            self.assertTrue(resultado.exito, resultado.mensaje)
            self.assertEqual(resultado.usuario.rol, rol)

    def test_ingreso_fallido(self):
        self.assertFalse(self.auth.ingresar(self.correo("sofia.morales"), "otra").exito)
        self.assertFalse(self.auth.ingresar("nadie@tutoreduca.cl", CLAVE).exito)
        self.assertFalse(self.auth.ingresar("correo-malo", CLAVE).exito)

    def test_ingreso_sin_conexion_con_credencial_recordada(self):
        self.monitor.forzado_sin_conexion = True
        self.assertFalse(self.auth.ingresar(self.correo("sofia.morales"), CLAVE).exito)  # nunca ingresó
        self.monitor.forzado_sin_conexion = False
        self.assertTrue(self.auth.ingresar(self.correo("sofia.morales"), CLAVE, recordar=True).exito)
        self.monitor.forzado_sin_conexion = True
        resultado = self.auth.ingresar(self.correo("sofia.morales"), CLAVE)
        self.assertTrue(resultado.exito)
        self.assertFalse(resultado.en_linea)
        self.assertFalse(self.auth.ingresar(self.correo("sofia.morales"), "mala").exito)
        # Los datos descargados siguen disponibles sin conexión.
        self.datos.iniciar_sesion(resultado.usuario)
        ficha = self.datos.ficha(resultado.usuario.id)
        self.assertEqual(ficha.promedio("mat"), 5.1)
        self.assertEqual(len(ficha.refuerzos_activos), 2)
        # Sin «Recordarme» la credencial se borra.
        self.monitor.forzado_sin_conexion = False
        self.auth.ingresar(self.correo("sofia.morales"), CLAVE, recordar=False)
        self.assertIsNone(self.local.credencial(self.correo("sofia.morales")))

    def test_intento_sin_conexion_se_sincroniza(self):
        sofia = self.auth.ingresar(self.correo("sofia.morales"), CLAVE).usuario
        self.datos.iniciar_sesion(sofia)
        intento = Intento.nuevo(sofia.id, "mat-ecuaciones", 5, 5)
        self.assertTrue(self.datos.registrar_intento(intento))           # queda logrado localmente
        self.assertEqual(self.local.cantidad_pendientes(), 2)
        self.assertLess(self.local.intentos([sofia.id])[0].id, 0)        # id local negativo
        resultado = self.sinc.sincronizar(sofia)
        self.assertEqual((resultado.enviados, resultado.descargado), (2, True))
        self.assertEqual(self.local.cantidad_pendientes(), 0)
        servidor = self.gestor.servidor
        estados = {r.tema_id: r.estado for r in servidor.refuerzos([sofia.id])}
        self.assertEqual(estados["mat-ecuaciones"], EstadoRefuerzo.LOGRADO)
        self.assertEqual(len(servidor.intentos([sofia.id])), 3)
        self.sinc.sincronizar(sofia)                                     # repetir no duplica
        self.assertEqual(len(servidor.intentos([sofia.id])), 3)

    def test_docente_desbloquea_y_estudiante_lo_recibe(self):
        docente = self.auth.ingresar(self.correo("carolina.fuentes"), CLAVE).usuario
        self.datos.iniciar_sesion(docente)
        curso = self.datos.cursos_docente()[0]
        fichas = self.datos.fichas_curso(curso.id)
        self.assertEqual(len(fichas), 8)
        necesitan = [f.estudiante.id for f in fichas if f.necesita_refuerzo]
        self.assertEqual(len(necesitan), 3)
        self.datos.desbloquear_varios(necesitan, "mat-potencias", "Repasen potencias")
        self.datos.publicar_aviso(Aviso.nuevo(curso.id, docente.id, "Aviso de prueba", "Cuerpo del aviso"))
        self.sinc.sincronizar(docente)
        camila = self.auth.ingresar(self.correo("camila.perez"), CLAVE).usuario
        self.datos.iniciar_sesion(camila)
        temas = {r.tema_id: r for r in self.datos.ficha(camila.id).refuerzos_activos}
        self.assertIn("mat-potencias", temas)
        self.assertEqual(temas["mat-potencias"].mensaje, "Repasen potencias")
        rodrigo = self.auth.ingresar(self.correo("rodrigo.perez"), CLAVE).usuario
        self.datos.iniciar_sesion(rodrigo)
        avisos = self.datos.avisos_apoderado()
        self.assertIn("Aviso de prueba", [a.titulo for a in avisos])
        no_leidos = self.datos.no_leidos()
        self.datos.marcar_leido(avisos[0])
        self.assertEqual(self.datos.no_leidos(), no_leidos - 1)

    def test_tutor_local(self):
        sofia = self.auth.ingresar(self.correo("sofia.morales"), CLAVE).usuario
        self.datos.iniciar_sesion(sofia)
        from tutor_educa.configuracion import ConfigIA
        servicio = ServicioTutorIA(ConfigIA(api_key=""), self.datos)
        self.assertFalse(servicio.usa_ia_real)
        contexto = ContextoConversacion("estudiante", sofia, tema=self.datos.tema("mat-ecuaciones"),
                                        ficha=self.datos.ficha(sofia.id))
        chat = servicio.conversacion(contexto)
        for texto in ("explícame", "dame un ejemplo", "hazme una prueba"):
            chat.agregar_usuario(texto)
            self.assertTrue(chat.generar_respuesta().texto)
        self.assertIn("Pregunta 1 de 3", chat.mensajes[-1].texto)
        sesion = chat.estado_local.sesion
        for _ in range(3):
            actual = sesion.actual
            chat.agregar_usuario(actual.respuesta_para_mostrar)
            chat.generar_respuesta()
        self.assertTrue(sesion.terminada)
        self.assertEqual(sesion.correctas, 3)
        apoderado = Usuario.desde_fila({"id": 10, "correo": "a@b.cl", "nombre": "Andrés Morales", "rol": "apoderado"})
        contexto = ContextoConversacion("apoderado", apoderado, ficha=self.datos.ficha(sofia.id),
                                        nombres_asignaturas={a.id: a.nombre for a in self.datos.asignaturas()})
        chat = servicio.conversacion(contexto)
        chat.agregar_usuario("¿Cómo lo apoyo en casa?")
        self.assertIn("Ecuaciones", chat.generar_respuesta().texto)


class PruebasMySQL(unittest.TestCase):
    """Se ejecuta solo si hay MySQL/MariaDB local con root sin contraseña."""

    BASE = "tutor_educa_pruebas"

    def setUp(self):
        try:
            admin = ConexionMySQL("127.0.0.1", 3306, "root", "", "", 2)
        except ErrorConexion as error:
            self.skipTest(f"MySQL no disponible: {error}")
        admin.ejecutar(f"DROP DATABASE IF EXISTS {self.BASE}")
        admin.ejecutar(f"CREATE DATABASE {self.BASE} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        admin.cerrar()
        self.conexion = ConexionMySQL("127.0.0.1", 3306, "root", "", self.BASE, 2)
        crear_esquema(self.conexion)
        self.conexion.insertar_tablas(DatosIniciales().todo())
        self.carpeta = Path(tempfile.mkdtemp())

    def tearDown(self):
        self.conexion.ejecutar(f"DROP DATABASE IF EXISTS {self.BASE}")
        self.conexion.cerrar()
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def test_flujo_completo_en_mysql(self):
        config = ConfigServidor(motor="mysql", base_datos=self.BASE)
        gestor = GestorServidor(config, self.carpeta).inicializar()
        self.assertFalse(gestor.es_demo, gestor.diagnostico)
        local = BaseDatosLocal(self.carpeta / "local.db")
        sinc = ServicioSincronizacion(local, gestor)
        auth = ServicioAutenticacion(local, gestor, sinc, MonitorFalso())
        resultado = auth.ingresar(f"sofia.morales@{DatosIniciales.DOMINIO}", CLAVE)
        self.assertTrue(resultado.exito, resultado.mensaje)
        datos = ServicioDatos(local)
        datos.iniciar_sesion(resultado.usuario)
        datos.registrar_intento(Intento.nuevo(resultado.usuario.id, "mat-ecuaciones", 4, 5))
        self.assertEqual(sinc.sincronizar(resultado.usuario).enviados, 2)
        self.assertEqual(self.conexion.valor("SELECT COUNT(*) FROM intentos WHERE estudiante_id = 2"), 3)


if __name__ == "__main__":
    unittest.main()

"""Construcción de la app: crea los servicios, las pantallas y la navegación."""

from __future__ import annotations

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, SlideTransition

from services.configuracion import Configuracion
from models.datos.local import BaseDatosLocal
from models.datos.servidor import GestorServidor
from views.dialogos import Notificador
from views.estilo import Paleta, Tipografia, color
from views.apoderado_screen import PantallaApoderado
from views.chat_screen import PantallaChat
from views.docente_screen import PantallaDocente
from views.estudiante_screen import PantallaEstudiante
from views.ficha_estudiante_screen import PantallaFichaEstudiante
from views.ingreso_screen import PantallaIngreso
from views.leccion_screen import PantallaLeccion
from views.raiz import RaizApp
from services.autenticacion import ServicioAutenticacion
from services.conexion import MonitorConexion
from services.datos_app import ServicioDatos
from services.ia.conversacion import ServicioTutorIA
from services.sincronizacion import ServicioSincronizacion
from services.tareas import EjecutorEnSegundoPlano


def programador_kivy(funcion) -> None:
    """Ejecuta ``funcion`` en el hilo principal de Kivy en el próximo cuadro."""
    Clock.schedule_once(lambda _dt: funcion(), 0)


class ConstruccionApp:
    """Parte de TutorEducaApp que arma todo al iniciar (y lo apaga al cerrar)."""

    def build(self):
        self.title = "Tutor Educa"
        self.theme_cls.theme_style = "Light"      # KivyMD 2.0: tema claro y color base azul
        self.theme_cls.primary_palette = "Blue"
        Window.clearcolor = color(Paleta.PAPEL)
        Window.softinput_mode = "below_target"    # el teclado del celular no tapa el campo activo
        Tipografia.registrar()

        # 1. Servicios (capa de datos y lógica)
        self.configuracion = Configuracion.cargar()
        carpeta = self.configuracion.carpeta_datos(self.user_data_dir)
        self.usuario = None
        self.local = BaseDatosLocal(carpeta / "tutor_educa_local.db")
        self.gestor_servidor = GestorServidor(self.configuracion.servidor, carpeta)
        self.ejecutor_datos = EjecutorEnSegundoPlano("datos", programador_kivy)
        self.ejecutor_ia = EjecutorEnSegundoPlano("ia", programador_kivy)
        url_internet = self.configuracion.ia.url_base or "https://api.anthropic.com"
        self.monitor = MonitorConexion(self.gestor_servidor, self.ejecutor_datos, url_internet=url_internet)
        self.sincronizacion = ServicioSincronizacion(self.local, self.gestor_servidor)
        self.autenticacion = ServicioAutenticacion(self.local, self.gestor_servidor, self.sincronizacion, self.monitor)
        self.datos = ServicioDatos(self.local, al_haber_cambios=self._hubo_cambios)
        self.tutor_ia = ServicioTutorIA(self.configuracion.ia, self.datos)
        self.pendientes = self.local.cantidad_pendientes()
        self._sincronizar_de_nuevo = False
        self._historial: list[str] = []

        # 2. Interfaz
        self.gestor = ScreenManager(transition=SlideTransition(duration=0.22))
        self.raiz = RaizApp(self.gestor)
        self.notificador = Notificador(self.raiz.capa_avisos)
        for clase, nombre in ((PantallaIngreso, "ingreso"), (PantallaEstudiante, "estudiante"),
                                (PantallaLeccion, "leccion"), (PantallaChat, "chat"), (PantallaDocente, "docente"),
                                (PantallaFichaEstudiante, "ficha"), (PantallaApoderado, "apoderado")):
            self.gestor.add_widget(clase(self, name=nombre))

        # 3. Conexión: se busca el servidor en segundo plano y se revisa cada cierto tiempo.
        Window.bind(on_keyboard=self._tecla)
        self.monitor.suscribir(self._conexion_cambio)
        self.ejecutor_datos.enviar(self.gestor_servidor.inicializar, self._servidor_listo)
        Clock.schedule_interval(lambda _dt: self.monitor.comprobar(),
                                max(5, self.configuracion.app.intervalo_sincronizacion))
        return self.raiz

    def on_stop(self):
        self.ejecutor_datos.detener()
        self.ejecutor_ia.detener()

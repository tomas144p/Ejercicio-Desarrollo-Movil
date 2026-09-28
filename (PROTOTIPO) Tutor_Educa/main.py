"""
Tutor Educa: tutor de refuerzo de matemáticas (5° a 8° básico).

Punto de entrada de la aplicación. Aquí solo se "arma" la app: se crean los
servicios (base de datos, sincronización, inicio de sesión, IA), las
pantallas y la navegación entre ellas. La lógica vive en el paquete
``tutor_educa``.

Ejecutar:  python main.py
"""

from __future__ import annotations

import sys
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kivy.config import Config  # noqa: E402

# Estas opciones deben definirse ANTES de crear la ventana.
Config.set("input", "mouse", "mouse,multitouch_on_demand")  # sin puntos rojos al hacer clic derecho
Config.set("kivy", "exit_on_escape", "0")                    # Esc / botón atrás lo maneja la app
Config.set("graphics", "width", "412")                        # tamaño de celular Android típico
Config.set("graphics", "height", "760")

from kivy.app import App  # noqa: E402
from kivy.clock import Clock  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from kivy.metrics import dp  # noqa: E402
from kivy.properties import BooleanProperty, NumericProperty, StringProperty  # noqa: E402
from kivy.uix.floatlayout import FloatLayout  # noqa: E402
from kivy.uix.modalview import ModalView  # noqa: E402
from kivy.uix.screenmanager import FadeTransition, ScreenManager, SlideTransition  # noqa: E402

from tutor_educa.configuracion import Configuracion  # noqa: E402
from tutor_educa.datos.local import BaseDatosLocal  # noqa: E402
from tutor_educa.datos.servidor import GestorServidor  # noqa: E402
from tutor_educa.interfaz.componentes import (Columna, FilaLista, InsigniaIcono, Interruptor,  # noqa: E402
                                                Separador, Texto)
from tutor_educa.interfaz.dialogos import Dialogo, Notificador  # noqa: E402
from tutor_educa.interfaz.estilo import Paleta, Tipografia, color  # noqa: E402
from tutor_educa.interfaz.pantallas.apoderado import PantallaApoderado  # noqa: E402
from tutor_educa.interfaz.pantallas.chat import PantallaChat  # noqa: E402
from tutor_educa.interfaz.pantallas.docente import PantallaDocente  # noqa: E402
from tutor_educa.interfaz.pantallas.estudiante import PantallaEstudiante  # noqa: E402
from tutor_educa.interfaz.pantallas.ficha_estudiante import PantallaFichaEstudiante  # noqa: E402
from tutor_educa.interfaz.pantallas.ingreso import PantallaIngreso  # noqa: E402
from tutor_educa.interfaz.pantallas.leccion import PantallaLeccion  # noqa: E402
from tutor_educa.modelos import Rol  # noqa: E402
from tutor_educa.servicios.autenticacion import ServicioAutenticacion  # noqa: E402
from tutor_educa.servicios.conexion import MonitorConexion  # noqa: E402
from tutor_educa.servicios.datos_app import ServicioDatos  # noqa: E402
from tutor_educa.servicios.ia.conversacion import ContextoConversacion, ServicioTutorIA  # noqa: E402
from tutor_educa.servicios.sincronizacion import ServicioSincronizacion  # noqa: E402
from tutor_educa.servicios.tareas import EjecutorEnSegundoPlano, programador_kivy  # noqa: E402


class RaizApp(FloatLayout):
    """Contenedor raíz: las pantallas abajo y una capa encima para las notificaciones."""

    def __init__(self, gestor: ScreenManager, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(gestor)
        self.capa_avisos = FloatLayout()
        self.add_widget(self.capa_avisos)


class TutorEducaApp(App):
    # Propiedades observables: las barras y pantallas se actualizan solas al cambiar.
    en_linea = BooleanProperty(False)            # el servidor del colegio responde
    internet = BooleanProperty(False)            # hay internet para el tutor IA
    sincronizando = BooleanProperty(False)
    conexion_revisada = BooleanProperty(False)   # ya se hizo la primera revisión
    pendientes = NumericProperty(0)              # cambios guardados que faltan por enviar
    descripcion_servidor = StringProperty("")

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------
    def build(self):
        self.title = "Tutor Educa"
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

    # ------------------------------------------------------------------
    # Conexión y sincronización
    # ------------------------------------------------------------------
    def _servidor_listo(self, _gestor) -> None:
        self.descripcion_servidor = self.gestor_servidor.descripcion
        print(f"[servidor] {self.gestor_servidor.diagnostico}")
        self.monitor.comprobar()

    def _conexion_cambio(self, monitor) -> None:
        antes = (self.en_linea, self.internet)
        self.en_linea, self.internet = monitor.en_linea, monitor.internet_disponible
        self.conexion_revisada = monitor.comprobado or monitor.forzado_sin_conexion
        self.descripcion_servidor = self.gestor_servidor.descripcion
        if self.en_linea and self.usuario is not None and (self.pendientes or not antes[0]):
            self.solicitar_sincronizacion()
        if antes != (self.en_linea, self.internet):
            self._refrescar_pantalla()

    def _hubo_cambios(self) -> None:
        """El usuario guardó algo: se intenta enviar de inmediato."""
        self.pendientes = self.local.cantidad_pendientes()
        self.solicitar_sincronizacion()

    def solicitar_sincronizacion(self, avisar: bool = False) -> None:
        if self.usuario is None or not self.en_linea:
            if avisar:
                self.notificador.mostrar("Sin conexión con el servidor: los cambios quedan guardados.", "aviso")
            return
        if self.sincronizando:
            self._sincronizar_de_nuevo = True
            return
        self.sincronizando = True
        usuario = self.usuario
        self.ejecutor_datos.enviar(lambda: self.sincronizacion.sincronizar(usuario),
                                    partial(self._sincronizado, usuario, avisar), self._fallo_sincronizacion)

    def _sincronizado(self, usuario, avisar: bool, resultado) -> None:
        self.sincronizando = False
        self.pendientes = self.local.cantidad_pendientes()
        if resultado.sin_conexion:
            self.monitor.comprobar()
        if usuario is self.usuario and resultado.descargado:
            self.datos.invalidar()
            self._refrescar_pantalla()
        if avisar:
            tipo = "aviso" if resultado.sin_conexion else "exito"
            self.notificador.mostrar(resultado.mensaje, tipo)
        if self._sincronizar_de_nuevo or (not resultado.descargado and not resultado.sin_conexion):
            self._sincronizar_de_nuevo = False
            Clock.schedule_once(lambda _dt: self.solicitar_sincronizacion(), 1.5)

    def _fallo_sincronizacion(self, error) -> None:
        self.sincronizando = False
        self.notificador.mostrar(f"No se pudo sincronizar: {error}", "error")

    def _refrescar_pantalla(self) -> None:
        pantalla = self.gestor.current_screen
        if pantalla is not None and (self.usuario is not None or pantalla.name == "ingreso"):
            pantalla.al_cambiar_datos()

    # ------------------------------------------------------------------
    # Sesión y navegación
    # ------------------------------------------------------------------
    def iniciar_sesion(self, resultado) -> None:
        self.usuario = resultado.usuario
        self.datos.iniciar_sesion(self.usuario)
        self.tutor_ia.olvidar_conversaciones()
        self._historial.clear()
        pantalla = self.gestor.get_screen(self.usuario.PANTALLA_INICIO)
        pantalla.reiniciar()
        self.gestor.transition = FadeTransition(duration=0.25)
        self.gestor.current = self.usuario.PANTALLA_INICIO
        self.pendientes = self.local.cantidad_pendientes()
        self.notificador.mostrar(resultado.mensaje, "exito" if resultado.en_linea else "aviso",
                                    duracion=2.5 if resultado.en_linea else 5)

    def cerrar_sesion(self) -> None:
        if self.pendientes:
            texto = (f"Hay {self.pendientes} cambio(s) sin enviar. Quedan guardados en este dispositivo y se "
                        "enviarán la próxima vez que haya conexión.")
        else:
            texto = "Podrás volver a entrar cuando quieras."
        Dialogo.confirmar("¿Cerrar sesión?", texto, "Cerrar sesión", self._cerrar_sesion, icono="log-out",
                            tinta=Paleta.POR_ROL[self.usuario.rol][0] if self.usuario else Paleta.AZUL)

    def _cerrar_sesion(self) -> None:
        self.usuario = None
        self.datos.cerrar_sesion()
        self.tutor_ia.olvidar_conversaciones()
        self._historial.clear()
        self.gestor.transition = FadeTransition(duration=0.25)
        self.gestor.current = "ingreso"

    def ir_a(self, nombre: str, **parametros) -> None:
        pantalla = self.gestor.get_screen(nombre)
        pantalla.preparar(**parametros)
        if self.gestor.current == nombre:
            pantalla.actualizar()
            return
        self._historial.append(self.gestor.current) # type: ignore
        self.gestor.transition = SlideTransition(direction="left", duration=0.22)
        self.gestor.current = nombre

    def volver(self) -> bool:
        if not self._historial:
            return False
        self.gestor.transition = SlideTransition(direction="right", duration=0.22)
        self.gestor.current = self._historial.pop()
        return True

    def abrir_leccion(self, tema_id: str, vista_previa: bool = False, nota: str = "") -> None:
        es_estudiante = self.usuario.rol == Rol.ESTUDIANTE and not vista_previa # type: ignore
        if not nota and not es_estudiante and self.usuario.rol == Rol.DOCENTE:  # type: ignore
            nota = "Vista previa del docente"
        self.ir_a("leccion", tema_id=tema_id, estudiante_id=self.usuario.id if es_estudiante else None, # type: ignore
                    vista_previa=not es_estudiante, nota_previa=nota)

    def abrir_chat_estudiante(self, tema_id: str | None) -> None:
        if not self.internet:
            self.notificador.mostrar("El tutor IA necesita internet.", "aviso")
            return
        tema = self.datos.tema(tema_id) if tema_id else None
        contexto = ContextoConversacion("estudiante", self.usuario, tema=tema, ficha=self.datos.ficha(self.usuario.id)) # type: ignore
        self.ir_a("chat", conversacion=self.tutor_ia.conversacion(contexto), titulo="Tutor IA",
                    subtitulo=tema.titulo if tema else "Pregunta libre")

    def abrir_chat_apoderado(self, estudiante_id: int, pregunta: str | None = None) -> None:
        if not self.internet:
            self.notificador.mostrar("El asistente necesita internet.", "aviso")
            return
        ficha = self.datos.ficha(estudiante_id)
        contexto = ContextoConversacion("apoderado", self.usuario, ficha=ficha, avisos=self.datos.avisos_apoderado(), # type: ignore
                                        nombres_asignaturas={a.id: a.nombre for a in self.datos.asignaturas()})
        self.ir_a("chat", conversacion=self.tutor_ia.conversacion(contexto), titulo="Asistente para familias",
                    subtitulo=f"Sobre {ficha.estudiante.primer_nombre}" if ficha else "", pregunta_inicial=pregunta)

    # ------------------------------------------------------------------
    # Estado de conexión (al tocar la pastilla "En línea / Sin conexión")
    # ------------------------------------------------------------------
    def mostrar_estado_conexion(self) -> None:
        monitor = self.monitor
        contenido = Columna(spacing=0)
        servidor_ok = monitor.servidor_ok and not monitor.forzado_sin_conexion
        contenido.add_widget(FilaLista("Servidor del colegio",
                                        f"{self.gestor_servidor.descripcion}: {'responde' if servidor_ok else 'no responde'}",
                                        inicio=InsigniaIcono("server", tinta=Paleta.VERDE if servidor_ok else Paleta.AMBAR,
                                                            lado=38)))
        contenido.add_widget(Separador())
        contenido.add_widget(FilaLista("Internet para el tutor IA", "Disponible" if self.internet else "No disponible",
                                        inicio=InsigniaIcono("bot", tinta=Paleta.VERDE if self.internet else Paleta.AMBAR,
                                                            lado=38)))
        contenido.add_widget(Separador())
        contenido.add_widget(FilaLista("Cambios por enviar",
                                        f"{self.pendientes} pendiente(s)" if self.pendientes else "Ninguno: todo al día",
                                        inicio=InsigniaIcono("refresh-cw", tinta=Paleta.AZUL, lado=38)))
        contenido.add_widget(Separador())
        interruptor = Interruptor(activo=monitor.forzado_sin_conexion, acento=Paleta.AMBAR)
        interruptor.bind(activo=lambda _w, valor: self._simular_sin_conexion(valor))
        contenido.add_widget(FilaLista("Simular sin conexión", "Para mostrar cómo funciona la app sin internet",
                                        inicio=InsigniaIcono("wifi-off", tinta=Paleta.AMBAR, lado=38), fin=interruptor))
        contenido.add_widget(Texto(self.gestor_servidor.diagnostico, tamano=12.5, color_texto=Paleta.TINTA_SUAVE))
        botones = [("Cerrar", None, "contorno")]
        if self.usuario is not None:
            botones.append(("Sincronizar", lambda: self.solicitar_sincronizacion(avisar=True), "primario")) # type: ignore
        Dialogo("Estado de la conexión", contenido=contenido, icono="wifi", botones=botones).open()

    def _simular_sin_conexion(self, valor: bool) -> None:
        self.monitor.forzar_sin_conexion(valor)
        if not valor:
            self.monitor.comprobar()
        self.notificador.mostrar("Modo sin conexión simulado activado." if valor else "Volviendo a conectar…",
                                    "aviso" if valor else "info")

    # ------------------------------------------------------------------
    def _tecla(self, _window, tecla, *_args) -> bool:
        """Botón "atrás" de Android (y tecla Esc en el computador)."""
        if tecla != 27:
            return False
        for widget in Window.children:
            if isinstance(widget, ModalView):
                widget.dismiss()
                return True
        if self.volver():
            return True
        if self.usuario is not None:
            self.cerrar_sesion()
            return True
        return False     # en la pantalla de ingreso, "atrás" cierra la app


if __name__ == "__main__":
    TutorEducaApp().run()

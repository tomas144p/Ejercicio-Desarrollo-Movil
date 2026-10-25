"""Inicio y cierre de sesión."""

from __future__ import annotations

from kivy.uix.screenmanager import FadeTransition

from views.dialogos import Dialogo
from views.estilo import Paleta


class SesionApp:
    """Parte de TutorEducaApp que maneja la sesión del usuario."""

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

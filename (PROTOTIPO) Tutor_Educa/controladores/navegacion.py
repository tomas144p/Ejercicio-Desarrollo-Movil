"""Navegación entre pantallas, historial y botón "atrás"."""

from __future__ import annotations

from kivy.core.window import Window
from kivy.uix.modalview import ModalView
from kivy.uix.screenmanager import SlideTransition

from models.modelos import Rol
from services.ia.conversacion import ContextoConversacion


class NavegacionApp:
    """Parte de TutorEducaApp que lleva al usuario de una pantalla a otra."""

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

"""
Recorre la app automáticamente y guarda capturas de cada pantalla en capturas/.

Sirve para documentar el prototipo y para revisar que nada se vea roto.
Usa una carpeta de datos temporal, así no toca tus datos.

    python herramientas/capturar_pantallas.py
    (en Linux sin pantalla:  xvfb-run -a python herramientas/capturar_pantallas.py)
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
TEMPORAL = Path(tempfile.mkdtemp())
os.environ["TUTOR_EDUCA_DATOS"] = str(TEMPORAL / "datos")

import main  # noqa: E402  (configura Kivy antes de crear la ventana)
from kivy.clock import Clock  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from kivy.uix.modalview import ModalView  # noqa: E402

CARPETA = RAIZ / "capturas"
CORREO = "@tutoreduca.cl"


class AppCapturas(main.TutorEducaApp):
    def build(self):
        raiz = super().build()
        self.pasos = self._guion()
        Clock.schedule_once(self._siguiente, 4)
        return raiz

    # --- utilidades -------------------------------------------------------
    def pantalla(self, nombre=None):
        return self.gestor.get_screen(nombre) if nombre else self.gestor.current_screen

    def cerrar_dialogos(self):
        for widget in list(Window.children):
            if isinstance(widget, ModalView):
                widget.dismiss(animation=False)

    def ingresar(self, usuario):
        self.cerrar_dialogos()
        if self.usuario is not None:
            self._cerrar_sesion()
        ingreso = self.pantalla("ingreso")
        ingreso.campo_correo.texto = usuario + CORREO
        ingreso.campo_clave.texto = "tutor2026"
        ingreso.ingresar()

    def responder_prueba(self, respuestas_malas=0):
        leccion = self.pantalla("leccion")
        leccion._comenzar()
        while not leccion.sesion.terminada:
            pregunta = leccion.sesion.actual
            correcta = pregunta.respuestas_aceptadas[0]
            if respuestas_malas > 0:
                respuestas_malas -= 1
                correcta = pregunta.alternativas[0] if pregunta.es_alternativas and pregunta.alternativas[0] != correcta else "0"
            leccion._resultado = leccion.sesion.responder(correcta)
            leccion._siguiente()

    def _guion(self):
        p = self.pantalla
        return [
            ("01_ingreso", None, 1.5),
            ("02_cuentas_de_prueba", lambda: p("ingreso")._cuentas_prueba(), 1.0),
            ("03_estudiante_inicio", lambda: self.ingresar("sofia.morales"), 4.0),
            ("04_estudiante_notas", lambda: p().cambiar_pestana("notas"), 1.0),
            ("05_estudiante_progreso", lambda: p().cambiar_pestana("progreso"), 1.0),
            ("06_estudiante_tutor", lambda: p().cambiar_pestana("tutor"), 1.0),
            ("07_leccion_aprende", lambda: self.abrir_leccion("mat-ecuaciones"), 1.2),
            ("08_leccion_ejemplos", lambda: p().cambiar_seccion("ejemplos"), 1.0),
            (None, lambda: (p().cambiar_seccion("prueba"), p()._comenzar()), 0.8),
            (None, lambda: setattr(p().campo, "texto", "x = 7"), 0.3),
            ("09_prueba_retroalimentacion", lambda: p()._comprobar(), 1.0),
            ("10_prueba_resultado", lambda: self.responder_prueba(respuestas_malas=1), 1.5),
            (None, lambda: self.abrir_chat_estudiante("mat-ecuaciones"), 1.0),
            (None, lambda: p().enviar("Dame un ejemplo"), 1.5),
            ("11_chat_tutor", lambda: p().enviar("Hazme una prueba"), 2.0),
            ("12_docente_curso", lambda: self.ingresar("carolina.fuentes"), 4.0),
            ("13_docente_temas", lambda: p().cambiar_pestana("temas"), 1.0),
            ("14_docente_desbloquear", lambda: p()._dialogo_desbloqueo(self.datos.tema("mat-potencias")), 1.0),
            ("15_docente_avisos", lambda: (self.cerrar_dialogos(), p().cambiar_pestana("avisos")), 1.0),
            ("16_ficha_estudiante", lambda: self.ir_a("ficha", estudiante_id=4), 1.5),
            ("17_apoderado_resumen", lambda: self.ingresar("andres.morales"), 4.0),
            ("18_apoderado_refuerzos", lambda: p().cambiar_pestana("refuerzos"), 1.0),
            ("19_apoderado_avisos", lambda: p().cambiar_pestana("avisos"), 1.0),
            ("20_chat_apoderado", lambda: self.abrir_chat_apoderado(2, "¿Cómo lo apoyo en casa?"), 2.5),
            ("21_estado_conexion", lambda: self.mostrar_estado_conexion(), 1.0),
            (None, lambda: (self.cerrar_dialogos(), self._simular_sin_conexion(True)), 1.0),
            ("22_ingreso_sin_conexion", lambda: self._cerrar_sesion(), 1.5),
            ("23_estudiante_sin_conexion", lambda: self.ingresar("sofia.morales"), 4.0),
        ]

    # --- motor del recorrido ------------------------------------------------
    def _siguiente(self, _dt=None):
        if not self.pasos:
            self.stop()
            return
        nombre, accion, espera = self.pasos.pop(0)
        try:
            if accion:
                accion()
        except Exception as error:  # se informa y se sigue con el resto
            import traceback
            traceback.print_exc()
            print(f"[capturas] Falló el paso {nombre}: {error}")
        Clock.schedule_once(lambda _dt: self._capturar(nombre), espera)

    def _capturar(self, nombre):
        if nombre:
            ruta = Window.screenshot(name=str(TEMPORAL / f"{nombre}.png"))
            if ruta:
                shutil.move(ruta, CARPETA / f"{nombre}.png")
                print(f"[capturas] {nombre}.png")
        Clock.schedule_once(self._siguiente, 0.1)


if __name__ == "__main__":
    CARPETA.mkdir(exist_ok=True)
    AppCapturas().run()
    shutil.rmtree(TEMPORAL, ignore_errors=True)

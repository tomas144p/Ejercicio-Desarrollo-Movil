"""Captura el selector de curso, el bloque «Para hoy» y las plantillas de aviso con una docente de dos cursos (xvfb-run -a python herramientas/capturar_selector_curso.py)."""
import sys, shutil
from pathlib import Path
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "herramientas"))
import capturar_pantallas as cp
from kivy.clock import Clock

class App2(cp.AppCapturas):
    def _guion(self):
        p = self.pantalla
        def segundo_curso():
            bd = self.datos.local.bd
            col = bd.consultar_uno("SELECT colegio_id FROM cursos WHERE id = 1")["colegio_id"]
            bd.ejecutar("INSERT INTO cursos (id, nombre, nivel, docente_id, anio, colegio_id) VALUES (2, '8° Básico A', '8° básico', ?, 2026, ?)",
                        (self.usuario.id, col))
            bd.ejecutar("UPDATE estudiantes SET curso_id = 2 WHERE usuario_id IN (5, 6, 7)")
            p().reiniciar(); p().actualizar()
        def desbloquear_sugerido():
            from services.acciones_docente import tema_sugerido
            sug = tema_sugerido(p().fichas, self.datos.temas())
            p()._dialogo_desbloqueo(self.datos.tema(sug.tema_id))
        def confirmar_dialogo():
            from kivy.core.window import Window
            from kivy.uix.modalview import ModalView
            self.cerrar_dialogos()
        return [
            ("A_login", lambda: self.ingresar("carolina.fuentes"), 4.0),
            ("B_selector", segundo_curso, 1.2),
            ("C_curso_elegido", lambda: p()._elegir_curso(1), 1.2),
            ("D_dialogo_sugerido", desbloquear_sugerido, 1.0),
            ("E_dialogo_plantillas", lambda: (self.cerrar_dialogos(), p()._dialogo_plantillas()), 1.0),
            ("F_aviso_con_plantilla", lambda: (self.cerrar_dialogos(), p()._usar_plantilla(
                __import__("services.acciones_docente", fromlist=["x"]).PLANTILLAS_AVISO[0], ir_a_avisos=True)), 1.2),
            ("G_selector_otra_vez", lambda: p()._cambiar_curso(), 1.0),
        ]

cp.CARPETA = RAIZ / "capturas" / "selector_curso"; cp.CARPETA.mkdir(exist_ok=True)
App2().run()

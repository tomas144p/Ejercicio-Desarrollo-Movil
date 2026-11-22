"""
Recorre la calculadora de notas (tarea 19) con la app real, sin abrir ventana, y guarda capturas en capturas/calculadora/.

    xvfb-run -a python herramientas/capturar_calculadora.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "herramientas"))
import capturar_pantallas as cp  # noqa: E402
from kivy.clock import Clock  # noqa: E402

cp.CARPETA = RAIZ / "capturas" / "calculadora"
cp.CARPETA.mkdir(parents=True, exist_ok=True)


class AppCalculadora(cp.AppCapturas):
    def _guion(self):
        p = self.pantalla

        def calc():
            return self.gestor.get_screen("calculadora")

        def escribir(campo, texto):
            campo.texto = texto

        def desplazar(valor):
            Clock.schedule_once(lambda _dt: setattr(calc()._scroll, "scroll_y", valor), 0.3)

        def datos_de_ejemplo():
            escribir(calc().c_obtenido, "42")
            escribir(calc().c_deseada, "5,0")
            escribir(calc().c_notas, "5,5 6,0 4,2")
            escribir(calc().c_faltan, "1")

        def errores():
            escribir(calc().c_obtenido, "99")
            escribir(calc().c_deseada, "8")
            escribir(calc().c_notas, "5,5 9,9")

        return [
            ("A_login_docente", lambda: self.ingresar("carolina.fuentes"), 4.0),
            (None, lambda: self.ir_a("calculadora", curso_id=1), 1.5),
            ("B_calculadora_vacia", lambda: None, 1.0),
            (None, datos_de_ejemplo, 0.8),
            ("C_con_datos", lambda: None, 1.0),
            ("D_abajo", lambda: desplazar(0.0), 1.0),
            ("E_errores", lambda: (errores(), desplazar(1.0)), 1.0),
            (None, lambda: (escribir(calc().c_obtenido, "42"), escribir(calc().c_deseada, "5,0"),
                            escribir(calc().c_notas, "5,5 6,0 4,2")), 0.5),
            ("F_tabla", lambda: calc()._abrir_tabla(), 1.2),
            (None, lambda: self.cerrar_dialogos(), 0.3),
            ("G_planilla", lambda: calc()._abrir_planilla(), 1.2),
            (None, lambda: self.cerrar_dialogos(), 0.3),
            ("H_apoderado", lambda: self.ingresar("andres.morales"), 4.0),
            (None, lambda: self.ir_a("calculadora"), 1.5),
            ("I_apoderado_calculadora", lambda: (escribir(calc().c_obtenido, "30")), 1.0),
        ]


if __name__ == "__main__":
    AppCalculadora().run()

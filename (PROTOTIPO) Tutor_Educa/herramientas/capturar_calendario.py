"""
Recorre el calendario (tareas 20 y 24) con la app real, sin abrir ventana, y guarda capturas en capturas/calendario/.

Comprueba de punta a punta: la pestaña Asistencia de la docente (pasar lista, sábado, eventos, alertas), la lista del
día con una inasistencia, el formulario de evento, y el calendario que ven la familia y el estudiante.

    xvfb-run -a python herramientas/capturar_calendario.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "herramientas"))
import capturar_pantallas as cp  # noqa: E402
from kivy.clock import Clock  # noqa: E402

from services import calendario  # noqa: E402

cp.CARPETA = RAIZ / "capturas" / "calendario"
cp.CARPETA.mkdir(parents=True, exist_ok=True)


class AppCalendario(cp.AppCapturas):
    def _guion(self):
        p = self.pantalla

        def desplazar(valor):
            Clock.schedule_once(lambda _dt: setattr(p()._scroll, "scroll_y", valor), 0.3)

        def pasar_lista_hoy():
            """Marca a Matías ausente y a Camila justificada con la misma función que usa el diálogo."""
            hoy = calendario.a_texto(self.datos.hoy())
            error = self.datos.pasar_lista(1, hoy, [9], [4])
            print(f"[lista] resultado: {error or 'ok'} | cola: {self.local.cantidad_pendientes()} cambio(s)")
            assert not error, error
            p().actualizar()

        def probar_reglas():
            """Domingo, feriado y futuro se rechazan en la app (el servidor los rechaza igual)."""
            hoy = self.datos.hoy()
            from datetime import timedelta
            domingo = hoy - timedelta(days=(hoy.weekday() + 1) % 7 or 7)
            for nombre, dia in (("domingo", domingo), ("mañana", hoy + timedelta(days=1)),
                                ("feriado 8 dic", None)):
                if dia is None:
                    continue
                print(f"[regla] {nombre} {dia}: {self.datos.pasar_lista(1, calendario.a_texto(dia), [], []) or 'SE ACEPTÓ (mal)'}")

        return [
            ("A_login_docente", lambda: self.ingresar("carolina.fuentes"), 4.0),
            ("B_asistencia_pestana", lambda: p().cambiar_pestana("asistencia"), 1.5),
            ("C_asistencia_abajo", lambda: desplazar(0.35), 1.0),
            ("D_asistencia_fin", lambda: desplazar(0.0), 1.0),
            ("E_lista_dialogo", lambda: (desplazar(1.0), p()._tarjeta_lista_de_hoy.__self__ and
                                         __import__("views.calendario_vista", fromlist=["x"]).abrir_lista_del_dia(
                                             self, p().curso, calendario.a_texto(self.datos.hoy()))), 1.2),
            (None, lambda: self.cerrar_dialogos(), 0.3),
            (None, pasar_lista_hoy, 0.8),
            ("F_lista_pasada", lambda: desplazar(1.0), 1.0),
            (None, probar_reglas, 0.2),
            ("G_evento_dialogo", lambda: __import__("views.calendario_vista", fromlist=["x"]).abrir_evento_nuevo(
                self, p().curso), 1.2),
            (None, lambda: self.cerrar_dialogos(), 0.3),
            ("H_ficha_matias", lambda: self.ir_a("ficha", estudiante_id=9), 1.5),
            ("I_apoderado", lambda: self.ingresar("andres.morales"), 4.0),
            ("J_apoderado_calendario", lambda: p().cambiar_pestana("calendario"), 1.5),
            ("K_apoderado_calendario_abajo", lambda: desplazar(0.0), 1.0),
            ("L_estudiante", lambda: self.ingresar("camila.perez"), 4.0),
            ("M_estudiante_calendario", lambda: p().cambiar_pestana("calendario"), 1.5),
        ]


if __name__ == "__main__":
    AppCalendario().run()

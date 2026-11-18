"""
Recorre las métricas de la tarea 22 con la app real (sin abrir ventana) y guarda capturas en capturas/metricas/.

Comprueba de punta a punta: la tarjeta de efecto en «Mi curso», en la ficha y en la vista del apoderado; la
exportación a CSV; y que un error simulado dentro de la app se registra (sin datos personales) y la app SIGUE
funcionando.

    xvfb-run -a python herramientas/capturar_metricas.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "herramientas"))
import capturar_pantallas as cp  # noqa: E402
from kivy.clock import Clock  # noqa: E402

cp.CARPETA = RAIZ / "capturas" / "metricas"
cp.CARPETA.mkdir(parents=True, exist_ok=True)


class AppMetricas(cp.AppCapturas):
    def _guion(self):
        p = self.pantalla

        def desplazar(valor):
            Clock.schedule_once(lambda _dt: setattr(p()._scroll, "scroll_y", valor), 0.3)

        def exportar():
            self.cerrar_dialogos()
            p()._exportar(True)
            carpeta = Path(self.user_data_dir) / "exportaciones"
            for archivo in sorted(carpeta.glob("*.csv")):
                print(f"[csv] {archivo.name}")
                print(archivo.read_text(encoding="utf-8").replace("\r\n", "\n"))
                (cp.CARPETA / "ejemplo_metricas_anonimo.csv").write_bytes(archivo.read_bytes())

        def error_simulado():
            self.cerrar_dialogos()
            antes = self.local.cantidad_pendientes()
            Clock.schedule_once(lambda _dt: {}["Sofía Pérez, sofia@colegio.cl"], 0)     # un error dentro de la app
            self._antes = antes

        def verificar_error():
            filas = [f for f in self.local.pendientes() if f["tipo"] == "error_app"]
            print(f"[error] errores en la cola: {len(filas)} | cambios pendientes que ve la persona: "
                  f"{self.local.cantidad_pendientes()} (antes {self._antes})")
            for fila in filas:
                print("[error]", fila["datos"])
            assert filas, "el error no se registró"
            assert "sofia@colegio.cl" not in filas[-1]["datos"] and "Sofía Pérez" not in filas[-1]["datos"]
            assert self.gestor.current == "docente", "la app debería seguir en la pantalla del docente"

        return [
            ("A_login_docente", lambda: self.ingresar("carolina.fuentes"), 4.0),
            ("B_mi_curso_efecto", lambda: desplazar(0.55), 1.0),
            ("C_dialogo_exportar", lambda: p()._dialogo_exportar(), 1.0),
            ("D_exportado", exportar, 1.2),
            ("E_ficha_con_efecto", lambda: (self.cerrar_dialogos(), self.ir_a("ficha", estudiante_id=4)), 1.5),
            ("F_ficha_efecto_arriba", lambda: desplazar(0.72), 1.0),
            ("G_apoderado", lambda: self.ingresar("rodrigo.perez"), 3.0),
            ("H_apoderado_efecto", lambda: desplazar(0.62), 1.0),
            ("I_vuelve_docente", lambda: self.ingresar("carolina.fuentes"), 3.0),
            ("J_error_simulado", error_simulado, 1.2),
            (None, verificar_error, 0.1),
        ]


if __name__ == "__main__":
    AppMetricas().run()

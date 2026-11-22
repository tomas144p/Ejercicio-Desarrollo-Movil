"""
Recorre, con la app real, el flujo de activar cuentas y gestionar estudiantes, y guarda capturas en capturas/gestion/.

Necesita un backend corriendo (por ejemplo `python -m backend`, que usa la base de demostración):

    python -m backend                                                    (en otra consola)
    python herramientas/capturar_gestion.py --url http://127.0.0.1:8000
    (en Linux sin pantalla:  xvfb-run -a python herramientas/capturar_gestion.py --url ...)

Qué hace, paso a paso, con los diálogos reales:
  la docente agrega un estudiante con un apoderado nuevo -> aparecen sus códigos -> el apoderado activa su cuenta con el
  código desde la pantalla de ingreso y ve a su hijo -> la docente da de baja al estudiante, lo ve en «Dados de baja» y
  lo reactiva.

Usa una carpeta de datos temporal para el teléfono; las cuentas de prueba que crea quedan en el servidor (con un sufijo).
"""

from __future__ import annotations

import argparse
import os
import secrets
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
_analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
_analizador.add_argument("--url", default="http://127.0.0.1:8000", help="dirección del backend")
ARGUMENTOS, _ = _analizador.parse_known_args()
os.environ["KIVY_NO_ARGS"] = "1"        # Kivy no debe intentar interpretar --url
TEMPORAL = Path(tempfile.mkdtemp())
os.environ["TUTOR_EDUCA_DATOS"] = str(TEMPORAL / "datos")
os.environ["TUTOR_EDUCA_SERVIDOR_URL"] = ARGUMENTOS.url

import main  # noqa: E402  (configura Kivy antes de crear la ventana)
from kivy.clock import Clock  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from kivy.uix.modalview import ModalView  # noqa: E402

import views.gestion_dialogos as gestion_dialogos  # noqa: E402
from views.componentes import Boton, CampoTexto  # noqa: E402

CARPETA = RAIZ / "capturas" / "gestion"
SUFIJO = secrets.token_hex(2)
ESTUDIANTE = f"luis.{SUFIJO}@correo.cl"
APODERADO = f"rosa.{SUFIJO}@correo.cl"
CLAVE_NUEVA = "Clave-larga-2026"


class AppGestion(main.TutorEducaApp):
    def build(self):
        raiz = super().build()
        self.codigos = {}
        self._original = gestion_dialogos.mostrar_codigos

        def espiar(app, resultado, titulo):          # guarda los códigos para el paso de activación
            for codigo in resultado.codigos:
                self.codigos[codigo.rol] = codigo.codigo
            return self._original(app, resultado, titulo)
        gestion_dialogos.mostrar_codigos = espiar
        self.pasos = self._guion()
        Clock.schedule_once(self._siguiente, 4)
        return raiz

    # --- utilidades -------------------------------------------------------
    def pantalla(self, nombre=None):
        return self.gestor.get_screen(nombre) if nombre else self.gestor.current_screen

    def dialogo(self):
        modales = [w for w in Window.children if isinstance(w, ModalView)]
        return modales[0] if modales else None

    def cerrar_dialogos(self):
        for widget in list(Window.children):
            if isinstance(widget, ModalView):
                widget.dismiss(animation=False)

    def campos(self):
        return [w for w in self.dialogo().walk(restrict=False) if isinstance(w, CampoTexto)]

    def pulsar(self, texto):
        for w in self.dialogo().walk(restrict=False):
            if isinstance(w, Boton) and w.texto_base == texto:
                w.dispatch("on_release")
                return
        raise RuntimeError(f"No hay un botón «{texto}» en el diálogo")

    def llenar(self, *valores):
        for campo, valor in zip(self.campos(), valores):
            campo.texto = valor

    def ingresar_docente(self):
        self.cerrar_dialogos()
        if self.usuario is not None:
            self._cerrar_sesion()
        ingreso = self.pantalla("ingreso")
        ingreso.campo_correo.texto = "carolina.fuentes@tutoreduca.cl"
        ingreso.campo_clave.texto = "tutor2026"
        ingreso.ingresar()

    def cerrar_sesion(self):
        self.cerrar_dialogos()
        self._cerrar_sesion()

    def abrir_ficha_del_nuevo(self):
        pantalla = self.pantalla("docente")
        ficha = [f for f in pantalla.fichas if f.estudiante.correo == ESTUDIANTE][0]
        self.ir_a("ficha", estudiante_id=ficha.estudiante.id)

    def _guion(self):
        p = self.pantalla
        return [
            ("g01_ingreso_con_boton_de_codigo", None, 1.5),
            ("g02_activar_cuenta_vacio", lambda: p("ingreso")._activar_cuenta(), 1.0),
            (None, lambda: self.ingresar_docente(), 4.0),
            ("g03_docente_mi_curso", None, 0.5),
            (None, lambda: gestion_dialogos.abrir_estudiante_nuevo(self, p("docente").curso), 1.0),
            ("g04_agregar_estudiante_lleno",
             lambda: self.llenar("Luis Pérez", ESTUDIANTE, APODERADO, "Rosa Pérez"), 1.0),
            (None, lambda: self.pulsar("Agregar"), 3.5),
            ("g05_codigos_para_entregar", None, 0.5),
            (None, lambda: (self.cerrar_dialogos(), self.cerrar_sesion()), 1.5),
            (None, lambda: p("ingreso")._activar_cuenta(), 1.0),
            ("g06_activacion_con_codigo",
             lambda: self.llenar(APODERADO, self.codigos["apoderado"], CLAVE_NUEVA, CLAVE_NUEVA), 1.0),
            (None, lambda: self.pulsar("Activar y entrar"), 4.5),
            ("g07_apoderado_ya_dentro_ve_a_su_hijo", None, 0.5),
            (None, lambda: self.ingresar_docente(), 4.0),
            (None, lambda: self.abrir_ficha_del_nuevo(), 1.5),
            ("g08_ficha_con_gestionar_cuenta", None, 0.3),
            (None, lambda: gestion_dialogos.abrir_gestion_estudiante(self, self.pantalla("ficha").ficha), 1.0),
            ("g09_menu_gestionar_estudiante", None, 0.3),
            (None, lambda: (self.cerrar_dialogos(), gestion_dialogos._confirmar_baja(self, self.pantalla("ficha").ficha)), 1.0),
            ("g10_confirmar_baja", None, 0.3),
            (None, lambda: self.pulsar("Dar de baja"), 3.5),
            ("g11_mi_curso_despues_de_la_baja", None, 0.3),
            (None, lambda: gestion_dialogos.abrir_bajas(self), 2.5),
            ("g12_estudiantes_dados_de_baja", None, 0.3),
            (None, lambda: self.pulsar_reactivar(), 3.5),
            ("g13_mi_curso_tras_reactivar", None, 0.3),
        ]

    def pulsar_reactivar(self):
        for w in self.dialogo().walk(restrict=False):
            if isinstance(w, Boton) and w.texto_base == "Reactivar":
                w.dispatch("on_release")
                return
        raise RuntimeError("No hay estudiantes dados de baja para reactivar")

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
    CARPETA.mkdir(parents=True, exist_ok=True)
    AppGestion().run()
    shutil.rmtree(TEMPORAL, ignore_errors=True)

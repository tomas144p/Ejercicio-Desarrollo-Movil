"""Tutor Educa: punto de entrada. Solo arma la app (views/, services/, models/)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from views.ventana import configurar_ventana
configurar_ventana()  # va ANTES de importar el resto de Kivy

from kivymd.app import MDApp
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from controladores import ConexionApp, ConstruccionApp, NavegacionApp, SesionApp


class TutorEducaApp(ConstruccionApp, ConexionApp, SesionApp, NavegacionApp, MDApp):
    en_linea = BooleanProperty(False)            # el servidor del colegio responde
    internet = BooleanProperty(False)            # hay internet para el tutor IA
    sincronizando = BooleanProperty(False)
    conexion_revisada = BooleanProperty(False)   # ya se hizo la primera revisión
    pendientes = NumericProperty(0)              # cambios guardados que faltan por enviar
    descripcion_servidor = StringProperty("")


if __name__ == "__main__":
    TutorEducaApp().run()

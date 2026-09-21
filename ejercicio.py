#Uno de sus botones existentes ahora abre un MDDialog de confirmación (no de alerta) antes de ejecutar la acción.
# Agregar un MDTextField relacionado con su problema real (ej. buscar algo, ingresar un dato).
# Agregar un MDDropdownMenu con al menos 2-3 opciones reales de su proyecto (no “Opción 1 / Opción 2” genéricos)

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.dialog import (
    MDDialog,
    MDDialogHeadlineText,
    MDDialogSupportingText,
    MDDialogButtonContainer
)
from kivymd.uix.textfield import MDTextField, MDTextFieldHintText
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.boxlayout import MDBoxLayout

class MiApp(MDApp):
    def build(self):
# Uno de sus botones existentes ahora abre un MDDialog de confirmación (no de alerta) antes de ejecutar la acción.
# Agregar un MDTextField relacionado con su problema real (ej. buscar algo, ingresar un dato).
# Agregar un MDDropdownMenu con al menos 2-3 opciones reales de su proyecto (no “Opción 1 / Opción 2” genéricos)

# Proto Primitivo *

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
from kivymd.uix.label import MDLabel
from kivy.core.window import Window

Window.clearcolor = (1, 1, 1, 1)

class MiApp(MDApp):
    def build(self):
        self.dialogo = None
        self.menu = None
        self.tema = ""

        pantalla = MDScreen()

        caja = MDBoxLayout(
            orientation="vertical",
            padding="24dp",
            spacing="12dp"
        )

        titulo = MDLabel(
            text="Tutor Híbrido Matemático",
            halign="center",
            font_style="Headline",
            role="small",
            adaptive_height=True
        )

        # Campo de texto: Estudiante
        self.campo_nombre = MDTextField(
            MDTextFieldHintText(text="Nombre Estudiante"),
            mode="outlined"
        )

        # Botón menú con temas
        self.texto_boton_tema = MDButtonText(text="Tema: No Asignado")
        self.boton_tema = MDButton(
            self.texto_boton_tema,
            style="outlined",
            on_release=self.abrir_menu
        )

        # Botón confirmación
        boton_asignar = MDButton(
            MDButtonText(text="Asignar práctica"),
            style="filled",
            on_release=self.abrir_confirmacion
        )

        self.resultado = MDLabel(
            text="",
            halign="center",
            adaptive_height=True
        )

        caja.add_widget(titulo)
        caja.add_widget(self.campo_nombre)
        caja.add_widget(self.boton_tema)
        caja.add_widget(boton_asignar)
        caja.add_widget(self.resultado)
        caja.add_widget(MDBoxLayout())  # espacio vacío para empujar todo hacia arriba

        pantalla.add_widget(caja)
        return pantalla

    # Menú
    def abrir_menu(self, boton):
        temas = ["Fracciones", "Geometría", "Ecuaciones", "Literatura"]
        opciones = []
        for t in temas:
            opciones.append({
                "text": t,
                "on_release": lambda x=t: self.elegir_tema(x)
            })

        self.menu = MDDropdownMenu(caller=self.boton_tema, items=opciones)
        self.menu.open()

    def elegir_tema(self, tema):
        self.tema = tema
        self.texto_boton_tema.text = "Tema: " + tema
        self.menu.dismiss()  # type: ignore

    # Confirmación
    def abrir_confirmacion(self, boton):
        nombre = self.campo_nombre.text.strip()
        if nombre == "":
            nombre = "Estudiante"

        self.dialogo = MDDialog(
            MDDialogHeadlineText(text="Confirmar práctica"),
            MDDialogSupportingText(
                text="¿Desea asignar práctica de " + self.tema + " a " + nombre + "?"
            ),
            MDDialogButtonContainer(
                MDButton(
                    MDButtonText(text="Cancelar"),
                    style="text",
                    on_release=self.cerrar_dialogo
                ),
                MDButton(
                    MDButtonText(text="Confirmar"),
                    style="text",
                    on_release=self.confirmar
                ),
                spacing="8dp"
            )
        )
        self.dialogo.open()

    def cerrar_dialogo(self, boton):
        self.dialogo.dismiss()  # type: ignore

    def confirmar(self, boton):
        nombre = self.campo_nombre.text.strip()
        if nombre == "":
            nombre = "Estudiante"
        self.resultado.text = "Práctica de " + self.tema + " asignada a " + nombre
        self.dialogo.dismiss()  # type: ignore

MiApp().run()
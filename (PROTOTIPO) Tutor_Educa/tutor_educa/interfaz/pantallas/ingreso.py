"""
Pantalla de ingreso.

El correo define el perfil: no hay botones "entrar como estudiante/docente".
La app busca el correo en el servidor y abre la pantalla del rol guardado.
"""

from __future__ import annotations

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.widget import Widget

from ...contenido.datos_iniciales import DatosIniciales
from ...modelos import Rol
from ..componentes import (Avatar, Boton, BotonIcono, CampoTexto, Casilla, Chip, Columna, ConCuadricula, Espacio,
                           Fila, FilaLista, Icono, InsigniaIcono, Superficie, Texto, TextoDestacado)
from ..dialogos import Dialogo
from ..estilo import Paleta, Tipografia
from .base import FondoPapel, PantallaBase, crear_desplazable


class Portada(ConCuadricula, BoxLayout):
    """Encabezado con papel cuadriculado y una ecuación "escrita a mano"."""

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, padding=(dp(22), dp(30), dp(22), dp(18)),
                         spacing=dp(8), **kwargs)
        self.bind(minimum_height=self.setter("height"))
        marca = Fila(spacing=dp(12))
        marca.add_widget(InsigniaIcono("graduation-cap", tinta="#FFFFFF", fondo=Paleta.AZUL, lado=46,
                                       tamano_icono=24, pos_hint={"center_y": 0.5}))
        marca.add_widget(Texto("Tutor Educa", tamano=27, fuente=Tipografia.NEGRITA, pos_hint={"center_y": 0.5}))
        self.add_widget(marca)
        self.add_widget(Texto("Refuerzo de matemáticas para 5° a 8° básico, con o sin internet.",
                              tamano=14, color_texto=Paleta.TINTA_SUAVE))
        self.add_widget(Espacio(6))
        self.add_widget(Texto("3x − 5 = 10", tamano=25, fuente=Tipografia.CUADERNO,
                              color_texto=Paleta.TINTA_CUADERNO, cuaderno=True))
        fila = Fila()
        self.resultado = TextoDestacado("x = 5", tamano=25)
        self.resultado.avance = 0
        fila.add_widget(self.resultado)
        fila.add_widget(Widget(size_hint_y=None, height=dp(1)))
        self.add_widget(fila)

    def animar(self) -> None:
        """El destacador "pinta" el resultado, como se hace en el cuaderno."""
        self.resultado.avance = 0
        Animation(avance=1, d=0.7, t="out_cubic").start(self.resultado)


class LineaEstado(ButtonBehavior, Fila):
    pass


class PantallaIngreso(PantallaBase):
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        raiz = FondoPapel()
        scroll, columna = crear_desplazable(padding=(0, 0, 0, dp(24)), spacing=0)
        raiz.add_widget(scroll)
        self.add_widget(raiz)

        self.portada = Portada()
        columna.add_widget(self.portada)
        cuerpo = Columna(padding=(dp(16), 0, dp(16), 0), spacing=dp(14))
        columna.add_widget(cuerpo)

        tarjeta = Superficie(padding=dp(20), spacing=dp(12), radio=dp(20))
        tarjeta.add_widget(Texto("Ingresa con tu correo", tamano=19, fuente=Tipografia.SEMI))
        tarjeta.add_widget(Texto("Tu correo define tu perfil: estudiante, docente o apoderado.",
                                 tamano=13, color_texto=Paleta.TINTA_SUAVE))
        self.campo_correo = CampoTexto("nombre@tutoreduca.cl", icono="mail", al_confirmar=self._enfocar_clave)
        self.campo_correo.entrada.input_type = "mail"
        self.campo_clave = CampoTexto("Contraseña", icono="lock", clave=True, al_confirmar=self.ingresar)
        self.casilla = Casilla("Recordarme en este dispositivo para poder entrar sin conexión", activa=True)
        self.error = Texto("", tamano=13.5, color_texto=Paleta.ROJO)
        self.boton = Boton("Ingresar", icono="log-in", al_presionar=self.ingresar)
        for widget in (self.campo_correo, self.campo_clave, self.casilla, self.error, self.boton):
            tarjeta.add_widget(widget)
        cuerpo.add_widget(tarjeta)

        self.zona_recordados = Columna(spacing=dp(8))
        cuerpo.add_widget(self.zona_recordados)

        self.linea_estado = LineaEstado(spacing=dp(8), padding=(dp(4), dp(4)))
        self.icono_estado = Icono("clock", tamano=16, color_icono=Paleta.TINTA_SUAVE, pos_hint={"center_y": 0.5})
        self.texto_estado = Texto("", tamano=12.5, color_texto=Paleta.TINTA_SUAVE, pos_hint={"center_y": 0.5})
        self.linea_estado.add_widget(self.icono_estado)
        self.linea_estado.add_widget(self.texto_estado)
        self.linea_estado.bind(on_release=lambda *_: self.app.mostrar_estado_conexion())
        cuerpo.add_widget(self.linea_estado)
        cuerpo.add_widget(Boton("Ver cuentas de prueba", icono="users", variante="fantasma",
                                al_presionar=self._cuentas_prueba))
        app.bind(en_linea=self._estado_servidor, conexion_revisada=self._estado_servidor,
                 descripcion_servidor=self._estado_servidor)

    # ------------------------------------------------------------------
    def actualizar(self) -> None:
        self.error.cambiar("")
        self.boton.cargando = False
        self._estado_servidor()
        self._dibujar_recordados()
        Clock.schedule_once(lambda _dt: self.portada.animar(), 0.35)

    def _estado_servidor(self, *_):
        app = self.app
        if not app.conexion_revisada:
            icono, texto, tinta = "clock", "Buscando el servidor del colegio…", Paleta.TINTA_SUAVE
        elif app.en_linea:
            icono, tinta = "server", Paleta.VERDE
            texto = f"Conectado: {app.descripcion_servidor}. Toca para ver detalles."
        else:
            icono, tinta = "wifi-off", Paleta.AMBAR
            texto = "Sin conexión con el servidor: solo pueden entrar las cuentas guardadas en este dispositivo."
        self.icono_estado.cambiar(icono)
        from ..estilo import color
        self.icono_estado.color = self.texto_estado.color = color(tinta)
        self.texto_estado.cambiar(texto)

    def _dibujar_recordados(self):
        self.zona_recordados.clear_widgets()
        recordados = self.app.autenticacion.recordados()
        if not recordados:
            return
        cabecera = Fila()
        cabecera.add_widget(Texto("Cuentas guardadas en este dispositivo", tamano=13.5, fuente=Tipografia.MEDIA,
                                  color_texto=Paleta.TINTA_SUAVE, pos_hint={"center_y": 0.5}))
        cabecera.add_widget(Boton("Gestionar", variante="fantasma", alto=32, tamano=13, size_hint_x=None,
                                  width=dp(96), al_presionar=self._gestionar_recordados, pos_hint={"center_y": 0.5}))
        self.zona_recordados.add_widget(cabecera)
        chips = StackLayout(orientation="lr-tb", size_hint_y=None, spacing=dp(8))
        chips.bind(minimum_height=chips.setter("height"))
        for cuenta in recordados:
            tinta = Paleta.POR_ROL.get(cuenta["rol"], (Paleta.AZUL,))[0]
            texto = f"{cuenta['nombre'].split()[0]} ({Rol.NOMBRES.get(cuenta['rol'], '').lower()})"
            chips.add_widget(Chip(texto, icono="user-round", acento=tinta,
                                  al_presionar=lambda correo=cuenta["correo"]: self._usar_cuenta(correo)))
        self.zona_recordados.add_widget(chips)

    def _usar_cuenta(self, correo: str, clave: str = "") -> None:
        self.campo_correo.texto = correo
        self.campo_clave.texto = clave
        self.error.cambiar("")
        if not clave:
            Clock.schedule_once(lambda _dt: setattr(self.campo_clave.entrada, "focus", True), 0.1)

    def _enfocar_clave(self):
        self.campo_clave.entrada.focus = True

    # ------------------------------------------------------------------
    def ingresar(self) -> None:
        if self.boton.cargando:
            return
        correo, clave, recordar = self.campo_correo.texto, self.campo_clave.texto, self.casilla.activa
        self.error.cambiar("")
        self.boton.cargando = True
        self.app.ejecutor_datos.enviar(lambda: self.app.autenticacion.ingresar(correo, clave, recordar),
                                       self._al_ingresar, self._al_fallar)

    def _al_ingresar(self, resultado) -> None:
        self.boton.cargando = False
        if resultado.exito:
            self.campo_clave.texto = ""
            self.app.iniciar_sesion(resultado)
        else:
            self.error.cambiar(resultado.mensaje)

    def _al_fallar(self, error) -> None:
        self.boton.cargando = False
        self.error.cambiar(f"Ocurrió un problema inesperado: {error}")

    # ------------------------------------------------------------------
    def _cuentas_prueba(self) -> None:
        contenido = Columna(spacing=0)
        dialogo = None

        def elegir(cuenta):
            self._usar_cuenta(cuenta["correo"], DatosIniciales.CLAVE_DEMO)
            dialogo.dismiss()

        for cuenta in DatosIniciales().cuentas_demo():
            tinta = Paleta.POR_ROL[cuenta["rol"]][0]
            iniciales = "".join(p[0] for p in cuenta["nombre"].split()[:2])
            contenido.add_widget(FilaLista(cuenta["nombre"], f"{cuenta['detalle']}\n{cuenta['correo']}",
                                           inicio=Avatar(iniciales, tinta=tinta, lado=38),
                                           al_presionar=lambda c=cuenta: elegir(c)))
        dialogo = Dialogo("Cuentas de prueba", "Toca una cuenta para completar el formulario. Todas usan la "
                          f"contraseña {DatosIniciales.CLAVE_DEMO}.", contenido=contenido, icono="users",
                          botones=[("Cerrar", None, "contorno")])
        dialogo.open()

    def _gestionar_recordados(self) -> None:
        contenido = Columna(spacing=0)
        dialogo = None

        def olvidar(correo):
            self.app.autenticacion.olvidar(correo)
            dialogo.dismiss()
            self._dibujar_recordados()
            self.app.notificador.mostrar("La cuenta ya no se podrá usar sin conexión en este dispositivo.")

        for cuenta in self.app.autenticacion.recordados():
            tinta = Paleta.POR_ROL.get(cuenta["rol"], (Paleta.AZUL,))[0]
            iniciales = "".join(p[0] for p in cuenta["nombre"].split()[:2])
            contenido.add_widget(FilaLista(cuenta["nombre"], cuenta["correo"], inicio=Avatar(iniciales, tinta=tinta, lado=38),
                                           fin=BotonIcono("trash-2", tinta=Paleta.ROJO, lado=40, tamano=18,
                                                          al_presionar=lambda c=cuenta["correo"]: olvidar(c))))
        dialogo = Dialogo("Cuentas guardadas", "Estas cuentas pueden ingresar sin conexión porque marcaron "
                          "«Recordarme». La contraseña se guarda cifrada. Toca el basurero para olvidar una.",
                          contenido=contenido, icono="shield-check", botones=[("Cerrar", None, "contorno")])
        dialogo.open()

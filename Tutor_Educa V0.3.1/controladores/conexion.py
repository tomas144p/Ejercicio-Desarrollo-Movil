"""Conexión con el servidor y sincronización de los cambios guardados."""

from __future__ import annotations

from functools import partial

from kivy.clock import Clock

from views.componentes import Columna, FilaLista, InsigniaIcono, Interruptor, Separador, Texto
from views.dialogos import Dialogo
from views.estilo import Paleta


class ConexionApp:
    """Parte de TutorEducaApp que revisa la conexión y sincroniza."""

    def _servidor_listo(self, _gestor) -> None:
        self.descripcion_servidor = self.gestor_servidor.descripcion
        print(f"[servidor] {self.gestor_servidor.diagnostico}")
        self.monitor.comprobar()

    def _conexion_cambio(self, monitor) -> None:
        antes = (self.en_linea, self.internet)
        self.en_linea, self.internet = monitor.en_linea, monitor.internet_disponible
        self.conexion_revisada = monitor.comprobado or monitor.forzado_sin_conexion
        self.descripcion_servidor = self.gestor_servidor.descripcion
        if self.en_linea and self.usuario is not None and (self.pendientes or not antes[0]):
            self.solicitar_sincronizacion()
        if antes != (self.en_linea, self.internet):
            self._refrescar_pantalla()

    def _hubo_cambios(self) -> None:
        """El usuario guardó algo: se intenta enviar de inmediato."""
        self.pendientes = self.local.cantidad_pendientes()
        self.solicitar_sincronizacion()

    def solicitar_sincronizacion(self, avisar: bool = False) -> None:
        if self.usuario is None or not self.en_linea:
            if avisar:
                self.notificador.mostrar("Sin conexión con el servidor: los cambios quedan guardados.", "aviso")
            return
        if self.sincronizando:
            self._sincronizar_de_nuevo = True
            return
        self.sincronizando = True
        usuario = self.usuario
        self.ejecutor_datos.enviar(lambda: self.sincronizacion.sincronizar(usuario),
                                    partial(self._sincronizado, usuario, avisar), self._fallo_sincronizacion)

    def _sincronizado(self, usuario, avisar: bool, resultado) -> None:
        self.sincronizando = False
        self.pendientes = self.local.cantidad_pendientes()
        if resultado.sin_conexion:
            self.monitor.comprobar()
        if usuario is self.usuario and resultado.descargado:
            self.datos.invalidar()
            self._refrescar_pantalla()
        if avisar:
            tipo = "aviso" if resultado.sin_conexion else "exito"
            self.notificador.mostrar(resultado.mensaje, tipo)
        if self._sincronizar_de_nuevo or (not resultado.descargado and not resultado.sin_conexion):
            self._sincronizar_de_nuevo = False
            Clock.schedule_once(lambda _dt: self.solicitar_sincronizacion(), 1.5)

    def _fallo_sincronizacion(self, error) -> None:
        self.sincronizando = False
        self.notificador.mostrar(f"No se pudo sincronizar: {error}", "error")

    def _refrescar_pantalla(self) -> None:
        pantalla = self.gestor.current_screen
        if pantalla is not None and (self.usuario is not None or pantalla.name == "ingreso"):
            pantalla.al_cambiar_datos()

    def mostrar_estado_conexion(self) -> None:
        monitor = self.monitor
        contenido = Columna(spacing=0)
        servidor_ok = monitor.servidor_ok and not monitor.forzado_sin_conexion
        contenido.add_widget(FilaLista("Servidor del colegio",
                                        f"{self.gestor_servidor.descripcion}: {'responde' if servidor_ok else 'no responde'}",
                                        inicio=InsigniaIcono("server", tinta=Paleta.VERDE if servidor_ok else Paleta.AMBAR,
                                                            lado=38)))
        contenido.add_widget(Separador())
        contenido.add_widget(FilaLista("Internet para el tutor IA", "Disponible" if self.internet else "No disponible",
                                        inicio=InsigniaIcono("bot", tinta=Paleta.VERDE if self.internet else Paleta.AMBAR,
                                                            lado=38)))
        contenido.add_widget(Separador())
        contenido.add_widget(FilaLista("Cambios por enviar",
                                        f"{self.pendientes} pendiente(s)" if self.pendientes else "Ninguno: todo al día",
                                        inicio=InsigniaIcono("refresh-cw", tinta=Paleta.AZUL, lado=38)))
        contenido.add_widget(Separador())
        interruptor = Interruptor(activo=monitor.forzado_sin_conexion, acento=Paleta.AMBAR)
        interruptor.bind(activo=lambda _w, valor: self._simular_sin_conexion(valor))
        contenido.add_widget(FilaLista("Simular sin conexión", "Para mostrar cómo funciona la app sin internet",
                                        inicio=InsigniaIcono("wifi-off", tinta=Paleta.AMBAR, lado=38), fin=interruptor))
        contenido.add_widget(Texto(self.gestor_servidor.diagnostico, tamano=12.5, color_texto=Paleta.TINTA_SUAVE))
        botones = [("Cerrar", None, "contorno")]
        if self.usuario is not None:
            botones.append(("Sincronizar", lambda: self.solicitar_sincronizacion(avisar=True), "primario")) # type: ignore
        Dialogo("Estado de la conexión", contenido=contenido, icono="wifi", botones=botones).open()

    def _simular_sin_conexion(self, valor: bool) -> None:
        self.monitor.forzar_sin_conexion(valor)
        if not valor:
            self.monitor.comprobar()
        self.notificador.mostrar("Modo sin conexión simulado activado." if valor else "Volviendo a conectar…",
                                    "aviso" if valor else "info")

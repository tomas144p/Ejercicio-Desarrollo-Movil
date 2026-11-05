"""
Sincronización entre el teléfono y el servidor.

Funciona como una "bandeja de salida":

1. Cada cambio hecho en el teléfono (un intento de prueba, un tema
   desbloqueado, un aviso) se guarda primero en la base local y en la cola.
2. Cuando hay conexión, se envía la cola al servidor, en orden.
3. Después se descarga la versión actualizada de los datos del usuario.

Si no hay conexión no se pierde nada: la cola espera hasta la próxima vez.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from ..datos.conexiones import ErrorConexion


@dataclass
class ResultadoSincronizacion:
    enviados: int = 0
    fallidos: int = 0
    descargado: bool = False
    sin_conexion: bool = False
    mensaje: str = ""


class ServicioSincronizacion:
    """Sube la cola de cambios y descarga los datos del usuario."""

    MAX_INTENTOS = 5   # un cambio que falla 5 veces se descarta (queda registrado en consola)

    def __init__(self, local, gestor_servidor):
        self.local = local
        self.gestor_servidor = gestor_servidor

    def sincronizar(self, usuario) -> ResultadoSincronizacion:
        """Operación bloqueante: se debe llamar desde un hilo en segundo plano."""
        servidor = self.gestor_servidor.servidor
        if servidor is None or not servidor.probar():
            return ResultadoSincronizacion(sin_conexion=True, mensaje="Sin conexión con el servidor.")
        try:
            enviados, fallidos = self._subir(servidor)
            ultimo = self.local.ultimo_id_cola()
            descargado = False
            if usuario is not None:
                paquete = servidor.paquete_para(usuario)
                descargado = self.local.aplicar_paquete(paquete, ultimo)
        except ErrorConexion as error:
            return ResultadoSincronizacion(sin_conexion=True, mensaje=str(error))
        mensaje = f"{enviados} cambio(s) enviado(s)." if enviados else "Datos al día."
        return ResultadoSincronizacion(enviados, fallidos, descargado, False, mensaje)

    def _subir(self, servidor) -> tuple[int, int]:
        enviados = fallidos = 0
        for item in self.local.pendientes():
            try:
                servidor.aplicar_cambio(item["tipo"], json.loads(item["datos"]))
            except ErrorConexion:
                raise   # sin conexión: se detiene todo y se reintenta después
            except Exception as error:
                fallidos += 1
                print(f"[sincronización] No se pudo enviar {item['tipo']}: {error}")
                self.local.registrar_error_cola(item["id"], str(error))
                if int(item["intentos"]) + 1 >= self.MAX_INTENTOS:
                    self.local.quitar_de_cola(item["id"])
                continue
            self.local.quitar_de_cola(item["id"])
            enviados += 1
        return enviados, fallidos

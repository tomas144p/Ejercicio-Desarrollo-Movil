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

from models.datos.conexiones import ErrorConexion


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
        if getattr(servidor, "requiere_sesion", False) and not servidor.sesion_activa:
            return ResultadoSincronizacion(mensaje="Sin sesión iniciada.")
        try:
            enviados, fallidos = self._subir(servidor, usuario)
            ultimo = self.local.ultimo_id_cola()
            descargado = False
            if usuario is not None:
                paquete = servidor.paquete_para(usuario)
                descargado = self.local.aplicar_paquete(paquete, ultimo)
        except ErrorConexion as error:
            return ResultadoSincronizacion(sin_conexion=True, mensaje=str(error))
        mensaje = f"{enviados} cambio(s) enviado(s)." if enviados else "Datos al día."
        return ResultadoSincronizacion(enviados, fallidos, descargado, False, mensaje)

    # Campo de cada cambio que dice quién lo hizo. Con la API, el servidor solo acepta cambios de quien tiene
    # la sesión abierta: los de otra persona del mismo teléfono esperan en la cola hasta que ella ingrese.
    CAMPO_AUTOR = {"intento": "estudiante_id", "estado_refuerzo": "estudiante_id", "desbloqueo": "docente_id",
                   "aviso": "autor_id", "aviso_leido": "usuario_id"}

    def _subir(self, servidor, usuario=None) -> tuple[int, int]:
        enviados = fallidos = 0
        dueno = getattr(usuario, "id", None) or getattr(servidor, "usuario_id", None)
        for item in self.local.pendientes():
            datos = json.loads(item["datos"])
            if getattr(servidor, "requiere_sesion", False) and dueno is not None:
                autor = datos.get(self.CAMPO_AUTOR.get(item["tipo"], ""))
                if autor is not None and int(autor) != int(dueno):
                    continue            # es de otra persona: se queda en la cola, sin contar como error
            try:
                servidor.aplicar_cambio(item["tipo"], datos)
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

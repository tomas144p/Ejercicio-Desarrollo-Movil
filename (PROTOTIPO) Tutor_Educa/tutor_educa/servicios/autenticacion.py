"""
Inicio de sesión en línea y sin conexión.

- En línea: se busca el correo en el servidor y se verifica la contraseña.
  El rol guardado para ese correo decide si entra como estudiante, docente
  o apoderado. Si marcó «Recordarme», se guarda en el teléfono una huella
  (hash) de su contraseña para poder entrar después sin internet.
- Sin conexión: se verifica contra esa huella guardada. Solo pueden entrar
  quienes ya ingresaron antes en este mismo dispositivo.

Una contraseña incorrecta en línea NUNCA pasa al modo sin conexión.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..datos.conexiones import ErrorConexion
from ..modelos import Usuario
from ..seguridad import GestorClaves


@dataclass
class ResultadoIngreso:
    exito: bool
    usuario: Usuario | None = None
    en_linea: bool = False
    mensaje: str = ""


class ServicioAutenticacion:
    PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    def __init__(self, local, gestor_servidor, sincronizacion, monitor=None):
        self.local = local
        self.gestor_servidor = gestor_servidor
        self.sincronizacion = sincronizacion
        self.monitor = monitor

    def ingresar(self, correo: str, clave: str, recordar: bool = True) -> ResultadoIngreso:
        """Operación bloqueante (usar en segundo plano)."""
        correo = (correo or "").strip().lower()
        if not self.PATRON_CORREO.match(correo):
            return ResultadoIngreso(False, mensaje="Escribe un correo válido, por ejemplo nombre@tutoreduca.cl.")
        if not clave:
            return ResultadoIngreso(False, mensaje="Escribe tu contraseña.")

        forzado = bool(self.monitor and self.monitor.forzado_sin_conexion)
        servidor = self.gestor_servidor.servidor
        if servidor is not None and not forzado:
            try:
                return self._ingresar_en_linea(servidor, correo, clave, recordar)
            except ErrorConexion:
                pass   # el servidor se cayó a mitad del ingreso: se intenta sin conexión
        return self._ingresar_sin_conexion(correo, clave)

    def _ingresar_en_linea(self, servidor, correo, clave, recordar) -> ResultadoIngreso:
        fila = servidor.usuario_por_correo(correo)
        if fila is None:
            return ResultadoIngreso(False, en_linea=True, mensaje="No encontramos una cuenta con ese correo.")
        if not int(fila.get("activo", 1)):
            return ResultadoIngreso(False, en_linea=True, mensaje="Esta cuenta está desactivada. Habla con tu colegio.")
        if not GestorClaves.verificar(clave, fila["clave_hash"]):
            return ResultadoIngreso(False, en_linea=True, mensaje="La contraseña no es correcta.")

        usuario = Usuario.desde_fila(fila)
        self.sincronizacion.sincronizar(usuario)   # descarga sus datos al teléfono
        if recordar:
            # Se guarda una huella nueva (con otra sal), nunca la contraseña.
            self.local.guardar_credencial(usuario, GestorClaves.generar_hash(clave))
        else:
            self.local.olvidar_credencial(correo)
        return ResultadoIngreso(True, usuario, en_linea=True, mensaje=f"¡Hola, {usuario.primer_nombre}!")

    def _ingresar_sin_conexion(self, correo, clave) -> ResultadoIngreso:
        credencial = self.local.credencial(correo)
        if credencial is None:
            return ResultadoIngreso(False, mensaje=(
                "No hay conexión con el servidor y esta cuenta no está guardada en este dispositivo. "
                "El primer ingreso debe hacerse con conexión y con «Recordarme» marcado."))
        if not GestorClaves.verificar(clave, credencial["clave_hash"]):
            return ResultadoIngreso(False, mensaje="La contraseña no coincide con la guardada en este dispositivo.")
        self.local.registrar_ingreso(correo)
        usuario = Usuario.desde_fila({"id": credencial["usuario_id"], "correo": credencial["correo"],
                                      "nombre": credencial["nombre"], "rol": credencial["rol"]})
        return ResultadoIngreso(True, usuario, en_linea=False, mensaje=(
            f"Hola, {usuario.primer_nombre}. Ingresaste sin conexión: verás los datos de tu última "
            "sincronización y tus cambios se enviarán cuando vuelva la conexión."))

    # --- Usuarios recordados ----------------------------------------------
    def recordados(self) -> list[dict]:
        return self.local.credenciales_recordadas()

    def olvidar(self, correo: str) -> None:
        self.local.olvidar_credencial(correo)

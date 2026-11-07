"""
Piezas de seguridad de la API: tokens y límites de uso.

- ``ServicioTokens``: crea y lee tokens JWT firmados (HS256). Hay dos tipos: de *acceso*
  (corto) y de *renovación* (largo, solo sirve para pedir un acceso nuevo).
- ``LimitadorVentana``: cuenta eventos por clave dentro de una ventana de tiempo. Se usa para
  frenar adivinación de contraseñas y para limitar el gasto de la IA.

Los límites viven en memoria: sirven para una sola instancia del servidor (el piloto). Si más
adelante hay varias instancias, hay que moverlos a una base compartida (por ejemplo Redis).
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict, deque
from typing import Callable

import jwt


class TokenInvalido(Exception):
    """El token no existe, venció, fue alterado o no es del tipo esperado."""


class ServicioTokens:
    ALGORITMO = "HS256"

    def __init__(self, secreto: str, minutos_acceso: int = 30, dias_renovacion: int = 30,
                 reloj: Callable[[], float] = time.time):
        if len(secreto) < 16:
            raise ValueError("El secreto de los tokens es demasiado corto.")
        self._secreto = secreto
        self.minutos_acceso = minutos_acceso
        self.dias_renovacion = dias_renovacion
        self._reloj = reloj

    def _crear(self, usuario_id: int, rol: str, tipo: str, segundos: int) -> str:
        ahora = int(self._reloj())
        carga = {"sub": str(usuario_id), "rol": rol, "typ": tipo, "iat": ahora, "exp": ahora + segundos,
                 "jti": uuid.uuid4().hex}
        return jwt.encode(carga, self._secreto, algorithm=self.ALGORITMO)

    def crear_acceso(self, usuario_id: int, rol: str) -> str:
        return self._crear(usuario_id, rol, "acceso", self.minutos_acceso * 60)

    def crear_renovacion(self, usuario_id: int, rol: str) -> str:
        return self._crear(usuario_id, rol, "renovacion", self.dias_renovacion * 86400)

    def leer(self, token: str, tipo: str) -> dict:
        """Devuelve los datos del token o lanza ``TokenInvalido``."""
        try:
            datos = jwt.decode(token, self._secreto, algorithms=[self.ALGORITMO],
                               options={"require": ["exp", "sub", "typ"], "verify_exp": False})
        except jwt.PyJWTError as error:
            raise TokenInvalido("Token inválido.") from error
        if datos.get("typ") != tipo:
            raise TokenInvalido("Tipo de token incorrecto.")
        if int(datos["exp"]) <= int(self._reloj()):     # el vencimiento se revisa con nuestro reloj (así se puede probar)
            raise TokenInvalido("El token venció.")
        try:
            datos["usuario_id"] = int(datos["sub"])
        except (TypeError, ValueError) as error:
            raise TokenInvalido("Token inválido.") from error
        return datos


class LimitadorVentana:
    """Permite como máximo ``maximo`` eventos por clave en los últimos ``ventana_seg`` segundos."""

    def __init__(self, maximo: int, ventana_seg: int, reloj: Callable[[], float] = time.monotonic):
        self.maximo, self.ventana = maximo, ventana_seg
        self._reloj = reloj
        self._eventos: dict[str, deque] = defaultdict(deque)
        self._candado = threading.Lock()

    def _purgar(self, clave: str, ahora: float) -> deque:
        cola = self._eventos[clave]
        while cola and ahora - cola[0] >= self.ventana:
            cola.popleft()
        if not cola:
            self._eventos.pop(clave, None)
            return deque()
        return cola

    def espera(self, clave: str) -> int:
        """Segundos que faltan para poder volver a intentar (0 si no está bloqueado)."""
        with self._candado:
            ahora = self._reloj()
            cola = self._purgar(clave, ahora)
            if len(cola) < self.maximo:
                return 0
            return max(1, int(self.ventana - (ahora - cola[0])) + 1)

    def registrar(self, clave: str) -> None:
        with self._candado:
            ahora = self._reloj()
            self._purgar(clave, ahora)
            self._eventos[clave].append(ahora)

    def intentar(self, clave: str) -> int:
        """Registra el evento si hay cupo. Devuelve 0 si se permitió, o los segundos de espera."""
        with self._candado:
            ahora = self._reloj()
            cola = self._purgar(clave, ahora)
            if len(cola) >= self.maximo:
                return max(1, int(self.ventana - (ahora - cola[0])) + 1)
            self._eventos[clave].append(ahora)
            return 0

    def limpiar(self, clave: str) -> None:
        with self._candado:
            self._eventos.pop(clave, None)

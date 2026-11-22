"""
Vigilante del reloj del servidor.

Todas las fechas de «hoy» y de registro salen del reloj del servidor, no del teléfono. Pero un reloj puede quedar mal
(un reinicio, un corte de luz, una pila agotada): por eso el servidor anota en su base la ÚLTIMA hora que vio. Si de
pronto su reloj marca una hora anterior a esa, sabe que está atrasado y **no registra asistencia** hasta que se
corrija: es mejor rechazar una lista (que sigue guardada en el teléfono y se envía sola después) que guardarla con
un día equivocado.

- Tolerancia de 10 minutos: los pequeños ajustes automáticos de hora (NTP) no cuentan como atraso.
- Si el reloj estaba ADELANTADO por error y ya se corrigió, la marca quedó en el futuro: la administración
  (superadministrador) puede confirmar que la hora actual es la correcta y restablecerla.
- Cuesta una escritura mínima por minuto como máximo.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from models.datos.conexiones import ErrorConexion
from services import calendario

TOLERANCIA = timedelta(minutes=10)
INTERVALO_ANOTAR = timedelta(seconds=60)


class ErrorReloj(Exception):
    """El reloj del servidor parece atrasado: no se puede confiar en «hoy» para registrar asistencia."""


def duracion_legible(atraso: timedelta) -> str:
    minutos = int(atraso.total_seconds() // 60)
    if minutos <= 1:
        return "1 minuto"
    if minutos < 90:
        return f"{minutos} minutos"
    horas = minutos // 60
    if horas < 48:
        return f"{horas} horas"
    return f"{horas // 24} días"


class VigilanteReloj:
    def __init__(self, obtener_servidor):
        """``obtener_servidor``: función que entrega el servidor de datos vigente."""
        self._servidor = obtener_servidor
        self._ultimo_anotado: datetime | None = None

    def estado(self) -> dict:
        repo = self._servidor()
        ahora, vista = repo.ahora_utc(), repo.ultima_hora_vista()
        atraso = (vista - ahora) if (vista is not None and ahora < vista) else timedelta(0)
        atrasado = atraso > TOLERANCIA
        chile = calendario.ahora_chile(ahora)
        return {"ahora": chile.strftime("%Y-%m-%d %H:%M:%S"),
                "texto": f"{calendario.fecha_legible(chile.date())}, {chile:%H:%M} (hora de Chile)",
                "ultima_vista": calendario.ahora_chile(vista).strftime("%Y-%m-%d %H:%M:%S") if vista else None,
                "atrasado": atrasado,
                "atraso": duracion_legible(atraso) if atrasado else ""}

    def exigir_confiable(self) -> None:
        estado = self.estado()
        if estado["atrasado"]:
            raise ErrorReloj(
                f"El reloj del servidor parece estar atrasado (unos {estado['atraso']} respecto de la última vez que "
                "funcionó). Por seguridad no se registra la asistencia hasta corregirlo. Tu lista sigue guardada en el "
                "teléfono y se enviará sola. Avisa a la administración del colegio.")

    def anotar(self) -> None:
        """Recuerda la hora más reciente vista. Se llama en cada petición; escribe como máximo una vez por minuto y
        NUNCA retrocede la marca (si el reloj está atrasado, la marca se queda donde estaba)."""
        try:
            repo = self._servidor()
            ahora = repo.ahora_utc()
            if self._ultimo_anotado is not None and timedelta(0) <= ahora - self._ultimo_anotado < INTERVALO_ANOTAR:
                return
            vista = repo.ultima_hora_vista()
            if vista is not None and ahora < vista:
                return
            repo.anotar_hora_vista(ahora)
            self._ultimo_anotado = ahora
        except ErrorConexion:
            pass                  # sin base de datos ahora: se anota en la próxima petición

    def restablecer(self) -> dict:
        """La administración confirma que la hora ACTUAL del servidor es la correcta."""
        repo = self._servidor()
        ahora = repo.ahora_utc()
        repo.anotar_hora_vista(ahora)
        self._ultimo_anotado = ahora
        return self.estado()

"""
Ajustes del backend. Todo viene de variables de entorno (nunca de archivos que se suban a Git).

Entorno de desarrollo (por defecto): usa la base de demostración (SQLite) y genera un secreto
temporal. Entorno de producción (``TUTOR_ENTORNO=produccion``): exige MySQL, un secreto largo y
desactiva la documentación automática de la API.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from services.configuracion import ConfigServidor


class AjustesInvalidos(Exception):
    """La configuración no es segura o está incompleta. El mensaje dice qué corregir."""


def _entero(env, nombre: str, defecto: int) -> int:
    try:
        return int(env.get(nombre, defecto))
    except (TypeError, ValueError):
        raise AjustesInvalidos(f"{nombre} debe ser un número entero.")


@dataclass
class Ajustes:
    entorno: str = "desarrollo"                  # "desarrollo" | "produccion"
    jwt_secreto: str = ""
    minutos_acceso: int = 30                     # duración del token de acceso
    dias_renovacion: int = 30                    # cuánto dura la sesión sin volver a escribir la clave
    bd: ConfigServidor = field(default_factory=lambda: ConfigServidor(motor="demo"))
    carpeta_datos: Path = Path("datos_backend")
    # IA
    ia_api_key: str = ""
    ia_modelo: str = "claude-haiku-4-5-20251001"
    ia_max_tokens: int = 700
    ia_cuota_diaria: int = 40                    # mensajes de IA por persona por día
    ia_por_minuto: int = 6
    # Protección del ingreso
    login_max_fallos: int = 5                    # por correo, dentro de la ventana
    login_max_fallos_ip: int = 30                # por dirección IP
    login_ventana_seg: int = 900
    confiar_proxy: bool = False                  # leer la IP real desde X-Forwarded-For (solo detrás de un proxy propio)
    max_cuerpo_bytes: int = 256 * 1024

    @property
    def es_produccion(self) -> bool:
        return self.entorno == "produccion"

    # ------------------------------------------------------------------
    @classmethod
    def desde_entorno(cls, env=None) -> "Ajustes":
        env = os.environ if env is None else env
        entorno = (env.get("TUTOR_ENTORNO") or "desarrollo").strip().lower()
        if entorno not in ("desarrollo", "produccion"):
            raise AjustesInvalidos("TUTOR_ENTORNO debe ser «desarrollo» o «produccion».")
        motor = (env.get("TUTOR_DB_MOTOR") or ("mysql" if entorno == "produccion" else "demo")).strip().lower()
        bd = ConfigServidor(
            motor=motor, host=env.get("TUTOR_DB_HOST", "127.0.0.1"), puerto=_entero(env, "TUTOR_DB_PUERTO", 3306),
            usuario=env.get("TUTOR_DB_USUARIO", "tutor_api"), clave=env.get("TUTOR_DB_CLAVE", ""),
            base_datos=env.get("TUTOR_DB_NOMBRE", "tutor_educa"), tiempo_espera=_entero(env, "TUTOR_DB_ESPERA", 5))
        ajustes = cls(
            entorno=entorno, jwt_secreto=(env.get("TUTOR_JWT_SECRETO") or "").strip(), bd=bd,
            carpeta_datos=Path(env.get("TUTOR_DATOS", "datos_backend")),
            minutos_acceso=_entero(env, "TUTOR_MINUTOS_ACCESO", 30),
            dias_renovacion=_entero(env, "TUTOR_DIAS_RENOVACION", 30),
            ia_api_key=(env.get("TUTOR_IA_API_KEY") or env.get("ANTHROPIC_API_KEY") or "").strip(),
            ia_modelo=env.get("TUTOR_IA_MODELO", cls.ia_modelo),
            ia_max_tokens=_entero(env, "TUTOR_IA_MAX_TOKENS", 700),
            ia_cuota_diaria=_entero(env, "TUTOR_IA_CUOTA_DIARIA", 40),
            ia_por_minuto=_entero(env, "TUTOR_IA_POR_MINUTO", 6),
            confiar_proxy=(env.get("TUTOR_CONFIAR_PROXY", "0") == "1"))
        return ajustes.validado()

    def validado(self) -> "Ajustes":
        """Revisa que la configuración sea segura. En desarrollo completa lo que falte."""
        if self.es_produccion:
            if len(self.jwt_secreto) < 32:
                raise AjustesInvalidos("En producción TUTOR_JWT_SECRETO es obligatorio y debe tener al menos 32 "
                                       "caracteres. Genera uno con:  python -c \"import secrets; "
                                       "print(secrets.token_urlsafe(48))\"")
            if self.bd.motor != "mysql":
                raise AjustesInvalidos("En producción la base de datos debe ser MySQL (TUTOR_DB_MOTOR=mysql).")
            if not self.bd.clave:
                raise AjustesInvalidos("En producción TUTOR_DB_CLAVE no puede estar vacía.")
            if self.bd.usuario == "root":
                raise AjustesInvalidos("No uses el usuario root de MySQL: crea un usuario solo para esta API.")
        elif not self.jwt_secreto:
            # Solo para desarrollo: los tokens dejan de valer al reiniciar el servidor.
            self.jwt_secreto = secrets.token_urlsafe(48)
        if self.bd.motor not in ("mysql", "demo"):
            raise AjustesInvalidos("TUTOR_DB_MOTOR debe ser «mysql» o «demo».")
        return self

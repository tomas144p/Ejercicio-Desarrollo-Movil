"""
Configuración de Tutor Educa.

La configuración se lee desde tres fuentes, en este orden (la última gana):

1. ``config.json``: valores por defecto que se suben al repositorio.
2. ``config.local.json``: valores personales (por ejemplo la clave de la IA
   o la contraseña de MySQL). Está en ``.gitignore`` para no publicarla.
3. Variables de entorno: ``ANTHROPIC_API_KEY`` o ``TUTOR_IA_API_KEY``.

Así el mismo código funciona en el computador de cada integrante del equipo
sin tener que modificar archivos compartidos.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields
from pathlib import Path

# Carpeta raíz del proyecto (donde están main.py y config.json).
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent


@dataclass
class ConfigServidor:
    """Datos para conectarse a la base de datos del colegio (MySQL)."""

    motor: str = "auto"          # "auto" | "mysql" | "demo"
    host: str = "127.0.0.1"
    puerto: int = 3306
    usuario: str = "root"
    clave: str = ""
    base_datos: str = "tutor_educa"
    tiempo_espera: int = 3       # segundos antes de rendirse al conectar


@dataclass
class ConfigIA:
    """Datos del proveedor de inteligencia artificial para el chat."""

    proveedor: str = "anthropic"  # "anthropic" | "openai_compatible" | "local"
    modelo: str = "claude-haiku-4-5-20251001"
    api_key: str = ""
    url_base: str = ""            # solo para "openai_compatible" (Ollama, Groq...)
    max_tokens: int = 700
    tiempo_espera: int = 40


@dataclass
class ConfigApp:
    """Opciones generales de la aplicación."""

    carpeta_datos: str = ""               # vacío = se elige automáticamente
    intervalo_sincronizacion: int = 15    # segundos entre revisiones de conexión


@dataclass
class Configuracion:
    """Agrupa las tres secciones de configuración."""

    servidor: ConfigServidor = field(default_factory=ConfigServidor)
    ia: ConfigIA = field(default_factory=ConfigIA)
    app: ConfigApp = field(default_factory=ConfigApp)

    # ------------------------------------------------------------------
    @classmethod
    def cargar(cls, raiz: Path = RAIZ_PROYECTO) -> "Configuracion":
        """Lee config.json, luego config.local.json y por último el entorno."""
        config = cls()
        for nombre in ("config.json", "config.local.json"):
            ruta = Path(raiz) / nombre
            if ruta.exists():
                try:
                    datos = json.loads(ruta.read_text(encoding="utf-8"))
                except (OSError, ValueError) as error:
                    # Un JSON mal escrito no debe impedir que la app abra.
                    print(f"[config] No se pudo leer {nombre}: {error}")
                    continue
                config._mezclar(datos)

        # La clave de la IA también puede venir de una variable de entorno.
        clave_entorno = os.environ.get("TUTOR_IA_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if clave_entorno and not config.ia.api_key:
            config.ia.api_key = clave_entorno.strip()
        return config

    def _mezclar(self, datos: dict) -> None:
        """Copia sobre esta configuración solo las claves conocidas del JSON."""
        for seccion in ("servidor", "ia", "app"):
            valores = datos.get(seccion)
            if not isinstance(valores, dict):
                continue
            destino = getattr(self, seccion)
            for campo in fields(destino):
                if campo.name in valores and not campo.name.startswith("_"):
                    valor = valores[campo.name]
                    # Se respeta el tipo original (por ejemplo, el puerto es int).
                    tipo_actual = type(getattr(destino, campo.name))
                    try:
                        valor = tipo_actual(valor)
                    except (TypeError, ValueError):
                        continue
                    setattr(destino, campo.name, valor)

    # ------------------------------------------------------------------
    def carpeta_datos(self, carpeta_usuario: str | None = None) -> Path:
        """
        Carpeta donde se guarda la base de datos interna del dispositivo.

        En Android Kivy entrega ``user_data_dir`` (carpeta privada de la app);
        en el computador se usa ``datos_locales/`` dentro del proyecto para que
        sea fácil de revisar o borrar durante el desarrollo.
        """
        if os.environ.get("TUTOR_EDUCA_DATOS"):
            ruta = Path(os.environ["TUTOR_EDUCA_DATOS"])
        elif self.app.carpeta_datos:
            ruta = Path(self.app.carpeta_datos).expanduser()
        elif carpeta_usuario and "ANDROID_ARGUMENT" in os.environ:
            ruta = Path(carpeta_usuario)
        else:
            ruta = RAIZ_PROYECTO / "datos_locales"
        ruta.mkdir(parents=True, exist_ok=True)
        return ruta

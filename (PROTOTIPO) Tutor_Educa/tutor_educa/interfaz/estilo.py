"""
Estilo visual de Tutor Educa: colores, tipografías, íconos y formato de texto.

Decisiones de diseño:
- Fondo "papel" claro y cuadrícula de cuaderno: la app se siente escolar.
- Un color por perfil: azul (estudiante), verde pizarra (docente) y mora
  (apoderado), para que cada persona reconozca "su" app.
- Lexend: tipografía pensada para facilitar la lectura en niños y niñas.
- Delius: letra manuscrita para los ejemplos resueltos "en el cuaderno".
- Íconos Lucide en vez de emojis: Kivy no puede dibujar emojis a color (por
  eso en el prototipo anterior se veían en blanco y negro o rayados).
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from kivy.core.text import DEFAULT_FONT, LabelBase
from kivy.metrics import sp
from kivy.utils import escape_markup, get_color_from_hex

CARPETA_FUENTES = Path(__file__).resolve().parents[2] / "fonts"


def color(hex_color: str, alfa: float = 1.0) -> list:
    """"#2748C9" → [r, g, b, a] (el formato que usa Kivy)."""
    rgba = list(get_color_from_hex(hex_color))
    rgba[3] = alfa
    return rgba


def oscurecer(hex_color: str, factor: float = 0.88) -> list:
    r, g, b, a = color(hex_color)
    return [r * factor, g * factor, b * factor, a]


class Paleta:
    PAPEL = "#F4F7FB"
    SUPERFICIE = "#FFFFFF"
    GRIS_SUAVE = "#EEF2F8"
    TINTA = "#1C2B4A"
    TINTA_SUAVE = "#5A6A86"
    TINTA_TENUE = "#8A97AD"
    TINTA_CUADERNO = "#23409A"     # "lápiz pasta" azul del cuaderno
    LINEA = "#DCE3EE"
    CUADRICULA = "#E3EAF4"
    MARGEN = "#F2B5B5"
    AZUL, AZUL_SUAVE = "#2748C9", "#E8EDFB"
    PIZARRA, PIZARRA_SUAVE = "#1F6B57", "#E3F1EC"
    MORA, MORA_SUAVE = "#7B3F98", "#F1E8F6"
    DESTACADOR, DESTACADOR_SUAVE = "#FFE45C", "#FFF6C2"
    ROJO, ROJO_SUAVE = "#D23C3C", "#FCE9E9"
    VERDE, VERDE_SUAVE = "#1F9D6B", "#E2F5EC"
    AMBAR, AMBAR_SUAVE = "#B36F00", "#FFF2D6"

    POR_ROL = {"estudiante": (AZUL, AZUL_SUAVE), "docente": (PIZARRA, PIZARRA_SUAVE),
               "apoderado": (MORA, MORA_SUAVE)}
    POR_CATEGORIA_NOTA = {"insuficiente": (ROJO, ROJO_SUAVE), "en_riesgo": (AMBAR, AMBAR_SUAVE),
                          "adecuado": (TINTA, GRIS_SUAVE), "destacado": (VERDE, VERDE_SUAVE),
                          "sin_nota": (TINTA_TENUE, GRIS_SUAVE)}
    POR_ESTADO = {"disponible": (AZUL, AZUL_SUAVE), "en_progreso": (AMBAR, AMBAR_SUAVE),
                  "logrado": (VERDE, VERDE_SUAVE)}
    POR_TIPO_AVISO = {"info": (AZUL, AZUL_SUAVE, "info", "Información"),
                      "evaluacion": (AMBAR, AMBAR_SUAVE, "calendar", "Evaluación"),
                      "refuerzo": (MORA, MORA_SUAVE, "book-open", "Refuerzo"),
                      "logro": (VERDE, VERDE_SUAVE, "trophy", "Logro")}
    SUAVE_DE = {AZUL: AZUL_SUAVE, PIZARRA: PIZARRA_SUAVE, MORA: MORA_SUAVE, ROJO: ROJO_SUAVE,
                VERDE: VERDE_SUAVE, AMBAR: AMBAR_SUAVE}

    @classmethod
    def suave(cls, hex_color: str) -> str:
        return cls.SUAVE_DE.get(hex_color, cls.GRIS_SUAVE)


class Tipografia:
    NORMAL = "Lexend"
    MEDIA = "LexendMedia"
    SEMI = "LexendSemi"
    NEGRITA = "LexendNegrita"
    CUADERNO = "Cuaderno"
    ICONOS = "Iconos"

    # Tamaños en sp (se escalan según la densidad de la pantalla)
    GIGANTE, TITULO, SUBTITULO, CUERPO, PEQUENA, MINI = 30, 21, 17, 15, 13, 11.5

    @classmethod
    def registrar(cls) -> None:
        """Registra las fuentes en Kivy. Lexend pasa a ser la fuente por defecto."""
        f = CARPETA_FUENTES
        LabelBase.register(DEFAULT_FONT, str(f / "Lexend-Regular.ttf"), fn_bold=str(f / "Lexend-Bold.ttf"))
        LabelBase.register(cls.NORMAL, str(f / "Lexend-Regular.ttf"), fn_bold=str(f / "Lexend-Bold.ttf"))
        LabelBase.register(cls.MEDIA, str(f / "Lexend-Medium.ttf"), fn_bold=str(f / "Lexend-Bold.ttf"))
        LabelBase.register(cls.SEMI, str(f / "Lexend-SemiBold.ttf"), fn_bold=str(f / "Lexend-Bold.ttf"))
        LabelBase.register(cls.NEGRITA, str(f / "Lexend-Bold.ttf"))
        LabelBase.register(cls.CUADERNO, str(f / "Delius-Regular.ttf"))
        LabelBase.register(cls.ICONOS, str(f / "lucide.ttf"))


class Iconos:
    """Traduce nombres de íconos Lucide ("calculator") a su carácter en la fuente."""

    _mapa: dict[str, int] | None = None

    @classmethod
    def caracter(cls, nombre: str) -> str:
        if cls._mapa is None:
            cls._mapa = json.loads((CARPETA_FUENTES / "lucide-codepoints.json").read_text(encoding="utf-8"))
        codigo = cls._mapa.get(nombre) or cls._mapa.get("circle-help")
        return chr(int(codigo))

    @classmethod
    def markup(cls, nombre: str, tamano: float) -> str:
        """Ícono para insertar dentro de un texto con markup (por ejemplo en un botón)."""
        return f"[font={Tipografia.ICONOS}][size={int(sp(tamano))}]{cls.caracter(nombre)}[/size][/font]"


MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic"]


class FormatoTexto:
    """Prepara textos para mostrarlos: potencias, negritas, fechas y notas."""

    _POTENCIA = re.compile(r"\^(\d+|[a-z])")
    _NEGRITA = re.compile(r"\*\*(.+?)\*\*")

    @classmethod
    def enriquecer(cls, texto: str, tamano: float, cuaderno: bool = False) -> str:
        """
        Escapa el texto (para que un "[" escrito por alguien no rompa el markup)
        y convierte  5^3 → 5 con el 3 elevado,  **idea** → negrita.
        """
        resultado = escape_markup(texto or "")
        chico = int(sp(tamano) * 0.62)
        resultado = cls._POTENCIA.sub(lambda m: f"[sup][size={chico}]{m.group(1)}[/size][/sup]", resultado)
        resultado = cls._NEGRITA.sub(r"[b]\1[/b]", resultado)
        if cuaderno:  # la letra manuscrita no tiene el signo de raíz
            resultado = resultado.replace("√", f"[font={Tipografia.NORMAL}]√[/font]")
        return resultado

    @staticmethod
    def _fecha(iso: str) -> datetime | None:
        try:
            return datetime.strptime((iso or "")[:10], "%Y-%m-%d")
        except ValueError:
            return None

    @classmethod
    def fecha_corta(cls, iso: str) -> str:
        fecha = cls._fecha(iso)
        return f"{fecha.day} {MESES_CORTOS[fecha.month - 1]}" if fecha else ""

    @classmethod
    def fecha_relativa(cls, iso: str) -> str:
        fecha = cls._fecha(iso)
        if not fecha:
            return ""
        dias = (datetime.now().date() - fecha.date()).days
        if dias <= 0:
            return "hoy"
        if dias == 1:
            return "ayer"
        if dias < 7:
            return f"hace {dias} días"
        return cls.fecha_corta(iso)

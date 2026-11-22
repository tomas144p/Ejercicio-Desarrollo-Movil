"""
Validaciones de lo que escribe el usuario (Python puro, sin Kivy).

Cada función devuelve el texto limpio o lanza ``ValueError`` con un mensaje
que la pantalla puede mostrar tal cual. Las pantallas (views/) las llaman
dentro de un ``try/except ValueError``.
"""

import re

PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validar_correo(texto: str) -> str:
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("Escribe tu correo.")
    if not PATRON_CORREO.match(texto):
        raise ValueError("El correo no parece válido. Ejemplo: nombre@tutoreduca.cl")
    return texto


def validar_clave(texto: str) -> str:
    if not texto:
        raise ValueError("Escribe tu contraseña.")
    return texto


def validar_aviso(titulo: str, cuerpo: str) -> tuple:
    titulo, cuerpo = (titulo or "").strip(), (cuerpo or "").strip()
    if len(titulo) < 3:
        raise ValueError("El título necesita al menos 3 letras.")
    if len(cuerpo) < 5:
        raise ValueError("El mensaje necesita al menos 5 letras.")
    return titulo, cuerpo


def validar_respuesta(texto: str) -> str:
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("Primero elige o escribe una respuesta.")
    return texto


LARGO_MINIMO_CLAVE_NUEVA = 10


def validar_clave_nueva(clave: str) -> str:
    """
    Regla para la contraseña que una persona elige al activar su cuenta. La usan la app (para avisar antes de enviar)
    y el servidor (que es quien la hace cumplir de verdad).
    """
    if len(clave or "") < LARGO_MINIMO_CLAVE_NUEVA:
        raise ValueError(f"La contraseña debe tener al menos {LARGO_MINIMO_CLAVE_NUEVA} caracteres.")
    if len(clave) > 200:
        raise ValueError("La contraseña es demasiado larga.")
    if clave.isdigit() or clave.lower() == clave.upper():
        raise ValueError("La contraseña no puede ser solo números ni solo símbolos: mezcla letras y números.")
    return clave

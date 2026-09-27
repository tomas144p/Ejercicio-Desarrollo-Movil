"""
Manejo seguro de contraseñas.

Las contraseñas NUNCA se guardan tal cual, ni en MySQL ni en el teléfono.
Se guarda un "hash": una huella que se calcula a partir de la contraseña y
de una "sal" aleatoria. Con la huella se puede comprobar si una contraseña
es correcta, pero no se puede recuperar la contraseña original.

Se usa PBKDF2-SHA256, que viene incluido en Python (módulo ``hashlib``), por
lo que no hace falta instalar nada extra ni en el PC ni en Android.

Formato guardado:  ``pbkdf2_sha256$<iteraciones>$<sal>$<huella>``
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets


class GestorClaves:
    """Crea y verifica huellas (hashes) de contraseñas."""

    ALGORITMO = "pbkdf2_sha256"
    ITERACIONES = 120_000

    @classmethod
    def generar_hash(cls, clave: str, sal: str | None = None) -> str:
        """Devuelve la huella de ``clave`` lista para guardar en la base de datos."""
        sal = sal or secrets.token_hex(8)
        huella = cls._calcular(clave, sal, cls.ITERACIONES)
        return f"{cls.ALGORITMO}${cls.ITERACIONES}${sal}${huella}"

    @classmethod
    def verificar(cls, clave: str, hash_guardado: str) -> bool:
        """Comprueba si ``clave`` corresponde a la huella guardada."""
        try:
            algoritmo, iteraciones, sal, huella = (hash_guardado or "").split("$")
            if algoritmo != cls.ALGORITMO:
                return False
            calculada = cls._calcular(clave, sal, int(iteraciones))
        except (ValueError, TypeError):
            return False
        # compare_digest compara en tiempo constante (evita ataques por tiempo).
        return hmac.compare_digest(calculada, huella)

    @staticmethod
    def _calcular(clave: str, sal: str, iteraciones: int) -> str:
        crudo = hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"),
                                    sal.encode("utf-8"), iteraciones)
        return base64.b64encode(crudo).decode("ascii").rstrip("=")

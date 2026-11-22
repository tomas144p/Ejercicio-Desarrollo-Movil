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


# ---------------------------------------------------------------------------
# Cuentas por invitación
# ---------------------------------------------------------------------------
CLAVE_PENDIENTE = "!pendiente"
"""
Marca que se guarda en lugar de la huella cuando la cuenta aún no tiene contraseña (esperando que su dueña use el
código de invitación). No tiene el formato de una huella, así que ninguna contraseña puede coincidir con ella.
"""


class CodigosInvitacion:
    """
    Códigos de un solo uso para activar una cuenta (o cambiar la contraseña) sin que nadie conozca la contraseña ajena.

    Formato ``ABCDE-FGHJK`` (10 caracteres, ~50 bits). Usa el alfabeto de Crockford, sin letras que se confunden
    (I, L, O, U). En la base de datos solo se guarda la huella SHA-256: ni siquiera el servidor puede volver a mostrarlo.
    """

    ALFABETO = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    LARGO = 10

    @classmethod
    def generar(cls) -> str:
        letras = "".join(secrets.choice(cls.ALFABETO) for _ in range(cls.LARGO))
        return f"{letras[:5]}-{letras[5:]}"

    @classmethod
    def normalizar(cls, codigo: str) -> str:
        """Mayúsculas, sin guiones ni espacios, y corrigiendo confusiones típicas (O→0, I/L→1)."""
        limpio = "".join(c for c in (codigo or "").upper() if c.isalnum())
        return limpio.translate(str.maketrans({"O": "0", "I": "1", "L": "1"}))

    @classmethod
    def huella(cls, codigo: str) -> str:
        return hashlib.sha256(cls.normalizar(codigo).encode("utf-8")).hexdigest()

    @classmethod
    def tiene_formato(cls, codigo: str) -> bool:
        normal = cls.normalizar(codigo)
        return len(normal) == cls.LARGO and all(c in cls.ALFABETO for c in normal)

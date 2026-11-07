"""
Backend de Tutor Educa (API).

Es lo ÚNICO que habla con la base de datos y con la IA. La app del celular solo
le habla a esta API por HTTPS: ya no lleva dentro claves de MySQL ni de la IA.

Reutiliza ``models/`` y ``services/`` de la app (esquema, repositorio, contraseñas).
Ejecutar:  python -m backend        (ver backend/README.md)
"""

VERSION = "0.1.0"

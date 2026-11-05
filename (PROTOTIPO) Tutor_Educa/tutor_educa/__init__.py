"""
Paquete principal de Tutor Educa.

La aplicación está separada en capas para que cada archivo tenga una sola
responsabilidad (principio básico de la Programación Orientada a Objetos):

- ``configuracion``, ``seguridad``, ``modelos`` y ``evaluacion``: núcleo sin
  interfaz gráfica (se puede probar con ``python -m unittest``).
- ``contenido``: la materia preescrita que se lee sin internet.
- ``datos``: conexión a MySQL/phpMyAdmin (servidor) y a SQLite (dispositivo).
- ``servicios``: inicio de sesión, sincronización, conexión y tutor IA.
- ``interfaz``: pantallas y componentes visuales hechos con Kivy.
"""

__version__ = "2.0.0"

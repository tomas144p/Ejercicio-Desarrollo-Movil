[app]

# ---------------------------------------------------------------------------
# Tutor Educa: configuración para compilar el APK con Buildozer.
# Este archivo debe llamarse EXACTAMENTE «buildozer.spec» y estar en la misma
# carpeta que main.py (la carpeta Tutor_Educa).
# ---------------------------------------------------------------------------

title = Tutor Educa
package.name = tutoreduca
package.domain = cl.tutoreduca

# Código fuente: la carpeta donde está este archivo y main.py
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,json,txt

# Lo que NO va dentro del APK (servidor, pruebas, herramientas, capturas, datos de tu PC...)
source.exclude_dirs = backend,pruebas,herramientas,capturas,database,datos_locales,docs,bin,.buildozer,.git,.github,__pycache__,node_modules,tests
source.exclude_patterns = config.local.json,docker-compose*,*.sql,*.md,*.db

# La versión se lee de services/version.py (VERSION_APP = "0.1.0"): se cambia en un solo lugar.
version.regex = VERSION_APP = ["'](.*)["']
version.filename = %(source.dir)s/services/version.py

# Librerías que lleva el teléfono. IMPORTANTE:
#  - Buildozer NO instala las dependencias de cada paquete: hay que listarlas todas (por eso están asyncgui, etc.).
#  - NumPy y Matplotlib se dejan FUERA a propósito: en el teléfono la app calcula las estadísticas con Python puro
#    y el gráfico de progreso muestra «Gráfico no disponible». Compila mucho más rápido y el APK pesa menos.
#  - KivyMD 2.x (la que usa la app: MDButton, MDTextField...) se instala desde GitHub, no desde PyPI.
requirements = python3,kivy==2.3.0,https://github.com/kivymd/KivyMD/archive/master.zip,materialyoucolor,materialshapes,asynckivy,asyncgui,exceptiongroup,pillow,certifi

# Pantalla
orientation = portrait
fullscreen = 0

# Ícono y pantalla de carga (opcionales). Si no los tienes, se usan los de Kivy.
# icon.filename = %(source.dir)s/assets/icono.png
# presplash.filename = %(source.dir)s/assets/presplash.png

# ---------------------------------------------------------------------------
# Android
# ---------------------------------------------------------------------------
# Permisos: internet para el tutor IA y el servidor del colegio; estado de la red para saber si hay conexión.
android.permissions = INTERNET,ACCESS_NETWORK_STATE

android.api = 33
android.minapi = 24
android.ndk = 25b
android.ndk_api = 24

# Solo teléfonos de 64 bits (casi todos): compila en la mitad del tiempo.
# Para teléfonos muy antiguos: android.archs = arm64-v8a, armeabi-v7a
android.archs = arm64-v8a

# Acepta las licencias del SDK de Android sin preguntar (necesario en GitHub Actions)
android.accept_sdk_license = True

# Los datos de la app (notas, asistencia) no se copian a la nube de Google
android.allow_backup = False

# Mensajes de la app en el log del teléfono (adb logcat)
android.logcat_filters = *:S python:D

# ---------------------------------------------------------------------------
# python-for-android
# ---------------------------------------------------------------------------
# Versión fija y probada de python-for-android: así el resultado no cambia solo cuando salen versiones nuevas.
p4a.branch = v2024.01.21

[buildozer]

# 2 = muestra todo el detalle (útil para encontrar errores en GitHub Actions)
log_level = 2
warn_on_root = 1

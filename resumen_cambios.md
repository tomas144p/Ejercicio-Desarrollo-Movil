# Cambios aplicados: Arquitectura Modular en Tutor Educa

Taller: *Arquitectura Modular* (Desarrollo de Aplicaciones Móviles).
Proyecto: Tutor Educa (Kivy), versión sin alterar entregada en `_PROTOTIPO__Tutor_Educa.rar`.

## 1. Resumen

| Paso del taller | Estado | Qué se hizo |
|---|---|---|
| 1. Crear `views/`, `services/`, `models/` con `__init__.py` | Hecho | El paquete único `tutor_educa/` se repartió en las tres carpetas. |
| 2. Lógica de negocio en `services/`, sin Kivy | Hecho | `services/` y `models/` no importan Kivy (lo verifica una prueba). Se agregó `services/validaciones.py`. |
| 3. Una pantalla por archivo en `views/` | Hecho | Cada pantalla está en `views/<nombre>_screen.py` y todas heredan de `PantallaBase(MDScreen)`. Los imports son absolutos: `from services.xxx import yyy`. |
| 4. KivyMD 2.0 | Hecho | `MDApp`, `MDScreen`, `MDButton` + `MDButtonText`, `MDTextField` + `MDTextFieldHintText`, validación con `try/except`. |
| 5. `main.py` con menos de 25 líneas | Hecho | `main.py` tiene 24 líneas y solo contiene la clase `TutorEducaApp(MDApp)`. |

El proyecto no tenía cálculo de IVA ni operaciones sueltas. La lógica que se movió a `services/` es la que ya existía: corrección de pruebas, ingreso, sincronización, conexión, IA y configuración.

## 2. Estructura antes y después

### Antes

```
main.py                 (318 líneas: servicios, pantallas, sesión, navegación, sincronización)
tutor_educa/
  configuracion.py  seguridad.py  modelos.py  evaluacion.py
  contenido/   datos/   servicios/   servicios/ia/
  interfaz/ (componentes, dialogos, estilo, navegacion, pantallas/)
```

### Después

```
main.py                   Solo TutorEducaApp(MDApp)
controladores/            Partes de la app que antes estaban en main.py
  construccion.py         build(): crea servicios, pantallas y navegación; on_stop()
  conexion.py             Revisión de conexión, sincronización, diálogo de estado
  sesion.py               Inicio y cierre de sesión
  navegacion.py           ir_a, volver, abrir lección/chat, botón atrás
views/                    LA VISTA (Kivy / KivyMD)
  base_screen.py          PantallaBase(MDScreen), pantallas con pestañas
  ingreso_screen.py  estudiante_screen.py  leccion_screen.py  chat_screen.py
  docente_screen.py  ficha_estudiante_screen.py  apoderado_screen.py
  componentes.py  estilo.py  dialogos.py  navegacion.py
  raiz.py  ventana.py
services/                 LA LÓGICA (Python puro)
  validaciones.py  evaluacion.py  autenticacion.py  sincronizacion.py
  conexion.py  datos_app.py  tareas.py  configuracion.py  seguridad.py
  ia/                     conversacion, instrucciones, proveedores, tutor_local
models/                   LOS DATOS
  modelos.py
  contenido/              matematicas.py, datos_iniciales.py
  datos/                  esquema, conexiones, repositorio, servidor, local
```

## 3. Dónde quedó cada archivo

| Antes | Ahora |
|---|---|
| `tutor_educa/configuracion.py` | `services/configuracion.py` |
| `tutor_educa/seguridad.py` | `services/seguridad.py` |
| `tutor_educa/evaluacion.py` | `services/evaluacion.py` |
| `tutor_educa/servicios/*` | `services/*` |
| `tutor_educa/modelos.py` | `models/modelos.py` |
| `tutor_educa/contenido/*` | `models/contenido/*` |
| `tutor_educa/datos/*` | `models/datos/*` |
| `tutor_educa/interfaz/componentes.py`, `dialogos.py`, `estilo.py`, `navegacion.py` | `views/` (mismo nombre) |
| `tutor_educa/interfaz/pantallas/base.py` | `views/base_screen.py` |
| `tutor_educa/interfaz/pantallas/<x>.py` | `views/<x>_screen.py` |
| Clase `RaizApp` dentro de `main.py` | `views/raiz.py` |
| `Config.set(...)` al inicio de `main.py` | `views/ventana.py` (`configurar_ventana()`) |
| Métodos de `TutorEducaApp` en `main.py` | `controladores/*.py` |

## 4. Cambios por paso

### Paso 1 y 3: carpetas y pantallas

- Se crearon `views/`, `services/` y `models/` (y subcarpetas) con su `__init__.py`.
- Todos los imports pasaron de relativos (`from ..modelos import ...`) a absolutos (`from models.modelos import ...`).
- Se actualizaron también los imports de `pruebas/` y `herramientas/`.
- Se corrigió la ruta de las fuentes en `views/estilo.py` (`parents[1] / "fonts"`).

### Paso 2: servicios sin Kivy

- `programador_kivy` (usaba `Clock`) salió de `services/tareas.py` y pasó a `controladores/construccion.py`. Así ningún archivo de `services/` ni de `models/` importa Kivy.
- Nuevo `services/validaciones.py`, con funciones puras que devuelven el texto limpio o lanzan `ValueError`:
  - `validar_correo`
  - `validar_clave`
  - `validar_aviso`
  - `validar_respuesta`

### Paso 4: KivyMD 2.0

- `main.py`: `TutorEducaApp` hereda de `MDApp`. En `build()` se define `theme_style = "Light"` y `primary_palette = "Blue"`.
- `PantallaBase` hereda de `MDScreen` (todas las pantallas la usan).
- `Boton` (en `views/componentes.py`) ahora es un `MDButton` con un `MDButtonText` adentro. Las variantes se mapean así:

  | Variante | Estilo MDButton |
  |---|---|
  | primario | `filled` |
  | secundario | `tonal` |
  | contorno | `outlined` |
  | fantasma | `text` |
  | peligro | `tonal` (colores rojos) |

  Se mantiene la misma API (`texto`, `icono`, `variante`, `acento`, `al_presionar`, `cargando`, `cambiar_texto`).
- `CampoTexto` ahora usa `MDTextField(MDTextFieldHintText(...), mode="outlined")`. Mantiene `texto`, `entrada`, `al_confirmar`, contraseña con botón de ojo y multilínea. El ícono inicial usa `MDTextFieldLeadingIcon`.
- Validación con `try/except ValueError` en:
  - `views/ingreso_screen.py`: correo y contraseña antes de ingresar (el mensaje aparece bajo el formulario).
  - `views/docente_screen.py`: título y mensaje del aviso.
  - `views/leccion_screen.py`: respuesta de la prueba.

### Paso 5: `main.py`

`main.py` quedó con 24 líneas: configura la ventana, define las propiedades observables y arma la clase con las cuatro partes de `controladores/`:

```python
class TutorEducaApp(ConstruccionApp, ConexionApp, SesionApp, NavegacionApp, MDApp):
    en_linea = BooleanProperty(False)
    ...
```

## 5. Otros archivos modificados

- `requirements.txt`: se agregó `KivyMD>=2.0.0`.
- `README.md`: nueva sección "Estructura del proyecto" y ruta de `services/ia/instrucciones.py`.
- `pruebas/test_nucleo.py`: imports actualizados y 5 pruebas nuevas.
  - `PruebasValidaciones`: correo, clave, aviso y respuesta.
  - `PruebasArquitectura`: `services/` y `models/` sin Kivy, carpetas con `__init__.py`, `main.py` con menos de 25 líneas.
- `capturas/`: regeneradas con la interfaz KivyMD.

## 6. Cómo se verificó

- `python -m unittest discover pruebas`: 18 pruebas, todas OK (la de MySQL se omite si no hay MySQL local).
- Recorrido automático de la app con `herramientas/capturar_pantallas.py` (ingreso, estudiante, lección, prueba, chat, docente, ficha y apoderado, también sin conexión).
- Inicio y cierre de sesión probados con la cuenta docente de demostración.
- Probado en escritorio con servidor de demostración (SQLite). No se probó en un celular ni con MySQL real.

## 7. Diferencias visibles

- Los campos de texto cambian de estilo: borde con la sugerencia flotando arriba.
- El campo de contraseña conserva su botón de ojo aparte, porque el campo de KivyMD no trae uno.
- Los botones tienen la apariencia de KivyMD, manteniendo los colores por perfil.

## 8. Cómo ejecutarlo

```bash
pip install -r requirements.txt
python main.py
python -m unittest discover pruebas -v
```

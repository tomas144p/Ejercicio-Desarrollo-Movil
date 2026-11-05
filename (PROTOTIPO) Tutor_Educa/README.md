# Tutor Educa (prototipo funcional en Kivy)

Tutor de refuerzo de **matemáticas para 5° a 8° básico** pensado para estudiantes que se atrasan por inasistencias o dificultades de aprendizaje. La app tiene tres perfiles y el **correo define el perfil** al ingresar:

- **Estudiante**: ve sus notas en todas las asignaturas y los temas que su docente le desbloqueó. Cada tema trae materia preescrita (explicación, ejemplos resueltos y una prueba) que se puede estudiar **sin internet**. Con internet puede conversar con un **tutor IA** que explica dudas, muestra ejemplos y toma una mini prueba.
- **Docente**: ve a su curso, quién necesita refuerzo (promedio de Matemáticas bajo 5,0) y **desbloquea temas por estudiante** o por grupo. También envía avisos a los apoderados y ve quién los leyó.
- **Apoderado/a**: ve cómo va su estudiante, qué está reforzando, recibe consejos concretos para apoyar en casa, lee los avisos de la docente y puede usar un asistente IA para familias.

Las capturas actuales están en `capturas/` (las del prototipo anterior quedaron en `capturas/version_anterior/`).

## Cómo ejecutar

Requiere Python 3.10 o superior.

```bash
pip install -r requirements.txt
python main.py
```

Sin configurar nada, la app funciona con un **servidor de demostración** (SQLite) que ya trae un curso completo. Para probar, en la pantalla de ingreso toca **«Ver cuentas de prueba»**. Todas usan la contraseña `tutor2026`:

| Correo | Perfil |
|---|---|
| sofia.morales@tutoreduca.cl | Estudiante (ecuaciones en curso) |
| camila.perez@tutoreduca.cl | Estudiante que necesita refuerzo |
| carolina.fuentes@tutoreduca.cl | Docente del 7° Básico B |
| andres.morales@tutoreduca.cl | Apoderado de Sofía |
| rodrigo.perez@tutoreduca.cl | Apoderado de Camila |

## Base de datos con phpMyAdmin (MySQL / XAMPP)

1. Enciende **Apache y MySQL** en XAMPP y abre phpMyAdmin.
2. Pestaña **Importar**, elige `database/tutor_educa_mysql.sql` y presiona **Importar**. Se crea la base `tutor_educa` con las tablas y los datos de prueba (las contraseñas van cifradas).
3. Abre la app. Con la configuración por defecto (`"motor": "auto"`) se conecta sola a MySQL en `127.0.0.1:3306` con el usuario `root` sin contraseña (lo normal en XAMPP). En la pantalla de ingreso aparece «Conectado: MySQL en 127.0.0.1».

Si MySQL no está encendido, la app usa el servidor de demostración y lo avisa (al tocar la línea de estado se ve el motivo). Otras opciones en `config.json`:

- `"motor": "mysql"`: usa solo MySQL; si no responde, la app trabaja sin conexión.
- `"motor": "demo"`: usa siempre el servidor de demostración.

Si tu MySQL tiene contraseña, **no la escribas en `config.json`** (ese archivo se sube a GitHub): copia `config.local.ejemplo.json` como `config.local.json` y ponla ahí. Ese archivo está en `.gitignore`.

Para regenerar el `.sql` después de cambiar la materia: `python herramientas/generar_sql_mysql.py`. Para crear una cuenta nueva con su contraseña cifrada: `python herramientas/nuevo_usuario.py correo "Nombre" estudiante clave` (imprime el `INSERT` para pegar en phpMyAdmin > SQL).

## Ingreso en línea y sin conexión

- **En línea**: el correo y la contraseña se verifican contra el servidor y luego se descargan al teléfono los datos de ese usuario (notas, temas, avisos). Si marca **«Recordarme en este dispositivo»** (viene marcado), se guarda una huella cifrada de su contraseña en la base interna.
- **Sin conexión**: solo pueden entrar las cuentas recordadas en ese dispositivo. Ven los datos de su última sincronización, pueden leer la materia y rendir pruebas.
- **Sincronización**: todo lo que se hace sin conexión (resultados de pruebas, temas desbloqueados, avisos, avisos leídos) queda en una cola y se envía solo cuando vuelve la conexión. Una contraseña incorrecta en línea nunca «pasa» al modo sin conexión.
- La pastilla **«En línea / Sin conexión»** de la barra superior muestra el estado. Al tocarla se ve el detalle, se puede sincronizar a mano y existe el interruptor **«Simular sin conexión»**, útil para presentar el modo offline sin desconectar el computador.

## Tutor IA

El chat se activa cuando hay internet. Hay dos modos:

- **Con clave de IA**: responde **Claude** (Anthropic). Crea `config.local.json` con `{"ia": {"api_key": "tu-clave"}}` o define la variable de entorno `ANTHROPIC_API_KEY`. El modelo se cambia en `config.json`.
- **Sin clave (modo demostración)**: responde un tutor integrado que usa la materia de la base de datos. Reconoce pedidos como «explícame», «dame un ejemplo», «hazme una prueba» o «dame una pista», toma mini pruebas de 3 preguntas y da una segunda oportunidad con pista antes de revelar la respuesta.

Las instrucciones que convierten a la IA en docente están en `tutor_educa/servicios/ia/instrucciones.py`: primero explicar la duda, luego un ejemplo resuelto paso a paso y después una pequeña prueba, una pregunta a la vez. También se le entrega la materia oficial del tema para que no enseñe de otra forma.

Si la IA falla (clave incorrecta, sin saldo, sin internet), la conversación no se corta: responde el tutor integrado y aparece una nota con el motivo. También se puede usar otro proveedor compatible con la API de OpenAI (por ejemplo **Ollama** en el mismo PC) con `"proveedor": "openai_compatible"` y `"url_base": "http://localhost:11434/v1"`.

## Estructura del proyecto (POO por capas)

```
main.py                         Arma la app: servicios, pantallas y navegación
config.json                     Configuración compartida (sin claves)
tutor_educa/
  configuracion.py              Lee config.json + config.local.json + variables de entorno
  seguridad.py                  Cifrado de contraseñas (PBKDF2-SHA256)
  modelos.py                    Usuario -> Estudiante/Docente/Apoderado, Tema, Pregunta, Intento...
  evaluacion.py                 Corrector flexible de respuestas y lógica de la prueba
  contenido/matematicas.py      La materia de los 7 temas (se edita aquí)
  contenido/datos_iniciales.py  Curso, notas y cuentas de demostración
  datos/esquema.py              Las tablas, definidas una vez para SQLite y MySQL
  datos/conexiones.py           ConexionSQLite y ConexionMySQL (misma interfaz)
  datos/repositorio.py          Consultas compartidas
  datos/servidor.py             Servidor (MySQL o demostración) y qué datos baja cada rol
  datos/local.py                Base interna: copia local, credenciales recordadas, cola
  servicios/                    Ingreso, sincronización, monitor de conexión, tareas en 2º plano
  servicios/ia/                 Proveedores de IA, instrucciones, tutor integrado, conversación
  interfaz/                     Estilo, componentes, diálogos, navegación y pantallas
database/tutor_educa_mysql.sql  Para importar en phpMyAdmin
herramientas/                   Generar el .sql, crear usuarios, capturar pantallas
pruebas/test_nucleo.py          Pruebas automáticas
fonts/                          Lexend, Delius (cuaderno) e íconos Lucide, con sus licencias
```

Todas las clases y funciones tienen comentarios en español que explican qué hacen y por qué.

## Pruebas y herramientas

```bash
python -m unittest discover pruebas -v      # 13 pruebas (la de MySQL se omite si no hay MySQL local)
python herramientas/capturar_pantallas.py   # recorre la app y guarda 23 capturas en capturas/
```

Las pruebas revisan, entre otras cosas, que cada respuesta guardada en la materia sea aceptada por el corrector: así un error de tipeo en el contenido se detecta antes de que le llegue a un estudiante.

## Decisiones de diseño

- **Emojis por íconos**: Kivy no puede dibujar emojis a color, por eso en el prototipo anterior se veían en blanco y negro o rayados. Ahora se usa la fuente de íconos Lucide, que se ve igual en PC y Android.
- **Diálogos propios**: los *alerts* anteriores usaban el `Popup` de Kivy, con alto fijo y sin salto de línea, por eso el texto se salía del recuadro. `Dialogo` se adapta al texto y se desplaza si es largo.
- **Tipografía**: Lexend, diseñada para facilitar la lectura, y Delius (letra manuscrita) para los ejemplos «escritos en el cuaderno», con papel cuadriculado, margen rojo y destacador amarillo en el resultado.
- **Un color por perfil**: azul (estudiante), verde pizarra (docente) y mora (apoderado).
- El flujo en que el apoderado aprobaba tareas se reemplazó por el desbloqueo directo del docente por estudiante, como se describe el proyecto. El apoderado ahora acompaña con consejos, avisos y el asistente.

## Nota sobre seguridad

En este prototipo la app se conecta **directamente** a MySQL, lo que sirve para trabajar con phpMyAdmin en clases. En una versión real, el teléfono debería hablar con una **API intermedia** (por ejemplo en PHP o Python), que es la única con acceso a la base y que valida los permisos de cada rol. Por la misma razón, la clave de la IA debería vivir en ese servidor y no en el teléfono. Ver `PENDIENTES.md`.

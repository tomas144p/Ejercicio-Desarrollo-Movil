# Backend de Tutor Educa

La API que se ubica entre la app y la base de datos. **Es lo único que habla con MySQL y con la IA**: el celular
solo habla con la API por HTTPS y ya no lleva claves de base de datos ni de la IA.

```
Celular (Kivy)  ──HTTPS──►  Caddy  ──►  API (FastAPI)  ──►  MySQL
                                              └──►  IA (Claude)
```

## Qué hace la API

| Ruta | Para qué |
|---|---|
| `GET /salud` | ¿Está vivo el servidor y la base de datos? |
| `POST /login` | Correo + contraseña → token de acceso (30 min) y de renovación (30 días) |
| `POST /renovar` | Pide un token de acceso nuevo sin volver a escribir la contraseña |
| `POST /activar` | Activa una cuenta nueva (o recupera el acceso) con el **código de invitación** y la deja dentro |
| `GET /paquete` | Los datos que le corresponden a la persona según su perfil |
| `POST /cambios` | Un cambio hecho en el celular (intento, aviso, desbloqueo, «Recibido»), **revisado** antes de aplicarse |
| `POST /ia/chat` | Pregunta al tutor IA (la clave vive solo aquí, con límites de uso) |
| `/admin/...` | Colegios, cuentas y cursos (administradores; ver abajo) |
| `/docente/...` | Lo que una docente puede hacer con SUS estudiantes y apoderados |

## Seguridad que ya incluye

- La contraseña se verifica **en el servidor**. La app nunca recibe la huella de nadie.
- Mismo mensaje para «correo inexistente» y «contraseña mala» (no se puede averiguar qué correos existen).
- Bloqueo temporal tras 5 intentos fallidos por correo (30 por IP) en 15 minutos.
- Cada petición revisa que la cuenta siga activa: desactivar una cuenta invalida sus sesiones.
- Cada cambio se valida contra la persona del token: nadie actúa «en nombre de» otra, un apoderado solo toca avisos
  de sus hijos, un docente solo sus cursos, y la nota de una prueba se recalcula en el servidor.
- IA con límites por minuto y por día por persona; el servidor agrega sus propias reglas al tutor.
- En producción: exige secreto largo, MySQL (no la base de demostración), usuario de BD distinto de `root`, y
  apaga la documentación automática. Las respuestas con datos nunca se guardan en caché.
- La app solo acepta direcciones `https://` (salvo `http` hacia tu propio PC o red local, para desarrollo).

## Perfiles, cuentas e invitaciones

| Perfil | Qué hace | Dónde lo usa |
|---|---|---|
| **superadmin** | Administra la plataforma: crea colegios y el primer administrador de cada uno | Panel web (`/panel`) / API |
| **admin** | Administra UN colegio: docentes, estudiantes, apoderados y cursos; reinicia accesos | Panel web (`/panel`) / API |
| **docente** | Agrega y da de baja a los estudiantes de SUS cursos y vincula a sus apoderados | App |
| estudiante / apoderado | Usan la app | App |

**Nadie conoce ni reparte la contraseña de otra persona.** Una cuenta nueva nace *pendiente* (sin contraseña) y se crea un
**código de invitación** (`ABCDE-FGHJK`): de un solo uso, vence a los 7 días, se muestra una sola vez y en la base solo se
guarda su huella. La persona entra con su correo + el código, elige su propia contraseña (mínimo 10 caracteres, con letras y
números) y queda dentro (`POST /activar`). Si olvida su contraseña, el administrador (o su docente, en el caso de sus
estudiantes y apoderados) le genera un código nuevo: la contraseña anterior deja de servir y los códigos viejos mueren.

Reglas que hacen cumplir las pruebas:
- Los superadministradores **solo** se crean desde la consola del servidor; ninguna ruta de la API los crea ni los toca.
- Un administrador no crea ni modifica a otros administradores; una docente no crea docentes ni administra cuentas ajenas.
- Todo ocurre dentro del colegio de quien actúa; un curso, docente o apoderado de otro colegio se rechaza.
- **Nada se borra**: una baja *desactiva* la cuenta (se puede reactivar; se conserva el historial). El estudiante dado de baja
  desaparece de las listas de su docente y de su apoderado, y su sesión deja de servir. Eliminar datos personales a pedido
  (derecho de eliminación) será un proceso aparte (ver `PENDIENTES.md`).
- Adivinar códigos cuenta como intento fallido igual que las contraseñas (bloqueo tras 5). Los registros de auditoría
  nunca incluyen códigos.
- Los administradores **no** usan la app: `/paquete`, `/cambios` y el tutor IA les responden 403, y la app les explica que
  su perfil se maneja desde el panel web.

### Lo que ya se hace desde la app (modo API)

- **Pantalla de ingreso → «Tengo un código de invitación»**: correo + código + contraseña nueva (mínimo 10 caracteres, con
  letras y números). La persona queda dentro de inmediato.
- **Docente → Mi curso → «Agregar estudiante»**: nombre y correo del estudiante, y opcionalmente su apoderado/a (si ya tiene
  cuenta solo se vincula; si no, se crea). Al terminar aparecen los códigos, con un botón para **copiar un mensaje listo
  para enviar** por WhatsApp o correo. Los códigos se muestran solo esa vez.
- **Docente → ficha del estudiante → «Gestionar cuenta y apoderado»**: cambiar o quitar apoderado/a, código nuevo (para el
  estudiante o su apoderado/a), cambiar de curso y dar de baja.
- **Docente → Mi curso → «Dados de baja»**: lista y reactivación. Dar de baja no borra nada; además, al sincronizar, el teléfono
  **olvida** lo que el colegio retiró (el estudiante y sus notas), para no dejar datos de un menor guardados.
- Todo esto necesita conexión (las cuentas y los códigos los crea el servidor): sin internet la app lo dice con claridad y no
  guarda nada a medias.

Para ver el recorrido completo con la app real: `python -m backend` y, en otra consola,
`python herramientas/capturar_gestion.py --url http://127.0.0.1:8000` (guarda capturas en `capturas/gestion/`).
La dirección del servidor también se puede dar con la variable de entorno `TUTOR_EDUCA_SERVIDOR_URL`.

Primer arranque (desde la consola; después todo se hace por la API):

```bash
python -m backend.crear_colegio "Colegio San Andrés"
python -m backend.crear_usuario superadmin plataforma@tutoreduca.cl "Equipo Tutor Educa" --invitacion
python -m backend.crear_usuario admin directora@colegio.cl "Marta Rojas" --colegio-id 1 --invitacion
```

Cada comando muestra un código; la persona lo usa en `POST /activar` (la app y el panel lo harán por ella). Mientras no
exista el panel web, la API se puede usar con cualquier cliente HTTP (por ejemplo `/docs` en modo desarrollo).

## El panel web de administración

Los administradores (**superadmin** y **admin de colegio**) trabajan en una página web que sirve la propia API:
`http://127.0.0.1:8000/panel` en tu PC, `https://TU_DOMINIO/panel` en el servidor. No hay nada más que instalar.

| Sección | Quién | Qué permite |
|---|---|---|
| **Personas** | admin y superadmin | Ver y buscar docentes, estudiantes, apoderados y administradores; crear cuentas y obtener su **código de invitación** con un mensaje listo para copiar (WhatsApp o correo); código nuevo (recuperar acceso); desactivar y reactivar; editar nombre, curso y apoderado de un estudiante |
| **Cursos** | admin y superadmin | Crear cursos, cambiar nombre, nivel o docente a cargo |
| **Errores** | admin y superadmin | Errores y cierres inesperados de la app agrupados por causa (cuántas veces, dónde, en qué versión) con su traza |
| **Colegios** | solo superadmin | Crear, renombrar, suspender y reactivar colegios; crear el primer administrador de cada uno |

Cómo se entra: con correo y contraseña, o por **«Tengo un código»** para activar una cuenta nueva (así empieza cada
administrador). Las docentes, estudiantes y apoderados que intenten entrar al panel reciben un mensaje que los manda a la app.

Seguridad del panel:
- Las reglas de **quién puede qué** las hace cumplir la API (el panel solo oculta los botones que no corresponden).
- La política de seguridad del navegador (CSP) solo permite scripts y estilos propios y conexiones al mismo servidor; no hay
  código `inline`, ni librerías ni fuentes externas. Todo texto del servidor se muestra como texto, nunca como HTML.
- El código de invitación se muestra **una sola vez**; la contraseña nunca se guarda. El token de renovación vive en
  `sessionStorage` (se borra al cerrar la pestaña) y la sesión se cierra tras **20 minutos** sin actividad.
- Para apagarlo en un servidor: `TUTOR_PANEL=0`.

## Registro de errores de la app («crasheos»)

La app guarda **qué provocó** cada error o cierre inesperado y lo envía al servidor cuando hay conexión, igual que una
prueba o un aviso (`POST /cambios`, tipo `error_app`).

| Qué | Dónde |
|---|---|
| Captura en el teléfono | `services/registro_errores.py` (Python puro) y `controladores/errores.py` (Kivy) |
| Tabla en el servidor | `errores_app` (migración para una base existente: `database/migracion_errores.sql`) |
| Lista para administradores | `GET /admin/errores?colegio_id=&dias=30`, agrupada por causa; también en el panel web, pestaña **Errores** |

Qué se guarda: fecha y hora, versión de la app, plataforma, pantalla, tipo de error, mensaje limpio y una traza resumida
(archivo, línea y función, **sin el código**). **No** se guardan nombres, correos, contraseñas, tokens, RUT ni teléfonos:
se limpian en el teléfono y el servidor los **vuelve a limpiar** al recibirlos. El colegio y el perfil salen de la
sesión, nunca de lo que mande el teléfono. Los textos entre comillas que no parecen nombres de campo se ocultan.

Reglas: el admin ve solo los de su colegio; la superadmin, los de todos o los de uno; los demás perfiles no ven la lista.
Un colegio no puede guardar más de 500 errores al día y todo se borra a los 90 días.

Cierres inesperados: si la app se cierra sin que Python alcance a avisar (el sistema, falta de memoria, un fallo
nativo), al abrirla de nuevo se detecta que la sesión anterior quedó «activa» y se registra un `CierreInesperado` con
la última pantalla. Es una señal y no una certeza: también ocurre si se la fuerza a cerrar mientras se usa.

**Antes de abrir un error a otras personas, revisa el mensaje**: la limpieza es automática, pero un nombre dentro de un
texto largo puede escaparse.

## Colegios: cada uno es un espacio separado

Una sola base de datos atiende a varios colegios, pero **nada se mezcla**:

- Cada cuenta y cada curso pertenecen a UN colegio (`colegio_id`). Un estudiante toma el colegio de su curso y su
  apoderado debe ser del mismo. El correo es único en todo el sistema, así que se ingresa igual que siempre.
- El servidor decide el colegio con la cuenta del token, **nunca** con lo que diga el celular.
- Cada consulta de datos lleva el colegio, y cada cambio se revisa contra él. Aunque alguien dejara un dato mal enlazado
  entre colegios (un niño de un colegio apuntando al curso de otro), no se comparte ni se puede modificar: hay pruebas
  que lo provocan a propósito.
- Una cuenta sin colegio no ingresa. Un colegio **suspendido** deja a todos sus usuarios sin acceso, incluso con la
  sesión abierta (`python -m backend.crear_colegio --suspender ID`).
- La materia (asignaturas, temas, preguntas) es común a todos los colegios.

```bash
python -m backend.crear_colegio "Colegio San Andrés"       # crea el colegio y muestra su id
python -m backend.crear_colegio --listar
python -m backend.crear_colegio --suspender 2               # y --reactivar 2
```

### Actualizar una base MySQL antigua

```bash
python herramientas/generar_sql_mysql.py --migracion         # 0.3 -> colegios            (database/migracion_colegios.sql)
python herramientas/generar_sql_mysql.py --migracion-roles   # + administradores e invitaciones (database/migracion_roles.sql)
```
Haz un respaldo, cambia `NOMBRE DE TU COLEGIO` en el primero y ejecuta cada archivo UNA vez, en ese orden (si ya tienes
colegios, solo el segundo). Más detalle del primero:

```bash
python herramientas/generar_sql_mysql.py --migracion       # genera database/migracion_colegios.sql
# 1) respaldo de la base  2) cambia 'NOMBRE DE TU COLEGIO' dentro del archivo  3) ejecútalo UNA vez:
mysql -u root -p < database/migracion_colegios.sql
```

Crea la tabla, agrega `colegio_id`, crea tu colegio y le asigna todas las cuentas y cursos existentes. Las bases SQLite
(teléfono y demostración) se actualizan solas al abrir la app.

## Probarlo en tu PC (modo desarrollo)

```bash
pip install -r backend/requirements.txt
python -m backend                         # http://127.0.0.1:8000  (base de demostración, secreto temporal)
```

En `config.local.json` de la app (copia `config.local.ejemplo.json`):

```json
{ "servidor": { "motor": "http", "url": "http://127.0.0.1:8000" } }
```

(Desde el emulador de Android el PC se ve como `http://10.0.2.2:8000`.) Cuentas de prueba: las de siempre.
En desarrollo la documentación interactiva de la API queda en `http://127.0.0.1:8000/docs`.

## Probarlo con Docker Desktop en tu PC (paso a paso)

Es el ensayo general antes de usar un servidor real. Necesitas Docker Desktop abierto (que diga «Engine running») y Python.

```powershell
# 1) Desde la carpeta del proyecto: prepara el archivo de configuración
copy backend\.env.ejemplo .env
#    Abre .env y completa: TUTOR_DOMINIO=localhost  ·  TUTOR_JWT_SECRETO  ·  MYSQL_ROOT_PASSWORD  ·  TUTOR_DB_CLAVE
#    (para generar el secreto:  python -c "import secrets; print(secrets.token_urlsafe(48))")
#    Deja TUTOR_IA_API_KEY vacío: el tutor IA responderá «no activado» y la prueba lo espera.

# 2) Genera el SQL de producción (tablas + materia, sin cuentas de prueba). Debe existir ANTES de levantar Docker.
python herramientas\generar_sql_mysql.py --produccion

# 3) Levanta la API y MySQL (sin Caddy: no hay dominio en tu PC)
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build

# 4) Corre la prueba automática del despliegue
python herramientas\probar_docker.py
```

La prueba crea dos colegios con cuentas de prueba, verifica ingreso, bloqueo por intentos, permisos, que un colegio no ve ni
cambia datos de otro, y que todo sobrevive a un reinicio de los contenedores. Termina con
«las N comprobaciones pasaron» o con la lista de las que fallaron.

Para probar la app contra tu Docker: `config.local.json` → `{"servidor": {"motor": "http", "url": "http://127.0.0.1:8000"}}`
y crea cuentas reales con `docker compose exec api python -m backend.crear_usuario ...` (ver más abajo).

| Si ves… | Qué hacer |
|---|---|
| «Cannot connect to the Docker daemon» / `docker info` falla | Abre Docker Desktop y espera a que termine de iniciar |
| `compose` se queja de «Falta TUTOR_JWT_SECRETO…» | Completa ese valor en `.env` |
| La API se reinicia sin parar | `docker compose logs api`: casi siempre es «Configuración inválida» (secreto corto, clave vacía…) |
| Puerto 8000 ocupado | Cambia `8000:8000` por `8001:8000` en `docker-compose.local.yml` y usa `--url http://127.0.0.1:8001` |
| MySQL no arranca o rechaza la clave tras cambiar `.env` | El volumen guarda la clave de la primera vez: `docker compose ... down -v` y vuelve a levantar (borra los datos de prueba) |
| Cambiaste el SQL y no se nota | Solo se carga la primera vez: `down -v` y levantar de nuevo |
| «tutor_educa_produccion.sql is a directory» | Levantaste Docker antes de generar el SQL. `down -v`, borra esa carpeta, ejecuta el paso 2 y reintenta |

Para empezar de cero: `docker compose -f docker-compose.yml -f docker-compose.local.yml down -v`.

### Las pruebas unitarias (sin Docker)

```powershell
pip install -r requirements.txt -r backend\requirements.txt
python -m unittest discover pruebas          # ~150 pruebas (una se omite si no hay MySQL local)
python -m unittest pruebas.test_backend pruebas.test_cliente_http     # solo backend y cliente

# Prueba del panel web en un navegador simulado (opcional; necesita Node.js):
cd pruebas\panel ; npm install ; cd ..\..
python -m unittest pruebas.test_panel
```

## Desplegarlo (Lightsail u otro servidor con Docker)

1. Servidor Linux con Docker y un dominio que apunte a su IP. Firewall: solo 80 y 443 (y SSH desde tu IP).
2. `cp backend/.env.ejemplo .env` y completa los valores (secreto, contraseñas, dominio).
3. `python herramientas/generar_sql_mysql.py --produccion` → crea `database/tutor_educa_produccion.sql`
   (tablas y materia, **sin cuentas de prueba**).
4. `docker compose up -d --build`
5. Crea el colegio y las primeras cuentas, **sin contraseñas**: cada comando muestra un código de invitación que se
   entrega a la persona (ver «Perfiles, cuentas e invitaciones»):

```bash
docker compose exec api python -m backend.crear_colegio "Colegio San Andrés"
docker compose exec api python -m backend.crear_usuario superadmin plataforma@tutoreduca.cl "Equipo Tutor Educa" --invitacion
docker compose exec api python -m backend.crear_usuario admin directora@colegio.cl "Marta Rojas" --colegio-id 1 --invitacion
```

   La directora crea después a sus docentes, y cada docente a sus estudiantes y apoderados, desde la API (y pronto desde el
   panel y la app). Sin `--invitacion`, la consola pide una contraseña por teclado.

6. En la app: `{ "servidor": { "motor": "http", "url": "https://api.tu-dominio.cl" } }`.

> **Qué está probado.** El backend en modo producción, el SQL de producción y la migración se probaron contra MariaDB
> 10.11, y `herramientas/probar_docker.py` se ejecutó en Docker Desktop con MySQL 8.4 (27 de 28 comprobaciones; la
> restante era un error de `/salud` ya corregido, ver `PENDIENTES.md`). Todavía no se ha probado en un servidor real
> de Lightsail. El paquete `cryptography` de `backend/requirements.txt` es necesario para la autenticación por
> defecto de MySQL 8.

## Variables de entorno

Ver `backend/.env.ejemplo`. Las demás tienen valores por defecto razonables: `TUTOR_MINUTOS_ACCESO`,
`TUTOR_DIAS_RENOVACION`, `TUTOR_IA_MODELO`, `TUTOR_IA_MAX_TOKENS`, `TUTOR_PANEL` (`0` apaga el panel web),
`TUTOR_CONFIAR_PROXY` (ya activo en Docker, porque Caddy va delante).

## Límites conocidos (ver PENDIENTES.md)

- Los límites de intentos y de uso de la IA viven en memoria: sirven para **una** instancia del servidor.
- El celular aún arma las instrucciones de la IA con los datos del estudiante y las envía; lo ideal es que el servidor
  las arme él mismo.
- La sesión de renovación se guarda en la base local del teléfono; lo ideal es el almacén seguro de Android.
- El panel web (`/panel`) aún no tiene **autenticación de dos pasos** ni envío del código por correo (el administrador
  lo entrega a mano): ver `PENDIENTES.md`. Conviene tenerlo detrás de HTTPS (Caddy ya lo hace) antes de abrirlo a internet.

## Calendario: asistencia diaria, eventos y feriados

| Qué | Dónde |
|---|---|
| Reglas (domingo nunca, sábado opcional, feriados, porcentaje) | `services/calendario.py` (Python puro: lo usan la app, el servidor y las pruebas) |
| Tablas | `asistencia_dias` (días con lista), `asistencia` (solo los ausentes), `eventos`, y `cursos.clases_sabado` |
| Migración para una base MySQL existente | `database/migracion_calendario.sql` (ejecutar una vez; SQLite se actualiza sola) |
| Cambios que manda la app (`POST /cambios`) | `asistencia_dia`, `evento`, `evento_baja`, `curso_sabado` (solo la docente del curso; el servidor vuelve a validar las reglas) |
| Administración (`/admin/...`) | `GET/POST /admin/eventos`, `DELETE /admin/eventos/{id}`, `POST /admin/eventos/feriados` (`{"anio": 2027}`, repetible), y `clases_sabado` en `PATCH /admin/cursos/{id}` |
| Panel web | pestaña **Calendario** y casilla «clases los sábados» al editar un curso |

El paquete (`GET /paquete`) incluye solo los días con lista de los cursos de la persona, las inasistencias de sus
estudiantes y los eventos de su colegio (los de todo el colegio y los de sus cursos). Los feriados de Chile están
precargados para 2026 y 2027 y hay que **revisarlos cada año** con la ley vigente. El servidor necesita la base de zonas
horarias para saber «qué día es hoy» en Chile (`tzdata` en `requirements.txt`; si falta, usa un cálculo de respaldo).

### Reloj del servidor

El «hoy» y la hora de registro de la asistencia y de los eventos los pone **el servidor** (hora de Chile), nunca el
teléfono. Para no confiar a ciegas en su propio reloj, el servidor guarda en la tabla `estado_servidor` la **última hora
que vio** (como máximo una escritura por minuto). Si de pronto su reloj marca una hora anterior en más de 10 minutos
(reinicio, corte de luz, pila agotada), **no registra asistencia**: responde 503 y la lista queda en el teléfono hasta que
se corrija. Código: `backend/reloj.py`.

| Qué | Dónde |
|---|---|
| Migración para una base MySQL existente | `database/migracion_reloj.sql` (ejecutar una vez, después de `migracion_calendario.sql`) |
| Estado del reloj (administradores) | `GET /admin/servidor/hora`; también se ve en el panel, pestaña **Calendario** |
| Confirmar la hora (solo superadministrador) | `POST /admin/servidor/hora/confirmar`: para cuando el reloj estaba adelantado, ya se corrigió y la marca quedó en el futuro |
| En la instalación | activar la sincronización automática de hora (`timedatectl` → «System clock synchronized: yes») |

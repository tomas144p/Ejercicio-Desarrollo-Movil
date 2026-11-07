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
| `GET /paquete` | Los datos que le corresponden a la persona según su perfil |
| `POST /cambios` | Un cambio hecho en el celular (intento, aviso, desbloqueo, «Recibido»), **revisado** antes de aplicarse |
| `POST /ia/chat` | Pregunta al tutor IA (la clave vive solo aquí, con límites de uso) |

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

## Desplegarlo (Lightsail u otro servidor con Docker)

1. Servidor Linux con Docker y un dominio que apunte a su IP. Firewall: solo 80 y 443 (y SSH desde tu IP).
2. `cp backend/.env.ejemplo .env` y completa los valores (secreto, contraseñas, dominio).
3. `python herramientas/generar_sql_mysql.py --produccion` → crea `database/tutor_educa_produccion.sql`
   (tablas y materia, **sin cuentas de prueba**).
4. `docker compose up -d --build`
5. Crea las primeras cuentas (te pide la contraseña por teclado):

```bash
docker compose exec api python -m backend.crear_usuario docente carolina@colegio.cl "Carolina Fuentes" \
        --curso "7° Básico B" --nivel "7° Básico"
docker compose exec api python -m backend.crear_usuario apoderado andres@correo.cl "Andrés Morales"
docker compose exec api python -m backend.crear_usuario estudiante sofia@correo.cl "Sofía Morales" \
        --curso-id 1 --apoderado andres@correo.cl
```

6. En la app: `{ "servidor": { "motor": "http", "url": "https://api.tu-dominio.cl" } }`.

> El `docker-compose.yml` y el `Dockerfile` **todavía no se han probado en un servidor real** (en el entorno donde
> se escribieron no había Docker). Pruébalos primero en tu PC o en una instancia de prueba antes del piloto.

## Variables de entorno

Ver `backend/.env.ejemplo`. Las demás tienen valores por defecto razonables: `TUTOR_MINUTOS_ACCESO`,
`TUTOR_DIAS_RENOVACION`, `TUTOR_IA_MODELO`, `TUTOR_IA_MAX_TOKENS`, `TUTOR_CONFIAR_PROXY` (ya activo en Docker, porque
Caddy va delante).

## Límites conocidos (ver PENDIENTES.md)

- Los límites de intentos y de uso de la IA viven en memoria: sirven para **una** instancia del servidor.
- El celular aún arma las instrucciones de la IA con los datos del estudiante y las envía; lo ideal es que el servidor
  las arme él mismo.
- La sesión de renovación se guarda en la base local del teléfono; lo ideal es el almacén seguro de Android.
- Todavía no hay varios colegios ni administradores: ver pasos 3 y 4 del plan.

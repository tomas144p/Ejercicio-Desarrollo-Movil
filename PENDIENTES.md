# PENDIENTES: Tutor Educa, camino al primer Release

Actualizado: 17 de noviembre de 2026 (tarea 22 implementada; ordenado por prioridad; tareas 22 a 35 agregadas)
Decisión: se abandona la etapa MVP y se empieza a preparar un despliegue temprano (piloto real con un colegio).

**Cómo leer este documento**
- **Prioridad:** P0 = bloquea todo lo demás · P1 = necesario para el piloto · P2 = importante, puede ir justo después · P3 = mejora.
- **Disponibilidad:** *Ahora* = se puede hacer ya con lo que tenemos · *Necesita…* = depende de algo externo o de una decisión.

---

## 1. Hoja de ruta ordenada por prioridad

Orden: primero lo que tiene fecha límite y luego P0 a P3. Dentro de P1 van primero las pendientes y después las ya hechas. Las tareas con ✅ conservan puntos abiertos en su detalle.

| # | Tarea | Prioridad | Estado |
|---|---|---|---|
| 22 | Métricas de uso y desempeño del estudiante | P1 | ✅ Hecho el 17/11 (falta probar en celular real) · plazo: semana del 23/11 |
| 1 | Unificar la versión V3 con la de tu compañero (ALT) | P0 | ✅ Hecho (quedan 2 puntos) |
| 2 | Servidor propio (API) entre la app y la base de datos | P0 | ✅ Primera versión hecha (quedan puntos) |
| 3 | Varios colegios en una misma base de datos | P0 | ✅ Hecho (quedan puntos) |
| 9 | APK de prueba en celulares reales | P1 | Pendiente · el mayor riesgo hoy |
| 8 | Despliegue en AWS Lightsail | P1 | Pendiente (necesita 2 y 6) · con estimación de costos |
| 6 | Seguridad y protección de datos | P1 | Parcial: varios puntos ya cumplidos |
| 7 | Datos locales y sincronización | P1 | Parcial |
| 32 | Términos de uso (EULA) y declaración de uso de IA | P1 | Pendiente · textos listos antes del piloto; implementar en el Release |
| 13 | Piloto con un colegio | Meta | Necesita 8, 9, 32 y los consentimientos |
| 4 | Roles de administrador y superadministrador (incluye el panel web) | P1 | ✅ Hecho (falta autenticación de dos pasos y correo) |
| 5 | La docente agrega y da de baja estudiantes y apoderados | P1 | ✅ Hecho (falta probar en celular real) |
| 14 | Selector de curso para docentes con más de un curso | P1 | ✅ Hecho (falta probar en celular real) |
| 15 | Aviso automático al desbloquear una actividad | P1 | ✅ Hecho (falta probar a mano) |
| 16 | Accesos rápidos y ayudas para el docente | P1 | ✅ Hecho (falta validar con docentes) |
| 20 | Calendario de asistencia (sábados opcionales, nunca domingo) | P2 | Pendiente · necesita base de datos |
| 24 | Calendario de eventos y feriados (los feriados no cuentan asistencia) | P2 | Pendiente · junto con la 20 |
| 18 | Notas manuales con ponderación (porcentajes) | P2 | Pendiente · necesita base de datos |
| 19 | Calculadora de notas con exigencia variable | P2 | Pendiente · no necesita base de datos |
| 23 | Notificaciones de recordatorio | P2 | Pendiente · se apoya en 24 y 11 |
| 11 | Notificaciones a apoderados | P2 | Pendiente · necesita el servidor en internet |
| 10 | Contenido por asignaturas como paquetes descargables | P2 | Pendiente · base de 33 y 34 |
| 33 | Completar las otras materias con contenido, por fases | P2 | Pendiente · hoy solo hay 7 temas de Matemáticas |
| 34 | Contenido editable, legible y enviable (formato) | P2 | Pendiente · revisado: está en un archivo Python |
| 26 | Accesibilidad para tipos de daltonismo | P2 | Pendiente · la escala rojo/verde es el riesgo |
| 27 | Tamaño de la interfaz ajustable | P2 | Pendiente |
| 12 | Accesibilidad y pulido para apoderados | P2 | Continuo |
| 17 | Colores y claridad de acciones en la vista del docente | P2 | En pausa hasta tener más feedback de profesores |
| 21 | Análisis: subida y bajada de archivos (PDF, presentaciones) | P3 | Primero analizar; no implementar aún |
| 25 | Modo oscuro (opcional) | P3 | Pendiente · base común: pantalla de Ajustes |
| 28 | Skins de temporada (opcional) | P3 | Pendiente |
| 29 | Botones con sonido (opcional) | P3 | Pendiente |
| 30 | Animaciones y transiciones (opcional) | P3 | Pendiente |
| 31 | Botón «Desactivar todas las modificaciones visuales» | P3 | Solo si se hacen 2 o más de 25, 28, 29 y 30 |
| 35 | Tutor Educa personal, sin colegio | P3 | Idea para después del piloto |

## 2. Detalle por tarea (en el mismo orden de la tabla)

---

#### PARA ESTA SEMANA · con fecha límite

### 22. Métricas de uso y desempeño del estudiante (P1) ✅ Hecho el 17/11 · Plazo: semana del 23 de noviembre · Pedido 17/11
Para una actividad de la Universidad. Sirve además para ver el **efecto real de Tutor Educa en cada estudiante, sea positivo o negativo**. Capturas y un CSV de ejemplo en `capturas/metricas/`.
- [x] **Promedio inicial**: la **primera nota del semestre** de Matemáticas (se avisa en pantalla que es eso). Semestres: marzo a julio y agosto a diciembre; enero y febrero cuentan como vacaciones.
- [x] **Promedio final**: el promedio del semestre a la fecha.
- [x] **Comparación**: variación entre inicial y final con **palabra, ícono y color** («Mejorando», «Bajando», «Estable»; no solo color). Con menos de 3 notas se muestra «datos insuficientes».
- [x] **Porcentaje de aciertos del primer intento**: el porcentaje del primer intento de cada tema, promedio por estudiante y por curso. Además, la **mejora por práctica** (del primer al último intento de cada tema) en el CSV.
- [x] **Uso**: pruebas rendidas, temas trabajados, días con actividad y fecha de la última actividad.
- [x] **Registro de crasheos con su causa**: se capturan los errores de la interfaz y de cualquier hilo, y se guarda fecha y hora, versión, plataforma, pantalla, tipo de error, mensaje limpio y traza resumida (archivo, línea y función, sin el código). **Sin datos personales**: se limpian correos, tokens, claves, RUT, teléfonos, rutas con nombre de usuario y textos entre comillas; el servidor lo vuelve a limpiar y toma el colegio y el perfil de la sesión.
  - [x] La persona ve «Algo salió mal. Ya quedó registrado y puedes seguir usando la app» y la app sigue; si falla más de 5 veces en 30 segundos, se deja cerrar.
  - [x] El mismo error seguido se guarda una vez por minuto; máximo 50 esperando en el teléfono, 500 al día por colegio y se borran a los 90 días. No cuentan como «cambios pendientes».
  - [x] **Cierres inesperados**: si la app se cerró sin avisar (sistema, memoria, fallo nativo), al abrirla se registra un `CierreInesperado` con la última pantalla. Es una señal, no una certeza.
  - [x] Visible en el **panel web, pestaña Errores**, agrupado por causa (cuántas veces, dónde, versión y traza); el admin ve su colegio y la superadmin, todos o uno. También `GET /admin/errores`.
- [x] **Quién ve qué**: la docente, por estudiante (ficha) y por curso («Mi curso»); el apoderado, solo lo de su estudiante, con lenguaje amable.
- [x] **Cuidado al interpretar**: el texto acompaña la variación con cuánto practicó y nunca afirma una causa. En el curso se compara «con práctica» (3 o más pruebas) y «sin práctica» solo si hay al menos 3 estudiantes en cada grupo.
- [x] **Exportar a CSV** por curso, con nombres o **anónimo** («Estudiante 01»…), que abre directo en Excel en español (separador `;`, decimales con coma).
- [x] Base de datos: **tabla nueva `errores_app`** (con índices). Instalaciones nuevas: ya viene en `tutor_educa_mysql.sql` y `tutor_educa_produccion.sql` (regenerados). **Base MySQL existente: ejecutar `database/migracion_errores.sql` una vez.** El servidor de demostración (SQLite) la crea sola. Los promedios, aciertos y uso se calculan y no necesitan columnas.
- [x] Pruebas: 57 nuevas (métricas, semestres, textos, CSV, limpieza de datos personales, huella de la causa, cola local, cierres inesperados, manejador de Kivy, permisos y aislamiento entre colegios, tope y borrado, panel web). Total: 217 pruebas pasando (1 se omite sin MySQL local). El recorrido con la app real comprueba que un error simulado se registra sin datos personales y la app sigue.
- [x] Se corrigió de paso una condición de carrera del panel web (cambiar de sección mientras otra cargaba).
- [ ] **Probar en un celular real**: la captura de errores, los cierres inesperados (pausa y reanudación) y la exportación.
- [ ] **Compartir el CSV desde Android** (hoy el archivo queda dentro de la app; en computador queda en la carpeta de datos de la app y se muestra su ruta).
- [ ] **Promedio inicial registrado** (campo opcional al agregar al estudiante), para cuando no sirva la primera nota.
- [ ] **Semestre configurable por colegio** (hoy es fijo: marzo a julio y agosto a diciembre).
- [ ] **Tiempo de estudio**: la duración de cada prueba se guarda solo en el teléfono, no en el servidor; para mostrarlo habría que subirla.
- [ ] **Acierto por pregunta** (si acertó a la primera cada pregunta): requeriría guardar las respuestas. Hoy se usa el resultado del primer intento de cada tema.
- [ ] Revisar con **datos reales de un curso** para ver si la lectura (frases y umbrales) les parece útil a las docentes.
- [ ] Antes de **compartir** un error con otras personas, revisar el mensaje: la limpieza es automática, pero un nombre dentro de un texto largo puede escaparse.

---

#### PRIORIDAD P0 · base del sistema (hechas, con puntos pendientes)

### 1. Unificar ALT + V3 (P0) ✅ Hecho
Se tomó ALT como base de carpetas y se portó encima todo lo de V3. Resultado: carpeta `Tutor_Educa_Unificada.zip`.
- [x] `models/modelos.py`: categoría "perfecto" (7,0), redondeo antes de colorear, mensajes amables, `tendencia()`. Se conserva lo de ALT (`duracion_seg`, `fecha_legible`, `to_dict`).
- [x] `views/estilo.py`, `views/componentes.py`, `views/dialogos.py`: colores de nota, flechas de tendencia, leyenda y botones con ícono, ya en KivyMD.
- [x] Pantalla del docente: orden de menor a mayor (o al revés / A–Z), flecha de tendencia, leyenda y "Recibido por X de Y".
- [x] Pantalla del apoderado: mensaje amable bajo el promedio, flechas, leyenda y botón "Recibido" (pulgar arriba). Se quitó "Marcar todos como leídos", porque contradice la confirmación explícita.
- [x] Mejora: el orden de estudiantes salió de la pantalla a `services/ordenamiento.py` (Python puro, con pruebas).
- [x] Pruebas: 30 en total (las de ALT + colores, mensajes, tendencia y orden). Una se omite si no hay MySQL local.
- [x] Recorrido automático de la app en pantalla virtual: todas las pantallas cargan sin errores.
- [x] README actualizado y `.gitignore` agregado (claves locales, bases de datos locales, `__pycache__`).
- [ ] Pendiente: probar el flujo "Recibido" a mano en la app (el recorrido automático no pulsa ese botón) y en un celular real.
- [ ] Pendiente: acordar con el compañero quién toca qué (usar Git con ramas) antes de seguir.

### 2. Backend propio (P0) ✅ Primera versión hecha
Carpeta `backend/` (FastAPI) + cliente en la app. Guía completa en `backend/README.md`.
- [x] API con `/login`, `/renovar`, `/paquete`, `/cambios`, `/ia/chat` y `/salud`; la app usa `ServidorHTTP` con `"motor": "http"` y **ya no lleva usuario ni clave de MySQL**.
- [x] Contraseña verificada en el servidor; tokens de acceso (30 min) y renovación (30 días); mismo mensaje para correo inexistente y contraseña mala; bloqueo tras 5 intentos fallidos.
- [x] Cada cambio se revisa contra el token: nadie actúa en nombre de otro, el docente solo toca sus cursos, el apoderado solo sus hijos, y la nota de una prueba se recalcula en el servidor.
- [x] La clave de la IA vive solo en el servidor, con límite por minuto y por día por persona.
- [x] La app solo acepta `https://` (salvo red local para desarrollo). Los cambios de otra persona del mismo teléfono esperan en la cola hasta que ingrese.
- [x] Modo sin conexión intacto: ingreso con credencial recordada, cola de cambios y reanudación de la sesión al volver internet.
- [x] `Dockerfile`, `docker-compose.yml` (Caddy con HTTPS automático + API + MySQL), SQL de producción **sin cuentas de prueba** y herramienta `python -m backend.crear_usuario`.
- [x] 72 pruebas en total; las nuevas cubren permisos, bloqueo, cuentas desactivadas, renovación, IA y la app completa contra un backend real. Recorrido de la app en modo API sin errores.

**Falta en este paso:**
- [x] **Prueba de Docker ejecutada en Docker Desktop: 27 de 28 comprobaciones pasaron.** Quedó confirmado con contenedores reales: el compose, el Dockerfile, MySQL 8.4 con el SQL de producción, la API en modo producción, la creación de colegios y cuentas, el ingreso, el bloqueo, los permisos y el aislamiento entre colegios. La única falla era un error de `/salud`: si la API arrancaba antes que MySQL (pasa al reiniciar todo junto) no volvía a reportarse sana hasta que otra ruta reintentara la conexión. Corregido, con prueba que lo cubre y comprobado contra MariaDB real.
- [ ] **Volver a correr `python herramientas/probar_docker.py`** con la versión corregida (reconstruir con `docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build`) y confirmar que dan las 28 comprobaciones.
- [ ] **Quitar los modos directos de la versión que se entregue** (`auto`, `mysql`, `demo` y la dependencia PyMySQL en la app) para que sea imposible volver a poner claves de base de datos dentro del APK.
- [ ] **Que el servidor arme las instrucciones de la IA** con los datos que ya tiene (hoy las arma el celular y las envía; el servidor las limita, pero un usuario podría escribir las suyas).
- [ ] **Guardar la sesión de renovación en el almacén seguro de Android** (hoy queda en la base local del teléfono, igual que la huella de la contraseña).
- [ ] **Límites de intentos en una base compartida** (Redis) cuando haya más de una instancia del servidor; hoy viven en memoria.
- [ ] Pasar la clave de la IA que estaba en `config.local.json` a la variable `TUTOR_IA_API_KEY` del servidor, y **revocar cualquier clave que ya se haya usado dentro de un APK**.
- [ ] Subir las iteraciones de la contraseña (hoy 120.000) o pasar a argon2 cuando se revise el rendimiento en celulares modestos.

### 3. Multi-colegio (P0) ✅ Hecho
Una sola base de datos con separación por colegio, hecha cumplir en el servidor. Guía en `backend/README.md`.
- [x] Tabla `colegios`; `colegio_id` en cuentas y cursos (en cursos es obligatorio: la base rechaza un curso sin colegio). Estudiantes, notas, avisos, intentos y refuerzos quedan en el colegio de su curso.
- [x] El servidor toma el colegio de la cuenta del token (el celular no puede pedir otro) y **cada consulta y cada cambio lo comprueba**, incluso si un dato estuviera mal enlazado entre colegios.
- [x] Cuenta sin colegio o colegio suspendido: no ingresa y las sesiones abiertas dejan de servir. Si alguien cambia de colegio, su sesión anterior se invalida.
- [x] `python -m backend.crear_colegio` (crear, listar, suspender, reactivar) y `crear_usuario --colegio-id`; un estudiante toma el colegio de su curso y su apoderado debe ser del mismo.
- [x] Migraciones: las bases SQLite (teléfono y demostración) se actualizan solas; para MySQL, `herramientas/generar_sql_mysql.py --migracion`.
- [x] La app guarda el colegio y lo muestra en el encabezado de cada pantalla.
- [x] 89 pruebas. Las de aislamiento crean un segundo colegio y provocan fugas a propósito; además **rompí los filtros a propósito** y las pruebas fallaron, así que sí detectan una fuga.
- [x] **Probado contra un MariaDB 10.11 real**: SQL de producción (sin cuentas, se puede importar dos veces), migración sobre la base MySQL antigua de la versión 0.3 y el flujo completo del backend en modo producción con dos colegios.

**Falta en este paso:**
- [x] SQL confirmado en **MySQL 8.4** (el del `docker-compose.yml`) con tu ejecución de `probar_docker.py`.
- [ ] Decidir si hace falta **restricción en la base de datos** (llaves compuestas o disparadores) para impedir enlaces entre colegios; hoy lo impiden las altas por herramienta y los filtros del servidor, pero no la base misma.
- [ ] Materia **propia de cada colegio** (hoy la materia es común a todos).
- [ ] **Correo único en todo el sistema**: la misma persona no puede estar en dos colegios con el mismo correo. Decidir si hace falta (por ejemplo, apoderados con hijos en dos colegios).
- [ ] Registro de auditoría con el colegio de cada acción (hoy se registra en el log del servidor).

---

#### PRIORIDAD P1 · necesarias para el piloto

### 9. APK de prueba en celulares reales (P1, Ahora)
- [ ] Empaquetar con Buildozer (incluyendo KivyMD y las fuentes).
- [ ] Probar en al menos un Android modesto: rendimiento, teclado, botón atrás, sin conexión.
- [ ] Revisar tamaño del APK y tiempos de arranque.
- [ ] Ícono, nombre, permisos mínimos y firma de la versión.

### 8. Despliegue en AWS Lightsail (P1, necesita 2 y 6)
Solo si se confirma Lightsail (hoy se evalúa por los 100 USD de crédito).
- [ ] Instancia Linux pequeña con IP estática; firewall solo 80/443 y SSH restringido a una IP.
- [ ] Base de datos administrada con respaldos, accesible solo por red privada.
- [ ] Dominio y certificado HTTPS.
- [ ] Contenidos pesados en almacenamiento de objetos (S3) y no en el disco de la instancia.
- [ ] Alerta de costos para cuidar el crédito.
- [ ] Todo en Docker para poder migrar cuando se acabe el crédito.
- [ ] **Estimación de costos (17/11), un colegio de 5° a 8° con secciones A y B (8 cursos, unas 600 personas):** de **USD 32 a 50 al mes** en AWS con todas las funcionalidades (instancia de 2 GB o 4 GB, base de datos administrada de USD 15, almacenamiento de archivos, respaldos y dominio). Los créditos nuevos de AWS alcanzan para **unos 2 a 3 meses (USD 100)** o **4 a 6 meses (USD 200)**, y vencen a los 6 meses. El uso de la **IA se paga aparte** (Anthropic), de unos USD 30 a 90 al mes con uso normal. **Verificar los precios en la calculadora de AWS** y en la región elegida.

### 6. Seguridad y protección de datos (P1, en paralelo)
- [ ] HTTPS obligatorio; la base de datos nunca expuesta a internet.
- [x] Permisos verificados en **cada** endpoint del servidor, no solo ocultando botones (hecho en las tareas 2 a 5, con pruebas que rompen las reglas a propósito).
- [x] Limitar intentos de login y bloquear temporalmente (5 intentos por correo; también por IP y para los códigos de invitación).
- [ ] Registro de accesos y cambios sensibles (auditoría).
- [x] Secretos fuera del código (variables de entorno del servidor); `config.local.json` fuera de Git (`.gitignore`).
- [ ] Respaldos automáticos y prueba de restauración.
- [ ] Minimizar datos: guardar solo lo necesario de menores.
- [ ] Revisar obligaciones de la Ley 21.719 (protección de datos personales, Chile) y preparar consentimiento de apoderados y colegio.
- [ ] Revisar dependencias antes de publicar.

### 7. Datos locales y sincronización (P1, después del 2)
- [ ] SQLite local como **caché** de lo que el usuario ya ve (sus cursos, notas, avisos), no como copia de todo el colegio.
- [x] Cola de cambios pendientes ("Recibido", intentos) que se envía al volver la conexión (hecho en la tarea 2).
- [ ] Token guardado en almacenamiento seguro del dispositivo, no en archivos planos.
- [ ] Al cerrar sesión o cambiar de usuario: borrar la caché local.
- [ ] Revisar `services/sincronizacion.py` y `almacen_json.py` (ALT) para alinearlos con el servidor.

### 32. Términos de uso (EULA) y declaración de uso de IA (P1 para el Release) · Pedido 17/11
**Tener listo antes del piloto; implementar en el Release.** El piloto (tarea 13) necesita consentimientos, así que los textos no pueden esperar.
- [ ] **Documentos en lenguaje simple:** Términos de uso (EULA), Política de privacidad (Ley 21.719: qué datos se guardan, para qué, quién los ve, por cuánto tiempo y los derechos de acceso, corrección y eliminación), consentimiento informado de apoderados y colegio (hay menores) y **licencias de código abierto** (Kivy, KivyMD, FastAPI, etc.).
- [ ] **Declaración de uso de IA en el desarrollo, pública y visible, no secreta:** Tutor Educa se desarrolló con apoyo de inteligencia artificial (Claude, de Anthropic) para escribir y revisar código, pruebas y documentación; las decisiones del producto son del equipo y el resultado se revisa con pruebas automáticas y por personas. Va en la pantalla «Acerca de», en el EULA y en el README de GitHub. Que el equipo revise que el texto describa con exactitud cómo se trabajó.
- [ ] **Declaración de uso de IA dentro de la app:** el tutor IA usa Claude (Anthropic), puede equivocarse y no reemplaza a la docente. Declarar **exactamente qué datos se envían** al proveedor y confirmar que no viajan nombres ni correos.
- [ ] **Pantalla antes del primer uso**: texto resumido, casilla de aceptación y enlace al texto completo.
- [ ] Guardar en el servidor la **versión** del documento, la fecha y quién aceptó (tabla `aceptaciones`), y pedir aceptar de nuevo si el documento cambia.
- [ ] Estudiantes menores: definir quién acepta (el apoderado o el colegio) y cómo se integra con el código de invitación.
- [ ] Disponible siempre en Ajustes («Términos y privacidad», «Acerca de»).
- [ ] **Revisión por una persona con conocimiento legal** antes de publicarlo. Yo puedo preparar un borrador como punto de partida, pero no soy abogado y no reemplaza esa revisión.

### 13. Piloto con un colegio (meta)
- [ ] Elegir un colegio y un curso, y acordar alcance y duración.
- [ ] Consentimientos informados (colegio y apoderados).
- [ ] Plan de soporte: a quién reportan problemas.
- [ ] Qué se mide: uso, avisos recibidos, notas, errores.

### 4. Roles nuevos (P1) ✅ API, reglas y panel web hechos
Perfiles **superadmin** (plataforma) y **admin** (un colegio), con cuentas por **código de invitación**. Guía en `backend/README.md`.
- [x] Perfiles `admin` y `superadmin`; los administradores usan el panel web y **no la app** (la API les responde 403 en `/paquete`, `/cambios` y el tutor IA, y la app se lo explica).
- [x] Cuentas **sin contraseña**: nacen pendientes y se activan con un código de un solo uso (`ABCDE-FGHJK`, vence a los 7 días, solo se guarda su huella, se muestra una vez). Nadie conoce ni reparte la contraseña de otro. `POST /activar` deja a la persona dentro.
- [x] Recuperar el acceso: el administrador (o la docente, para sus estudiantes y apoderados) genera un código nuevo; la contraseña anterior deja de servir y los códigos viejos mueren.
- [x] Rutas `/admin/...`: colegios (solo superadmin), cuentas, cursos, cambiar docente de un curso, baja/alta, reinicio de acceso. Solo dentro del colegio de quien actúa; la superadmin ve todos.
- [x] Reglas probadas, incluso **rompiéndolas a propósito**: un admin no crea ni toca a otros admins; la superadmin solo se crea desde la consola; el admin no ve otro colegio; adivinar códigos se bloquea; los registros de auditoría no contienen códigos.
- [x] La consola (`crear_usuario`, `crear_colegio`) sigue sirviendo para el primer arranque, con `--invitacion`.
- [x] Migración SQL para bases MySQL existentes (`--migracion-roles`), probada sobre la base antigua real en MariaDB; la base de demostración antigua se aparta y se recrea sola.
- [x] **Panel web** para superadmin y admin, servido por la propia API en `/panel` (sin librerías ni servicios externos). Guía en `backend/README.md`.
  - [x] **Personas**: lista con filtros por perfil, curso y búsqueda (sin tildes); crear docente (con su primer curso), estudiante (con apoderado nuevo o existente), apoderado y, la superadmin, administradores; **código de invitación con mensaje listo para copiar**; código nuevo; desactivar y reactivar (avisa si la docente tiene cursos a cargo); editar nombre, curso y apoderado de un estudiante.
  - [x] **Cursos**: crear, cambiar nombre, nivel o docente a cargo.
  - [x] **Colegios** (solo superadmin): crear, renombrar, suspender y reactivar; crear el primer administrador de cada colegio.
  - [x] **«Tengo un código»**: así activa su cuenta cada administrador nuevo. Si una docente, estudiante o apoderado/a lo usa por error, su cuenta queda activada y se le indica que ingrese desde la app.
  - [x] Seguridad: política CSP estricta (solo scripts y estilos propios, sin `inline`), solo se sirven 3 archivos, todo texto se muestra como texto (probado con un nombre con HTML), el código se muestra una sola vez, sesión de renovación en `sessionStorage` y cierre a los **20 minutos** sin actividad. Se puede apagar con `TUTOR_PANEL=0`.
  - [x] Pruebas: 8 nuevas en `pruebas/test_panel.py` (cabeceras, lista blanca de archivos, sin código inseguro, `limite` de la API) y un **recorrido completo en un navegador simulado** (jsdom: `cd pruebas/panel && npm install`) con administrador y superadmin contra un servidor real. Total: 160 pruebas pasando (1 se omite sin MySQL local). Se comprobó que el recorrido falla si se introduce un defecto a propósito.
  - [ ] **Mirarlo en un navegador real** (computador y celular): el diseño (CSS) no se pudo ver aquí, solo se probó la lógica. Ajustar lo que se vea mal.
  - [ ] **Paginación** de la lista de personas (hoy muestra hasta 1000 y pide usar los filtros; sobra para un colegio, no para cientos).
  - [ ] **Desvincular o reasignar docentes** al desactivar a una con cursos (hoy solo avisa y se cambia en Cursos).
  - [ ] **Registro de actividad** visible en el panel (hoy solo está en el log del servidor).
  - [ ] **Importar estudiantes desde Excel/CSV** (útil cuando un colegio llega con 200 estudiantes).
- [ ] **Envío del código por correo** (hoy el administrador lo entrega a mano). Necesita decidir un servicio de correo.
- [ ] **«Olvidé mi contraseña» sin pasar por un administrador** (autoservicio por correo). Hoy lo reinicia el colegio.
- [ ] **Cambiar la contraseña desde la app** estando dentro.
- [ ] Autenticación de dos pasos para administradores (recomendable antes de abrir el panel a internet).

### 5. Gestión de estudiantes y apoderados (P1) ✅ Hecho (API y pantallas de la app)
La docente gestiona a sus estudiantes y las familias activan sus cuentas, todo desde la app. Capturas del recorrido real en `capturas/gestion/` (`herramientas/capturar_gestion.py`).
- [x] La docente agrega estudiantes a SUS cursos, con apoderado nuevo (se crea) o ya existente (se vincula; no se le toca la contraseña). Recibe un código por cada cuenta nueva, con un botón para **copiar un mensaje listo para WhatsApp o correo**.
- [x] Cambia a un estudiante de curso (solo entre los suyos), cambia o quita su apoderado (un apoderado puede tener varios hijos), genera un código nuevo para el estudiante o su apoderado.
- [x] **Baja = desactivar, nunca borrar**: el estudiante sale de las listas de su docente y de su apoderado, su sesión deja de servir y se conserva su historial. Se ve en «Dados de baja» y se **reactiva** desde ahí.
- [x] **Pantalla «Tengo un código de invitación»** en el ingreso: correo + código + contraseña nueva, y la persona queda dentro.
- [x] **El teléfono olvida lo que el colegio retira** (estudiante dado de baja o movido, curso reasignado): sus datos y sus notas se borran de la copia local. Antes se quedaban guardados para siempre; las pruebas lo detectaron.
- [x] No puede salirse de sus cursos ni de su colegio, ni crear docentes, ni tocar cuentas ajenas; campos desconocidos se rechazan. Necesita conexión: sin ella, la app lo explica y no deja nada a medias.
- [ ] **Compartir el código directo por WhatsApp** (hoy se copia el mensaje y se pega) y mostrarlo como **QR**.
- [ ] Mostrar quién **aún no activó su cuenta** en la lista del curso (para hacer seguimiento a las familias).
- [ ] **Carga masiva** de estudiantes desde una planilla (útil para un curso de 40).
- [ ] Pantalla para **cambiar la contraseña** estando dentro de la app.
- [ ] **Eliminar datos personales a pedido** (derecho de eliminación, Ley 21.719): hoy la baja solo desactiva. Definir el proceso (anonimizar notas, plazos de conservación).
- [ ] Probar las pantallas nuevas **en un celular real** (se probaron con la app real en pantalla virtual).

### 14. Selector de curso para docentes con más de un curso (P1) ✅ Hecho · Feedback profesor 15/11
Los profesores con más de un curso ahora eligen el curso ANTES de ver la lista de estudiantes. Capturas en `capturas/selector_curso/`.
- [x] Pantalla de selección con una tarjeta por curso: nombre, nº de estudiantes, cuántos están bajo 5,0 y cuántos no tienen apoderado. Los cursos con más estudiantes en riesgo aparecen primero.
- [x] Con un solo curso no cambia nada: entra directo, sin selector.
- [x] En «Mi curso», «Temas» y «Avisos» aparece el curso actual con el botón **«Cambiar curso»**; el subtítulo de la pantalla también muestra el curso.
- [x] Al cambiar de curso se limpian el filtro, la pestaña y el destinatario del aviso en borrador (era un estudiante del curso anterior); el título y el texto del borrador se conservan.
- [x] Si el curso elegido deja de ser suyo (reasignación), vuelve a elegir.
- [x] Lógica en `services/cursos.py` (Python puro) con pruebas; nueva prueba con una docente de dos cursos. Total: 145 pruebas pasando (1 se omite sin MySQL local). El recorrido automático de la app termina sin errores.
- [ ] **Recordar el último curso abierto** entre sesiones (hoy lo recuerda mientras la sesión está abierta).
- [x] Cada tarjeta del selector muestra cuántos **avisos siguen sin «Recibido»** (hecho junto con la tarea 16).
- [ ] Probar con una docente real con 2 o 3 cursos y en un celular real.

### 15. Aviso automático al desbloquear una actividad (P1) ✅ Hecho · Feedback profesor 15/11
Antes, el mensaje adicional al desbloquear solo se veía dentro de «Refuerzos»; no aparecía en «Avisos» del apoderado. Ahora cada desbloqueo deja un aviso.
- [x] Al desbloquear (con o sin mensaje) se crea un **aviso de tipo «Refuerzo»** en Avisos del apoderado, con el botón «Recibido». Vale para el desbloqueo desde la lista del curso y desde la ficha de un estudiante.
- [x] Texto automático («Se liberó el tema «X» para…, puede repasarlo desde su app, incluso sin internet»); si la docente escribe un mensaje, se agrega como «Mensaje de la docente».
- [x] Si se desbloquea para **todo el curso**, se envía **un solo aviso** al curso; si es para un grupo (ej. «Necesitan refuerzo»), un aviso por estudiante, con su nombre.
- [x] No se duplica: si el estudiante ya tenía el tema activo, no recibe otro aviso.
- [x] Los diálogos del docente ahora dicen que las familias reciben un aviso automático, y la confirmación indica que se avisó.
- [x] Funciona sin conexión: el aviso entra a la cola de cambios como cualquier otro y se envía al volver internet (el servidor ya validaba el tipo «refuerzo» y que el curso sea del docente).
- [x] La docente ve cada aviso en su pestaña Avisos, con «Recibido por X de Y».
- [x] Pruebas nuevas: grupo parcial, curso completo, sin duplicados, sin aviso si se pide expresamente, y la familia lo ve en sus Avisos. Total: 139 pruebas pasando (1 se omite sin MySQL local).
- [x] Desde el aviso, el apoderado tiene un botón **«Ver refuerzos»** que lo lleva a esa pestaña.
- [ ] Que el botón lleve **directo al tema** desbloqueado (hoy lleva a la pestaña Refuerzos; requiere guardar el tema en el aviso).
- [ ] Prueba de aislamiento entre colegios específica para estos avisos (la regla ya existe en el servidor, falta la prueba).
- [ ] Probar **a mano en la app** (el recorrido automático no pulsa estos botones) y en un celular real.
- [ ] Decidir si la docente quiere poder **desactivar** el aviso automático en algún caso (hoy siempre se envía).

### 16. Accesos rápidos y ayudas para el docente (P1) ✅ Hecho · Feedback profesor 15/11
Meta: que la app sea una ayuda y no un trabajo adicional para el profesor. Capturas en `capturas/selector_curso/`.
- [x] Bloque **«Para hoy»** arriba de «Mi curso», con acciones a uno o dos toques:
  - **Desbloquear** el tema sugerido (el que más estudiantes bajo 5,0 todavía no tienen; si hay empate, el primero del programa). Abre el diálogo ya existente con «Necesitan refuerzo» preseleccionado. «Otro tema» lleva a la pestaña Temas.
  - Etiqueta roja si hay estudiantes bajo 5,0 **sin ningún refuerzo**.
  - **Familias sin «Recibido»**: cuenta de los avisos de las últimas dos semanas con confirmaciones pendientes, con botón «Ver avisos».
  - **Aviso rápido al curso**: elige una plantilla, la revisas y la envías en Avisos.
  - Si no hay nada urgente, muestra «Todo al día».
- [x] **Plantillas de aviso** (Evaluación, Refuerzo, Reunión, Felicitación), también disponibles como chips en la pestaña Avisos. Los datos por completar van entre [corchetes] y la app **no deja enviar** el aviso mientras queden sin reemplazar.
- [x] Se mantiene el filtro de estudiantes en riesgo y se suma la ayuda extra: tema sugerido + familias sin «Recibido».
- [x] La fila de tipo de aviso quedó rotulada («Tipo:») para no confundirla con las plantillas.
- [x] Lógica en `services/acciones_docente.py` (Python puro). 152 pruebas pasando (1 se omite sin MySQL local); el recorrido automático termina sin errores.
- [ ] **Validar con 2 o 3 docentes reales**: ¿el tema sugerido les parece útil? ¿Faltan plantillas? ¿Qué otra tarea repetitiva les cuesta?
- [ ] Medir pasos con una docente real (meta: tareas habituales en 2 toques o menos). Hoy: desbloquear = 2 toques + confirmar; aviso rápido = 3 toques + completar datos + enviar.
- [ ] Idea para después: **recordatorio individual** a las familias que no han confirmado «Recibido» (hoy habría que enviar un aviso a todo el curso).
- [ ] Idea para después: plantillas **editables por la docente** o por colegio (requiere guardarlas en la base de datos).

---

#### PRIORIDAD P2 · funcionalidades importantes

### 20. Calendario de asistencia (P2) · Pedido 16/11
Hoy `estudiantes.asistencia` es un número fijo; la inasistencia es el problema de fondo del proyecto, así que conviene registrarla día a día.
- [ ] **Calendario mensual por curso** con la asistencia de cada día.
- [ ] **Días con clases: lunes a viernes. El sábado es opcional y el domingo nunca.** Un **interruptor por curso**: «Este curso tiene clases los sábados» (apagado por defecto). El domingo no se puede marcar, ni desde la app ni desde el servidor.
- [ ] Qué pasa si se apaga el interruptor y ya había sábados marcados: se conserva el historial, se ocultan y no cuentan en el porcentaje.
- [ ] **Feriados y días sin clases**: se resuelven en la tarea 24 (eventos del calendario). Regla decidida: un feriado **no permite marcar asistencia ni cuenta** en el porcentaje.
- [ ] Decidir los estados: presente, ausente y, quizá, **ausente justificado** y atraso.
- [ ] **Pasar lista sin trabajo extra**: todos aparecen presentes y se marcan solo los ausentes (en línea con la tarea 16).
- [ ] El **porcentaje de asistencia se calcula** con los días marcados y reemplaza al número fijo de hoy (compatible con lo que ya existe).
- [ ] Las familias ven la asistencia de su estudiante en un calendario simple de colores, con aviso de **inasistencias seguidas**.
- [ ] Base de datos: tabla `asistencia` (estudiante, fecha, estado), campo de sábados en `cursos` y tabla de días sin clases (con migración para SQLite y MySQL).
- [ ] Fechas **sin hora** y con la zona de Chile, para que un día no se corra por la hora universal; funciona sin conexión.
- [ ] Pruebas: sábado con y sin interruptor, domingo rechazado también por el servidor, porcentaje, permisos y aislamiento entre colegios.

### 24. Calendario de eventos y feriados (P2) · Pedido 17/11
Amplía el calendario de asistencia (tarea 20). Los eventos no están necesariamente ligados a las notas.
- [ ] **Eventos** con título, fecha (o rango de fechas), tipo y descripción. Ejemplos: 16 de septiembre «Celebración de fiestas patrias»; 18 y 19 de septiembre «Feriado».
- [ ] Tipos propuestos: feriado, sin clases, celebración, evaluación, reunión de apoderados y otro. Cada evento indica si **hay clases ese día** o no.
- [ ] **Regla decidida: un feriado no permite marcar asistencia y no cuenta en el porcentaje** (ni a favor ni en contra). La regla la hace cumplir también el servidor.
- [ ] **Quién los maneja**: los docentes (eventos de sus cursos) y los administradores (eventos de todo el colegio). Las familias y los estudiantes solo los ven.
- [ ] **Feriados de Chile precargados**, editables por el administrador. Revisar cada año, porque la ley puede cambiar o mover algún feriado.
- [ ] Un evento con hora o fecha de entrega puede generar un **recordatorio** (tarea 23).
- [ ] Vista de calendario simple para las familias, con colores y textos (no solo color: ver tarea 26).
- [ ] Base de datos: tabla `eventos` (colegio, curso opcional, fechas, tipo, si hay clases, quién lo creó) y migración.
- [ ] Fechas **sin hora** y con la zona de Chile; funciona sin conexión.
- [ ] Pruebas: feriado que bloquea la asistencia, evento de un curso que no se ve en otro, permisos, aislamiento entre colegios.

### 18. Notas manuales con ponderación (P2) · Pedido 16/11
Hoy las notas que se ven salen de las actividades de repaso de Tutor Educa. Esas actividades son para repasar: **no son exámenes formales ni influyen necesariamente en la nota final**. La docente necesita ingresar a mano las evaluaciones que sí cuentan.
- [ ] **Separar el origen de cada nota**: «Repaso Tutor Educa» (no cuenta para la nota final, salvo que la docente decida lo contrario) y «Evaluación» ingresada a mano. Base de datos: columnas de origen y de porcentaje en `calificaciones` (con migración para SQLite y MySQL).
- [ ] **Ingreso manual**: la docente elige curso, asignatura y evaluación (nombre y fecha) y completa una planilla con **una fila por estudiante**. Teclado numérico, acepta coma o punto, rango 1,0 a 7,0.
- [ ] **Sistema de porcentajes**: cada evaluación tiene su % sobre la nota final. La app avisa si los porcentajes de una asignatura no suman 100 % y muestra una nota parcial mientras falten evaluaciones.
- [ ] **Interruptor «todas valen lo mismo»**: reparte el 100 % en partes iguales y lo recalcula al agregar o quitar evaluaciones; la docente puede volver al modo manual.
- [ ] **Promedio final ponderado**, con una regla de redondeo clara (decidir cuántos decimales y cuándo se redondea).
- [ ] Decidir **qué cuenta para «estudiante en riesgo»** (hoy es el promedio de Matemáticas bajo 5,0): propuesta, usar las evaluaciones formales y mostrar los repasos como un indicador aparte.
- [ ] **Familias y estudiantes** ven cada nota con su etiqueta (repaso o evaluación), para no mezclarlas ni asustarse por un repaso.
- [ ] **Seguridad**: solo la docente del curso edita; el servidor valida rango y que el estudiante sea de ese curso; **no se borra**: una nota corregida deja historial (quién y cuándo). Funciona sin conexión con la cola de cambios.
- [ ] Pruebas: suma de porcentajes, igual ponderación, redondeo, permisos y aislamiento entre colegios.
- [ ] Validar con 2 o 3 docentes cómo evalúan realmente (períodos o semestres, notas parciales, decimales).

### 19. Calculadora de notas con exigencia variable (P2) · Pedido 16/11
Fórmula habitual en Chile, con exigencia `e` (por defecto 60 %), puntaje máximo `M` y puntaje obtenido `p`: si `p ≥ e·M`, nota = `4 + 3·(p − e·M) / (M − e·M)`; si no, nota = `1 + 3·p / (e·M)`. Para confirmar con docentes, porque algunos colegios usan otra escala.
- [ ] Calculadora: puntaje máximo, **exigencia variable** (campo o deslizador, 60 % por defecto) y puntaje obtenido → nota.
- [ ] Cálculo inverso: «¿cuántos puntos necesito para un 4,0?» (o para la nota que se elija).
- [ ] **Tabla de puntaje a nota** de toda la prueba, para mirarla o compartirla.
- [ ] Modo docente: ingresar los puntajes de un curso y generar las notas (se conecta con la tarea 18, para no digitar dos veces).
- [ ] Modo familias y estudiantes: «¿qué nota necesito en lo que viene para promediar un 5,0?» (necesita los porcentajes de la tarea 18).
- [ ] Va en `services/` como **Python puro con pruebas** (límites en 1,0 y 7,0, exigencia de 0 % y de 100 %, redondeo). Funciona sin internet y no necesita base de datos.

### 23. Notificaciones de recordatorio (P2) · Pedido 17/11
Ejemplo: «No olvides la maqueta para el 24/11/2026».
- [ ] Un **recordatorio** tiene título, fecha de entrega y curso; lo crea la docente. Decidir si el estudiante o la familia también pueden crear recordatorios propios.
- [ ] Se ve como aviso (tipo «recordatorio») y en el calendario (tarea 24).
- [ ] Notificación en el teléfono **antes de la fecha** (por ejemplo 3 días, 1 día y el mismo día), configurable y desactivable por cada persona.
- [ ] **Sin conexión**: notificaciones locales programadas en el teléfono. En Android 13 o superior hay que pedir el permiso de notificaciones, y las alarmas exactas tienen restricciones: **probar en un celular real**. Las notificaciones push (Firebase) siguen en la tarea 11.
- [ ] **Que no sea excesivo**: máximo por día, hora de silencio en la noche y nada de duplicados.
- [ ] Botón «Listo» que cancela los recordatorios restantes; la docente ve cuántos lo marcaron, como con «Recibido».
- [ ] Si la docente cambia la fecha, se reprograman; si lo borra, se cancelan.
- [ ] Base de datos: decidir entre una tabla `recordatorios` o agregar una fecha límite a los avisos.

### 11. Notificaciones a apoderados (P2, necesita 8)
- [ ] Definir el canal: notificación push (Firebase Cloud Messaging), correo o ambos.
- [ ] Aviso de nuevo mensaje, con el botón "Recibido" para confirmar lectura.
- [ ] Cuidar que no sea excesivo (apoderados con poca experiencia tecnológica).

### 10. Contenido por asignaturas como paquetes (P2)
Hoy `models/contenido/matematicas.py` es un archivo Python grande dentro de la app.
- [ ] Pasar el contenido a archivos de datos (JSON u otro) fuera del código.
- [ ] Estructura propuesta: `/matematicas/algebra/EcuacionesPrimerGrado/` con su contenido.
- [ ] Un `manifest.json` por asignatura/unidad con versión, tamaño y hash de verificación.
- [ ] La app descarga solo las unidades que el usuario va a usar y puede borrarlas.
- [ ] Control de versiones del contenido y actualización incremental.

### 33. Completar las otras materias con contenido predefinido, por fases (P2) · Pedido 17/11
**Hallazgo (17/11):** hoy solo existe **Matemáticas, con 7 temas**: 5 de 7° básico, 1 de 6° y 1 de 8°. **No hay ninguno de 5° básico**, aunque la app se presenta para 5° a 8°.
- [ ] **Primero, completar Matemáticas de 5° a 8°** (hoy falta todo 5° y casi todo 6° y 8°).
- [ ] **Fases por nivel y semestre**; cada fase incluye todas las asignaturas elegidas: Fase 1, 5° 1.er semestre · Fase 2, 5° 2.º semestre · Fase 3, 6° 1.er semestre · Fase 4, 6° 2.º semestre · Fase 5, 7° 1.er semestre · Fase 6, 7° 2.º semestre · Fase 7, 8° 1.er semestre · Fase 8, 8° 2.º semestre.
- [ ] **Decidir qué asignaturas entran en la v1** y en qué orden (Lenguaje, Ciencias Naturales, Historia, Inglés…).
- [ ] Basarse en las **Bases Curriculares y programas de estudio del Mineduc**, anotando el objetivo de aprendizaje de cada tema.
- [ ] Usar la misma **plantilla de tema** de hoy: resumen, contenido, ejemplos resueltos, 5 preguntas, error común y consejo para apoderados.
- [ ] **Proceso de calidad:** redacción (si se usa IA, declararlo según la tarea 32), **revisión por una docente de la asignatura**, respuestas verificadas, lenguaje simple y prueba con estudiantes.
- [ ] Publicar cada fase **antes** de que parta el semestre correspondiente.
- [ ] **Depende de las tareas 10 y 34:** sin sacar el contenido del código, cada tema nuevo agranda `matematicas.py`.
- [ ] Llevar una tabla «materia × nivel × semestre» con la cantidad de temas, para ver el avance.

### 34. Contenido editable, legible y enviable (P2) · Pedido 17/11
**Revisión pedida (17/11):** el contenido **no está escrito con etiquetas `<p>`** ni HTML. Está dentro de un archivo Python (`models/contenido/matematicas.py`, 526 líneas) como diccionarios: cada párrafo es un texto largo dentro de una lista, y hay convenciones propias (`^` para potencias, `||` en los pasos de los ejemplos). Funciona, pero **no es cómodo para editar si no se programa**, y cambiar un texto obliga a actualizar la app.
- [ ] **Formato propuesto:** un archivo por tema, en texto simple. Opción A: **Markdown con encabezado YAML** (título, nivel, ícono y resumen; secciones «Contenido» y «Ejemplos»; preguntas en bloques estructurados). Opción B: **JSON**, más estricto pero menos legible. Probar las dos con un tema de ejemplo; recomendación inicial: A.
- [ ] **Carpetas** como las que se pensaron: `contenido/matematicas/7-basico/semestre-1/porcentajes/` (conecta con la tarea 10, con `manifest.json` por unidad).
- [ ] **Validador** (script y prueba automática) que revisa cada archivo: campos obligatorios, la respuesta está entre las alternativas, formatos numéricos estrictos, 5 preguntas, y avisa la línea del error en lenguaje claro.
- [ ] **Convertidor** del `matematicas.py` actual al formato nuevo, sin perder nada, con pruebas de ida y vuelta.
- [ ] **Editar sin programar:** (1) con cualquier editor de texto; (2) un **editor en el panel web** con formulario por tema, vista previa, validación en vivo e historial de versiones, para docentes y administradores. Editar dentro de la app se descarta por ahora.
- [ ] **Enviar a los estudiantes:** publicar una versión del paquete (número y huella de verificación) que la app descarga y guarda para usarla sin internet (tarea 10), avisando «Contenido actualizado».
- [ ] **Añadir ejercicios:** hoy cada tema tiene 5 preguntas. Decidir si se arma un banco de ejercicios del que se sortean preguntas.
- [ ] **Permisos e historial:** quién puede editar (¿contenido oficial frente a contenido propio del colegio?; ver la materia propia de cada colegio en la tarea 3), quién cambió qué y poder volver atrás.
- [ ] Mantener funcionando el contenido actual hasta que el convertidor y las pruebas pasen.

### 26. Accesibilidad para tipos de daltonismo (P2) · Pedido 17/11
La app comunica con color (notas, tendencia, estados), y la escala actual va de **rojo a verde**, justo lo que más confunden la protanopia y la deuteranopia. Por eso sube de importancia.
- [ ] **Auditoría**: listar cada lugar donde el color es la **única** señal (notas, flechas de tendencia, etiquetas de riesgo, asistencia, calendario).
- [ ] **Regla: nunca solo color.** Acompañar con número, ícono o texto (por ejemplo «Bajo 5,0», ▲ y ▼). Las notas ya muestran su número: mantenerlo siempre visible.
- [ ] **Paleta apta para daltonismo**: separar los extremos con azul y naranja (más distinguibles que rojo y verde) y con diferencia de luminosidad. Opción «Colores para daltonismo» en Ajustes (protanopia/deuteranopia, y tritanopia).
- [ ] Probar con un **simulador** de daltonismo sobre las capturas de la app y con **personas daltónicas reales**.
- [ ] La leyenda de colores explica cada color con palabras.
- [ ] Esta opción **no** la apaga el botón «Desactivar modificaciones visuales» (tarea 31): es accesibilidad, no decoración.

### 27. Tamaño de la interfaz ajustable (P2) · Pedido 17/11
Para dificultad visual o problemas de compatibilidad con el teléfono.
- [ ] Ajuste de escala (por ejemplo 85 %, 100 %, 125 %, 150 %) para **texto e interfaz**, con vista previa en vivo en Ajustes.
- [ ] Respetar también el tamaño de letra que la persona ya definió en Android.
- [ ] Que **no se rompa nada** en 150 % en una pantalla pequeña (unos 360 dp de ancho): sin textos cortados ni botones tapados, y botones táctiles de al menos 48 dp.
- [ ] Guardar la preferencia por dispositivo.
- [ ] Capturas a 85 %, 100 % y 150 % en las pantallas principales.
- [ ] No la apaga el botón de la tarea 31. Revisar también el panel web en pantallas pequeñas.

### 12. Accesibilidad y pulido (P2, continuo)
- [ ] Letra grande y botones amplios, textos simples y emojis para una app más cercana.
- [ ] Sensación de **urgencia** para docentes y apoderados (feedback de la presentación): colores de nota, orden por nota y avisos pendientes visibles.
- [ ] Probar con 2 o 3 apoderados reales sin ayuda.

### 17. Colores y claridad de acciones en la vista del docente (P2) · Feedback profesor 15/11
Apoderados y estudiantes se entienden a la primera; la vista del docente es más compleja (qué hacer y dónde).
- [ ] Llevar la escala de colores (urgencia/estado) a más lugares: tarjetas de curso, encabezados, avisos pendientes, indicadores de refuerzos.
- [ ] Marcar con color y texto corto la acción sugerida por estudiante (ej. «Desbloquear refuerzo», «Esperando Recibido»).
- [ ] Reordenar la pantalla del docente: primero lo urgente, luego el detalle.
- [ ] Probar sin explicación previa con un docente.

---

#### PRIORIDAD P3 · baja prioridad, ideas y opcionales

### 21. Análisis: subida y bajada de archivos (P3) · Pedido 16/11
**Primero analizar y decidir el alcance; no implementar todavía.** Lo que hay que tener en cuenta si se llegara a hacer:
- [ ] **Alcance mínimo propuesto para una v1**: solo la docente sube, a sus cursos, PDF o presentaciones sin macros, con un tamaño máximo (ej. 10 MB); las familias y estudiantes de ese curso descargan. Que los estudiantes suban archivos (tareas) queda fuera: son menores y suben datos que no controlamos.
- [ ] **Qué formatos**: PDF, `.pptx`, `.docx` e imágenes; rechazar los que traen macros (`.pptm`, `.docm`, `.xlsm`) y los ejecutables.
- [ ] **Seguridad**: validar el tipo por el **contenido** y no por la extensión, limitar el tamaño, limpiar el nombre del archivo, revisar con un antivirus (ej. ClamAV), no ejecutar nunca lo subido y guardarlo **fuera** de la carpeta pública, con enlaces de descarga firmados y de corta duración.
- [ ] **Separación por colegio y curso**: las mismas reglas del resto del sistema, con pruebas de fuga a propósito. Los identificadores no deben poder adivinarse.
- [ ] **Privacidad de menores y Ley 21.719**: prohibir listas con datos de estudiantes en archivos compartidos, definir cuánto tiempo se guardan, poder **eliminar** a pedido y registrar quién sube, descarga y elimina.
- [ ] **Derechos de autor**: la docente es responsable del material que sube; incluirlo en los términos de uso.
- [ ] **Almacenamiento y costos**: almacenamiento de objetos (S3 u otro; ya está contemplado en las tareas 8 y 10), cuota por colegio, costo de transferencia y respaldos.
- [ ] **Conexión rural y datos móviles**: mostrar el tamaño antes de descargar, descarga solo cuando la persona la pide, poder **reanudarla**, guardar en el teléfono con un tope de espacio y opción de borrar, y que lo ya descargado funcione sin conexión. Nada de subidas en segundo plano con datos móviles.
- [ ] **En el celular (Android)**: usar el selector de archivos del sistema (sin pedir permiso amplio de almacenamiento) y abrir los PDF con el visor del teléfono. Hay que probar cómo lo resuelve Kivy en el APK.
- [ ] **Relación con la tarea 10** (contenido por paquetes): reutilizar la idea del `manifest.json` con tamaño y huella de verificación, y distinguir el contenido **oficial** de los archivos de la docente.
- [ ] Al subir un archivo, generar un **aviso automático** a las familias (como en la tarea 15).
- [ ] Base de datos: tabla `archivos` (colegio, curso, autor, nombre, tipo, tamaño, huella, clave de almacenamiento, fecha, vigencia).
- [ ] Entregable: un documento corto con la decisión (qué entra en la v1 y qué no) antes de escribir código.

---

### 25. Modo oscuro (P3) · Opcional · Pedido 17/11
**Por defecto, modo claro. Se puede activar y desactivar a voluntad.** Es completamente opcional.
- [ ] **Base común (tareas 25 a 31):** una pantalla de **Ajustes** y un almacén local de preferencias por dispositivo.
- [ ] Interruptor «Modo oscuro» en Ajustes; evaluar si se agrega la opción «seguir al sistema».
- [ ] Definir los colores de la interfaz como una paleta clara y otra oscura (en `views/estilo.py`) y usar el tema oscuro de KivyMD.
- [ ] **Revisar el contraste de la escala de notas** (rojo, naranja, azul y verde) sobre fondo oscuro: mínimo 4,5:1 para texto.
- [ ] Gráficos (matplotlib), íconos e imágenes también deben verse bien en oscuro.
- [ ] Panel web: modo oscuro opcional.
- [ ] Capturas de todas las pantallas en ambos modos para revisarlas.

### 28. Skins de temporada (P3) · Opcional · Pedido 17/11
Algo simple: huevos de Pascua en Pascua, calabazas en Halloween, luces en Navidad. **Desactivable a voluntad.** Completamente opcional.
- [ ] Decoración liviana en el encabezado, el fondo o los íconos, **sin cambiar** la escala de colores de las notas ni el diseño.
- [ ] Activación **automática por fechas** (usando el calendario de la tarea 24) o manual desde Ajustes.
- [ ] Skins posibles: Pascua, Halloween, Navidad y Fiestas Patrias; sumar otras si se quiere.
- [ ] **No** en pruebas ni en pantallas con información importante (notas, avisos urgentes); no deben bajar el contraste ni el rendimiento.
- [ ] Imágenes livianas (menos de 100 KB cada una).
- [ ] **Derechos de autor**: imágenes propias o con licencia libre (por ejemplo CC0), con créditos.
- [ ] Sensibilidad cultural: dejar que el **administrador del colegio** elija qué skins se permiten (un colegio laico o religioso puede preferir distintos).
- [ ] La apaga el botón de la tarea 31.

### 29. Botones con sonido (P3) · Opcional · Pedido 17/11
Un clic suave, un «pop». **Desactivable a voluntad.** Completamente opcional.
- [ ] Efectos muy cortos (menos de 50 KB) en los botones principales.
- [ ] Respetar el modo silencio y el volumen del teléfono.
- [ ] Interruptor en Ajustes. **Decisión pendiente:** si viene encendido o apagado de fábrica (propuesta: **apagado**, porque se usa en clases y en casa).
- [ ] Sin sonido durante las pruebas.
- [ ] Probar la **demora** en Android con un celular modesto (precargar los sonidos).
- [ ] Licencia libre para los sonidos, con créditos.
- [ ] No reemplaza el aviso visual: es un refuerzo, nunca la única señal.
- [ ] Lo apaga el botón de la tarea 31.

### 30. Animaciones y transiciones entre pantallas (P3) · Opcional · Pedido 17/11
**Desactivable a voluntad.** Completamente opcional.
- [ ] Transiciones cortas (150 a 250 ms) entre pantallas y animaciones sutiles en tarjetas y botones.
- [ ] Al desactivarlas, sin transición (cambio inmediato).
- [ ] Respetar el ajuste «quitar animaciones» de accesibilidad de Android.
- [ ] Medir el rendimiento en un Android modesto; evitar animar listas largas.
- [ ] La apaga el botón de la tarea 31.

### 31. Botón «Desactivar todas las modificaciones visuales» (P3) · Pedido 17/11
**Solo si se llega a implementar más de una** de las tareas 25, 28, 29 y 30.
- [ ] Un botón simple en la **pantalla de inicio** (antes de ingresar), por ejemplo «Modo simple», que apaga de una vez las **decoraciones**: skins (28), animaciones (30) y sonidos (29).
- [ ] **Decisión propuesta:** que **no** toque el modo oscuro, el daltonismo ni el tamaño de la interfaz (25 a 27 son preferencias de accesibilidad y comodidad, no decoración).
- [ ] Guarda el estado por dispositivo (antes de ingresar no hay usuario) y se puede volver a encender cada ajuste por separado en Ajustes.
- [ ] Prueba: con todo encendido y luego «Modo simple», la app queda como la versión base.

### 35. Tutor Educa personal, sin colegio (P3) · Idea para después del piloto · Pedido 17/11
Un modo privado que **no depende de una docente, de un apoderado ni de un colegio**, pero que igual apoya al estudiante. Es como Duolingo con inglés: no es necesario para aprender, pero ayuda a mejorar en el ramo del colegio.
- [ ] **Qué cambia en el diseño:** hoy todo cuelga de un colegio (cada curso exige `colegio_id`) y de una docente. Habría un tipo de cuenta «estudiante independiente» con su propio espacio.
- [ ] **Menores y consentimiento:** sin colegio ni apoderado, ¿quién autoriza? Revisar la Ley 21.719 sobre datos de menores antes de diseñarlo.
- [ ] **Seguridad del tutor IA** sin supervisión: reglas más estrictas, límites de uso y revisión de los contenidos que genera.
- [ ] **Costos:** hoy el colegio es quien asume el uso de IA; sin colegio, ¿quién paga? (suscripción, límites gratuitos, anuncios, etc.)
- [ ] **Contenido:** reutilizar el contenido predefinido (tareas 33 y 34) con progreso propio, sin notas ni avisos de una docente.
- [ ] Posible gamificación liviana (rachas, metas), con cuidado de no presionar.
- [ ] Se parece a un producto distinto: decidir si tiene sentido **después** del piloto con colegios.

---

## 3. Decisiones por tomar

- ¿Confirmamos **AWS Lightsail** o evaluamos otra opción con Docker?
- ¿Notificaciones por **push**, **correo** o ambas?
- ~~¿Panel de SuperAdmin/Admin web o dentro de la app?~~ **Decidido: web** (`/panel`, ya implementado).
- ¿Qué asignaturas entran en la v1.0 además de Matemáticas?
- ¿Quién mantiene el servidor y los respaldos?
- ¿Los sonidos de los botones (tarea 29) vienen **apagados** o encendidos de fábrica? (propuesta: apagados)
- ¿«Desactivar modificaciones visuales» (tarea 31) incluye el modo oscuro? (propuesta: no; solo skins, animaciones y sonidos)
- ¿Qué **asignaturas** entran primero en el contenido nuevo y quién las revisa (tarea 33)?
- ¿Cómo se define el **semestre** para las métricas (por ejemplo marzo a julio y agosto a diciembre, configurable por colegio)? (tarea 22)
- ¿Las clases de sábado se configuran por **curso** (propuesta) o por colegio? (tareas 20 y 24)
- ¿El modo personal de Tutor Educa (tarea 35) tiene sentido antes o después del piloto, y quién pagaría la IA?
- ¿Las evaluaciones formales (tarea 18) pasan a definir quién está «en riesgo» o seguimos con el promedio actual?
- ¿Las clases de sábado se configuran por **curso** (propuesto) o por colegio?
- ¿Qué alcance tendrá la subida de archivos en la v1 (tarea 21)?

---

## 4. Ideas guardadas de las presentaciones

- Feedback de un profesor (15/11): selector de curso, accesos rápidos, más color en la vista docente y aviso al liberar actividades (tareas 14 a 17).
- Escala de colores de notas: hasta 3,9 rojo · 4,0 a 4,9 naranjo · 5,0 a 5,9 neutro · 6,0 a 6,9 azul · 7,0 verde ("¡Perfecto!").
- Ordenar alumnos de menor a mayor nota y flecha de tendencia (sube/baja).
- Avisos con botón "Recibido" en lugar de respuesta escrita (funciona con y sin conexión).
- Acceso en casa y en el colegio, pensando en zonas rurales.

---

## Anexo A. Qué encontramos al revisar los zips

- **V3** (donde lo dejamos) tiene las mejoras del 18/10: colores de nota por rango (rojo, naranjo, neutro, azul, verde), mensajes amables por categoría, tendencia por asignatura y el aviso "Recibido".
- **ALT** (compañero) tiene el orden nuevo: `models/`, `views/`, `services/`, `controladores/`, `main.py` de 24 líneas, KivyMD 2.0, `validaciones.py` y 18 pruebas. Pero parte de la versión anterior a V3, así que **no trae** los colores de nota, los mensajes, la tendencia ni "Recibido".
- **(Resuelto en el paso 2)** La app se conectaba directo a MySQL desde el celular y la clave de la IA iba dentro de la app. Ahora todo pasa por el backend en modo `"motor": "http"`.
- **(Resuelto en el paso 3)** No existía el concepto de colegio. Sigue pendiente: administrador y forma de agregar o quitar estudiantes desde la app (hoy solo por consola).
- Las contraseñas ya se guardan con hash (PBKDF2-SHA256 con sal). Eso está bien y se mantiene.
- ALT se probó en escritorio, **no en un celular real**.

---

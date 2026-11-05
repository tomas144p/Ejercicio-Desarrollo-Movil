# PENDIENTES: Tutor Educa, camino al primer Release

Actualizado: 5 de noviembre de 2026
Decisión: se abandona la etapa MVP y se empieza a preparar un despliegue temprano (piloto real con un colegio).

**Cómo leer este documento**
- **Prioridad:** P0 = bloquea todo lo demás · P1 = necesario para el piloto · P2 = importante, puede ir justo después · P3 = mejora.
- **Disponibilidad:** *Ahora* = se puede hacer ya con lo que tenemos · *Necesita…* = depende de algo externo o de una decisión.

---

## 0. Qué encontramos al revisar los zips

- **V3** (donde lo dejamos) tiene las mejoras del 18/10: colores de nota por rango (rojo, naranjo, neutro, azul, verde), mensajes amables por categoría, tendencia por asignatura y el aviso "Recibido".
- **ALT** (compañero) tiene el orden nuevo: `models/`, `views/`, `services/`, `controladores/`, `main.py` de 24 líneas, KivyMD 2.0, `validaciones.py` y 18 pruebas. Pero parte de la versión anterior a V3, así que **no trae** los colores de nota, los mensajes, la tendencia ni "Recibido".
- **La app hoy se conecta directo a MySQL desde el celular**, con usuario y clave en `config.json`, y la **clave de la API de IA también va dentro de la app**. Eso no es seguro para un piloto con datos de menores y es el principal motivo del paso 2.
- **No existe el concepto de colegio**: hay un solo conjunto de datos y tres roles (estudiante, docente, apoderado). No hay administrador ni forma de agregar o quitar estudiantes desde la app (solo `herramientas/nuevo_usuario.py` por consola).
- Las contraseñas ya se guardan con hash (PBKDF2-SHA256 con sal). Eso está bien y se mantiene.
- ALT se probó en escritorio, **no en un celular real**.

---

## 1. Hoja de ruta ordenada

| # | Tarea | Prioridad | Disponibilidad |
|---|---|---|---|
| 1 | Unificar ALT + V3 | P0 | ✅ Hecho |
| 2 | Backend propio (API) entre la app y la base de datos | P0 | Ahora |
| 3 | Multi-colegio en la base de datos | P0 | Ahora (después del 2) |
| 4 | Roles nuevos: SuperAdmin y Admin de colegio | P1 | Después del 3 |
| 5 | Profesor agrega/quita estudiantes y apoderados | P1 | Después del 4 |
| 6 | Seguridad y protección de datos | P1 | En paralelo con 2 a 5 |
| 7 | Datos locales y sincronización | P1 | Después del 2 |
| 8 | Despliegue en AWS Lightsail | P1 | Necesita 2 y 6 listos |
| 9 | APK de prueba en celulares reales | P1 | Ahora (idealmente antes del 8) |
| 10 | Contenido por asignaturas como paquetes descargables | P2 | Después del 2 |
| 11 | Notificaciones a apoderados | P2 | Necesita 8 |
| 12 | Accesibilidad y pulido para apoderados | P2 | Ahora, continuo |
| 13 | Piloto con un colegio | Meta | Necesita 8, 9 y consentimientos |

---

## 2. Detalle por tarea

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

### 2. Backend propio (P0, Ahora)
**Problema:** hoy la app guarda host, usuario y clave de MySQL, y la clave de IA. Cualquiera que abra el APK las obtiene.
- [ ] Crear un servicio (por ejemplo FastAPI) que sea lo único que habla con la base de datos.
- [ ] La app solo usa HTTPS contra esa API (login, datos del curso, avisos, intentos, "Recibido").
- [ ] Autenticación con token con expiración (JWT) y renovación.
- [ ] Mover la **clave de la IA al servidor**: la app pide al servidor y el servidor llama a la IA, con límite de uso por usuario.
- [ ] Reutilizar `services/` y `models/datos/repositorio.py` en el servidor; quitar `PyMySQL` y las credenciales de la app.
- [ ] Empaquetar el servidor con Docker para no depender de Lightsail.

### 3. Multi-colegio (P0, después del 2)
Una sola base de datos con separación por colegio (decisión de diseño; se puede revisar).
- [ ] Tabla `colegios` y columna `colegio_id` en usuarios, cursos, estudiantes, avisos, notas, intentos y refuerzos.
- [ ] El servidor obtiene el `colegio_id` del token del usuario y lo aplica en **toda** consulta; la app nunca lo envía.
- [ ] Mantener MySQL por ahora (el esquema actual ya genera MySQL y SQLite). Si más adelante se pasa a PostgreSQL, se puede reforzar con Row-Level Security.
- [ ] Pruebas automáticas: un usuario del colegio A **no puede** leer ni escribir datos del colegio B.
- [ ] Migrar el SQL de `database/` y `herramientas/generar_sql_mysql.py`.

### 4. Roles nuevos (P1)
- **SuperAdmin** (el equipo): crea colegios y su primer administrador.
- **Admin de colegio**: crea docentes y cursos.
- Docente, estudiante y apoderado siguen como están.
- [ ] Alta por **código de invitación de un solo uso** con vencimiento, en lugar de entregar contraseñas.
- [ ] Panel mínimo para SuperAdmin/Admin (puede ser web simple, no necesita estar en la app móvil).

### 5. Gestión de estudiantes y apoderados (P1)
Hoy no existe en la app.
- [ ] Docente: agregar, editar y dar de baja estudiantes de sus cursos.
- [ ] Docente: vincular y desvincular apoderados de un estudiante (un apoderado puede tener varios hijos).
- [ ] Dar de baja = desactivar (no borrar de inmediato), con registro de quién y cuándo.
- [ ] Validaciones (`services/validaciones.py`): correo, duplicados, curso del mismo colegio.

### 6. Seguridad y protección de datos (P1, en paralelo)
- [ ] HTTPS obligatorio; la base de datos nunca expuesta a internet.
- [ ] Permisos verificados en **cada** endpoint del servidor, no solo ocultando botones.
- [ ] Limitar intentos de login y bloquear temporalmente.
- [ ] Registro de accesos y cambios sensibles (auditoría).
- [ ] Secretos fuera del código (variables de entorno); `config.local.json` fuera de Git.
- [ ] Respaldos automáticos y prueba de restauración.
- [ ] Minimizar datos: guardar solo lo necesario de menores.
- [ ] Revisar obligaciones de la Ley 21.719 (protección de datos personales, Chile) y preparar consentimiento de apoderados y colegio.
- [ ] Revisar dependencias antes de publicar.

### 7. Datos locales y sincronización (P1, después del 2)
- [ ] SQLite local como **caché** de lo que el usuario ya ve (sus cursos, notas, avisos), no como copia de todo el colegio.
- [ ] Cola de cambios pendientes ("Recibido", intentos) que se envía al volver la conexión, con manejo de duplicados.
- [ ] Token guardado en almacenamiento seguro del dispositivo, no en archivos planos.
- [ ] Al cerrar sesión o cambiar de usuario: borrar la caché local.
- [ ] Revisar `services/sincronizacion.py` y `almacen_json.py` (ALT) para alinearlos con el servidor.

### 8. Despliegue en AWS Lightsail (P1, necesita 2 y 6)
Solo si se confirma Lightsail (hoy se evalúa por los 100 USD de crédito).
- [ ] Instancia Linux pequeña con IP estática; firewall solo 80/443 y SSH restringido a una IP.
- [ ] Base de datos administrada con respaldos, accesible solo por red privada.
- [ ] Dominio y certificado HTTPS.
- [ ] Contenidos pesados en almacenamiento de objetos (S3) y no en el disco de la instancia.
- [ ] Alerta de costos para cuidar el crédito.
- [ ] Todo en Docker para poder migrar cuando se acabe el crédito.

### 9. APK de prueba en celulares reales (P1, Ahora)
- [ ] Empaquetar con Buildozer (incluyendo KivyMD y las fuentes).
- [ ] Probar en al menos un Android modesto: rendimiento, teclado, botón atrás, sin conexión.
- [ ] Revisar tamaño del APK y tiempos de arranque.
- [ ] Ícono, nombre, permisos mínimos y firma de la versión.

### 10. Contenido por asignaturas como paquetes (P2)
Hoy `models/contenido/matematicas.py` es un archivo Python grande dentro de la app.
- [ ] Pasar el contenido a archivos de datos (JSON u otro) fuera del código.
- [ ] Estructura propuesta: `/matematicas/algebra/EcuacionesPrimerGrado/` con su contenido.
- [ ] Un `manifest.json` por asignatura/unidad con versión, tamaño y hash de verificación.
- [ ] La app descarga solo las unidades que el usuario va a usar y puede borrarlas.
- [ ] Control de versiones del contenido y actualización incremental.

### 11. Notificaciones a apoderados (P2, necesita 8)
- [ ] Definir el canal: notificación push (Firebase Cloud Messaging), correo o ambos.
- [ ] Aviso de nuevo mensaje, con el botón "Recibido" para confirmar lectura.
- [ ] Cuidar que no sea excesivo (apoderados con poca experiencia tecnológica).

### 12. Accesibilidad y pulido (P2, continuo)
- [ ] Letra grande y botones amplios, textos simples y emojis para una app más cercana.
- [ ] Sensación de **urgencia** para docentes y apoderados (feedback de la presentación): colores de nota, orden por nota y avisos pendientes visibles.
- [ ] Probar con 2 o 3 apoderados reales sin ayuda.

### 13. Piloto con un colegio (meta)
- [ ] Elegir un colegio y un curso, y acordar alcance y duración.
- [ ] Consentimientos informados (colegio y apoderados).
- [ ] Plan de soporte: a quién reportan problemas.
- [ ] Qué se mide: uso, avisos recibidos, notas, errores.

---

## 3. Decisiones por tomar

- ¿Confirmamos **AWS Lightsail** o evaluamos otra opción con Docker?
- ¿Notificaciones por **push**, **correo** o ambas?
- ¿Panel de SuperAdmin/Admin **web** (recomendado) o dentro de la app?
- ¿Qué asignaturas entran en la v1.0 además de Matemáticas?
- ¿Quién mantiene el servidor y los respaldos?

---

## 4. Ideas guardadas de las presentaciones

- Escala de colores de notas: hasta 3,9 rojo · 4,0 a 4,9 naranjo · 5,0 a 5,9 neutro · 6,0 a 6,9 azul · 7,0 verde ("¡Perfecto!").
- Ordenar alumnos de menor a mayor nota y flecha de tendencia (sube/baja).
- Avisos con botón "Recibido" en lugar de respuesta escrita (funciona con y sin conexión).
- Acceso en casa y en el colegio, pensando en zonas rurales.

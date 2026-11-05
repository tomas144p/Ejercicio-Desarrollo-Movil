# Pendientes de Tutor Educa

## Resuelto en esta versión

- [x] **Base de datos**: SQLite interna en el dispositivo + MySQL en el servidor (`database/tutor_educa_mysql.sql` se importa en phpMyAdmin). Si MySQL no está encendido, se usa un servidor de demostración con los mismos datos.
- [x] **Conectar la base de datos al proyecto**: ingreso, notas, temas desbloqueados, intentos de prueba y avisos se leen y guardan en la base.
- [x] **Perfiles de ingreso** para docente, apoderado y estudiante. El rol se obtiene del correo (tabla `usuarios`).
- [x] **Ingreso en línea** contra la base del servidor e **ingreso sin conexión** con credenciales recordadas (contraseña cifrada) en la base interna. Lo hecho sin conexión se sincroniza al volver la conexión.
- [x] **Chat con IA funcional**: con clave responde Claude; sin clave responde un tutor integrado que explica, muestra ejemplos y toma una mini prueba. También hay asistente para apoderados.
- [x] **Emojis**: reemplazados por la fuente de íconos Lucide (Kivy no dibuja emojis a color).
- [x] **Alerts con texto desbordado**: reemplazados por diálogos que se ajustan al texto.
- [x] **Prototipo más bonito**: nueva identidad visual (papel cuadriculado, color por perfil, tipografía Lexend, ejemplos «en el cuaderno»).
- [x] **Programado en POO** y **con comentarios** que explican el código en todos los archivos.
- [x] Pruebas automáticas (`pruebas/`) y capturas de todas las pantallas (`capturas/`).

## Siguientes pasos sugeridos

- [ ] **API intermedia** (PHP o Python) entre la app y MySQL: hoy la app se conecta directo a la base, lo que no es seguro fuera de un prototipo. La API también debería guardar la clave de la IA.
- [ ] **Compilar para Android** con Buildozer (`buildozer init`, agregar `kivy, pymysql, certifi` en `requirements` e incluir `fonts/*.ttf`, `fonts/*.json` y `config.json`).
- [ ] Clave de IA propia del proyecto (o un modelo local con Ollama para no depender de pagos).
- [ ] Materia para las otras asignaturas (hoy solo Matemáticas tiene contenido y tutor).
- [ ] Panel para que el docente cree o edite temas y preguntas desde la app.
- [ ] Recuperación de contraseña y gestión de cuentas por parte del colegio.
- [ ] Probar la app con estudiantes y docentes reales para ajustar textos y tamaños.

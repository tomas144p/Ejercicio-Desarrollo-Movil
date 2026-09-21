# Tutor Educa — versión Kivy

Conversión funcional del prototipo web de Tutor Educa a una aplicación de escritorio hecha con Python + Kivy.

## Incluye
- Inicio de sesión simulado: Apoderado, Estudiante y Profesor.
- Dashboard del apoderado con rendimiento, tareas, seguimiento, avisos y asistente IA simulado.
- Revisión/aprobación de tareas antes de asignarlas al estudiante.
- Vista del estudiante con asignaturas activadas/desactivadas.
- Contenido offline de Matemáticas: explicación, ejemplos y ejercicios.
- Verificación de un ejercicio.
- Asistente IA simulado con modo estudiante/apoderado.
- Progreso del estudiante.
- Panel profesor con activación/desactivación de asignaturas, estudiantes, rendimiento y avisos.
- Estado Online/Offline simulado.

## Ejecutar

Python 3.10+ recomendado.

```bash
pip install -r requirements.txt
python main.py
```

La IA de esta versión es simulada, igual que en el prototipo original. Para conectar un modelo real habría que añadir una API/servidor y manejo de credenciales.

## Nota
Es una traducción funcional del prototipo React/Tailwind a widgets nativos de Kivy. El diseño es equivalente en estructura y flujo, pero no pretende ser un clon pixel-perfect del CSS web.

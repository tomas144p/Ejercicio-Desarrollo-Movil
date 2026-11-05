-- ===============================================================
-- Tutor Educa: base de datos para MySQL / MariaDB (phpMyAdmin)
-- Generado el 27-09-2026 con herramientas/generar_sql_mysql.py
--
-- Cómo importarlo: phpMyAdmin > Importar > elegir este archivo > Importar.
-- Crea la base 'tutor_educa'. Si se importa otra vez, borra y recrea las tablas.
-- Todas las cuentas de prueba usan la contraseña: tutor2026
-- Las contraseñas se guardan cifradas (PBKDF2-SHA256), nunca en texto plano.
-- ===============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
CREATE DATABASE IF NOT EXISTS tutor_educa CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE tutor_educa;

DROP TABLE IF EXISTS avisos_leidos;
DROP TABLE IF EXISTS avisos;
DROP TABLE IF EXISTS intentos;
DROP TABLE IF EXISTS refuerzos;
DROP TABLE IF EXISTS preguntas;
DROP TABLE IF EXISTS ejemplos;
DROP TABLE IF EXISTS temas;
DROP TABLE IF EXISTS calificaciones;
DROP TABLE IF EXISTS asignaturas;
DROP TABLE IF EXISTS estudiantes;
DROP TABLE IF EXISTS cursos;
DROP TABLE IF EXISTS usuarios;

CREATE TABLE IF NOT EXISTS usuarios (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  correo VARCHAR(120) NOT NULL UNIQUE,
  nombre VARCHAR(120) NOT NULL,
  rol ENUM('estudiante', 'docente', 'apoderado') NOT NULL,
  clave_hash VARCHAR(200) NOT NULL,
  activo INT NOT NULL DEFAULT 1,
  creado_en DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Cuentas de ingreso. El rol define la pantalla de inicio';

CREATE TABLE IF NOT EXISTS cursos (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(60) NOT NULL,
  nivel VARCHAR(40) NOT NULL,
  docente_id INT NOT NULL,
  anio INT NOT NULL DEFAULT 2026,
  FOREIGN KEY (docente_id) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Cursos y su docente a cargo';

CREATE TABLE IF NOT EXISTS estudiantes (
  usuario_id INT NOT NULL PRIMARY KEY,
  curso_id INT NOT NULL,
  apoderado_id INT,
  asistencia INT NOT NULL DEFAULT 100,
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
  FOREIGN KEY (curso_id) REFERENCES cursos(id),
  FOREIGN KEY (apoderado_id) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Datos escolares de cada estudiante';

CREATE TABLE IF NOT EXISTS asignaturas (
  id VARCHAR(10) NOT NULL PRIMARY KEY,
  nombre VARCHAR(60) NOT NULL,
  icono VARCHAR(40) NOT NULL,
  color VARCHAR(9) NOT NULL,
  tiene_tutor INT NOT NULL DEFAULT 0,
  orden INT NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Asignaturas del curso';

CREATE TABLE IF NOT EXISTS calificaciones (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  estudiante_id INT NOT NULL,
  asignatura_id VARCHAR(10) NOT NULL,
  nota DECIMAL(3,1) NOT NULL,
  descripcion VARCHAR(120),
  fecha DATE,
  FOREIGN KEY (estudiante_id) REFERENCES estudiantes(usuario_id) ON DELETE CASCADE,
  FOREIGN KEY (asignatura_id) REFERENCES asignaturas(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Notas de 1,0 a 7,0';

CREATE TABLE IF NOT EXISTS temas (
  id VARCHAR(40) NOT NULL PRIMARY KEY,
  asignatura_id VARCHAR(10) NOT NULL,
  titulo VARCHAR(120) NOT NULL,
  nivel VARCHAR(40) NOT NULL,
  orden INT NOT NULL DEFAULT 0,
  icono VARCHAR(40) NOT NULL DEFAULT 'book-open',
  resumen TEXT NOT NULL,
  contenido TEXT NOT NULL,
  clave TEXT NOT NULL,
  error_comun TEXT NOT NULL,
  consejo_apoderado TEXT NOT NULL,
  FOREIGN KEY (asignatura_id) REFERENCES asignaturas(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Materia preescrita que se lee sin internet';

CREATE TABLE IF NOT EXISTS ejemplos (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  tema_id VARCHAR(40) NOT NULL,
  orden INT NOT NULL,
  titulo VARCHAR(120) NOT NULL,
  enunciado TEXT NOT NULL,
  pasos TEXT NOT NULL,
  resultado VARCHAR(120) NOT NULL,
  comprobacion TEXT,
  FOREIGN KEY (tema_id) REFERENCES temas(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Ejemplos resueltos paso a paso';

CREATE TABLE IF NOT EXISTS preguntas (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  tema_id VARCHAR(40) NOT NULL,
  orden INT NOT NULL,
  enunciado TEXT NOT NULL,
  tipo ENUM('numerica', 'alternativas') NOT NULL,
  alternativas TEXT,
  respuesta VARCHAR(120) NOT NULL,
  pista TEXT,
  explicacion TEXT,
  FOREIGN KEY (tema_id) REFERENCES temas(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Preguntas de la prueba de cada tema';

CREATE TABLE IF NOT EXISTS refuerzos (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  estudiante_id INT NOT NULL,
  tema_id VARCHAR(40) NOT NULL,
  estado ENUM('disponible', 'en_progreso', 'logrado') NOT NULL DEFAULT 'disponible',
  mensaje TEXT,
  desbloqueado_por INT,
  desbloqueado_en DATETIME,
  actualizado_en DATETIME,
  activo INT NOT NULL DEFAULT 1,
  UNIQUE (estudiante_id, tema_id),
  FOREIGN KEY (estudiante_id) REFERENCES estudiantes(usuario_id) ON DELETE CASCADE,
  FOREIGN KEY (tema_id) REFERENCES temas(id),
  FOREIGN KEY (desbloqueado_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Temas que el docente desbloqueó a cada estudiante';

CREATE TABLE IF NOT EXISTS intentos (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  codigo VARCHAR(40) NOT NULL UNIQUE,
  estudiante_id INT NOT NULL,
  tema_id VARCHAR(40) NOT NULL,
  correctas INT NOT NULL,
  total INT NOT NULL,
  porcentaje INT NOT NULL,
  nota DECIMAL(3,1) NOT NULL,
  realizado_en DATETIME NOT NULL,
  origen VARCHAR(10) NOT NULL DEFAULT 'app',
  FOREIGN KEY (estudiante_id) REFERENCES estudiantes(usuario_id) ON DELETE CASCADE,
  FOREIGN KEY (tema_id) REFERENCES temas(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Resultados de las pruebas (codigo evita duplicados al sincronizar)';

CREATE TABLE IF NOT EXISTS avisos (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  codigo VARCHAR(40) NOT NULL UNIQUE,
  curso_id INT NOT NULL,
  estudiante_id INT,
  autor_id INT NOT NULL,
  titulo VARCHAR(120) NOT NULL,
  cuerpo TEXT NOT NULL,
  tipo ENUM('info', 'evaluacion', 'refuerzo', 'logro') NOT NULL DEFAULT 'info',
  creado_en DATETIME NOT NULL,
  FOREIGN KEY (curso_id) REFERENCES cursos(id) ON DELETE CASCADE,
  FOREIGN KEY (estudiante_id) REFERENCES estudiantes(usuario_id) ON DELETE CASCADE,
  FOREIGN KEY (autor_id) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Avisos del docente. estudiante_id NULL = todo el curso';

CREATE TABLE IF NOT EXISTS avisos_leidos (
  aviso_id INT NOT NULL,
  usuario_id INT NOT NULL,
  leido_en DATETIME NOT NULL,
  PRIMARY KEY (aviso_id, usuario_id),
  FOREIGN KEY (aviso_id) REFERENCES avisos(id) ON DELETE CASCADE,
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Qué apoderado leyó cada aviso';

-- usuarios: 12 fila(s)
INSERT INTO usuarios (id, correo, nombre, rol, clave_hash, activo, creado_en) VALUES
  (1, 'carolina.fuentes@tutoreduca.cl', 'Carolina Fuentes', 'docente', 'pbkdf2_sha256$120000$cd7e80c316d75df4$aaMLG/An69aIeetfEgbjWWzSkbxITTCPyh4ve9xjv2Q', 1, '2026-07-29 10:00:00'),
  (2, 'sofia.morales@tutoreduca.cl', 'Sofía Morales', 'estudiante', 'pbkdf2_sha256$120000$9b0fd3263d52f403$DaQDM3xL7pfKKOmf16dLFGSr2/c0IrspfKWuW2TYCeM', 1, '2026-07-29 10:00:00'),
  (3, 'tomas.rojas@tutoreduca.cl', 'Tomás Rojas', 'estudiante', 'pbkdf2_sha256$120000$b929d3ac67ed7de2$X+R1HXwsPEr1yzo3q/xg6t/rWx+j1sUJmeystPDG2YQ', 1, '2026-07-29 10:00:00'),
  (4, 'camila.perez@tutoreduca.cl', 'Camila Pérez', 'estudiante', 'pbkdf2_sha256$120000$bc252d1259f14672$aiEDNNFpEEV+ffPWS/dXyZvCNzXRSL+dEb2uAgWCCXU', 1, '2026-07-29 10:00:00'),
  (5, 'diego.soto@tutoreduca.cl', 'Diego Soto', 'estudiante', 'pbkdf2_sha256$120000$1cfcdcefa92c2877$v/n6m7KWizkYLvQ60r/cxiqHAMTIvFPFYWNtfy1mRvU', 1, '2026-07-29 10:00:00'),
  (6, 'martina.diaz@tutoreduca.cl', 'Martina Díaz', 'estudiante', 'pbkdf2_sha256$120000$56120529d0c447e6$exK7OU2gZs92ULB2YiHuh3Op4dxDnmvyQaJIYW2jrZ4', 1, '2026-07-29 10:00:00'),
  (7, 'benjamin.munoz@tutoreduca.cl', 'Benjamín Muñoz', 'estudiante', 'pbkdf2_sha256$120000$96cfa39c5c0d39ac$TZodRyyQvAJWzNs9UGLH71XSSWZvYiUcsrum5VVYwtU', 1, '2026-07-29 10:00:00'),
  (8, 'isidora.vargas@tutoreduca.cl', 'Isidora Vargas', 'estudiante', 'pbkdf2_sha256$120000$0c8e8e795392fd44$rpyjwOnV9i5XxHLTkzkMrZlNxTKZvazVE5LuACHv8r8', 1, '2026-07-29 10:00:00'),
  (9, 'matias.contreras@tutoreduca.cl', 'Matías Contreras', 'estudiante', 'pbkdf2_sha256$120000$5a9ee8912664a0d8$tNq0ySqtEAhzMokyPZKEcCMTq/3cA579G9PvtNgZncM', 1, '2026-07-29 10:00:00'),
  (10, 'andres.morales@tutoreduca.cl', 'Andrés Morales', 'apoderado', 'pbkdf2_sha256$120000$d3d0c96c5ca114ae$sASo4ISPhwOngRrCMpXCcj+9OFDyr5nB5cHcc3Vlx4c', 1, '2026-07-29 10:00:00'),
  (11, 'rodrigo.perez@tutoreduca.cl', 'Rodrigo Pérez', 'apoderado', 'pbkdf2_sha256$120000$2ed8e74c81a44033$c/o6qAyYHPN6RaxRHfEW3InsAWnQfB0Usz4/OadY3P8', 1, '2026-07-29 10:00:00'),
  (12, 'carmen.soto@tutoreduca.cl', 'Carmen Soto', 'apoderado', 'pbkdf2_sha256$120000$fd466469d7e7c29f$z0veIY/8COh45WkfO6h+m3urIS/wfxCH/zT9ZwHKkew', 1, '2026-07-29 10:00:00');

-- cursos: 1 fila(s)
INSERT INTO cursos (id, nombre, nivel, docente_id, anio) VALUES
  (1, '7° Básico B', '7° básico', 1, 2026);

-- estudiantes: 8 fila(s)
INSERT INTO estudiantes (usuario_id, curso_id, apoderado_id, asistencia) VALUES
  (2, 1, 10, 96),
  (3, 1, NULL, 92),
  (4, 1, 11, 88),
  (5, 1, 12, 94),
  (6, 1, NULL, 99),
  (7, 1, NULL, 90),
  (8, 1, NULL, 97),
  (9, 1, NULL, 85);

-- asignaturas: 5 fila(s)
INSERT INTO asignaturas (id, nombre, icono, color, tiene_tutor, orden) VALUES
  ('mat', 'Matemáticas', 'calculator', '#2748C9', 1, 1),
  ('len', 'Lenguaje', 'book-open', '#B4235A', 0, 2),
  ('cie', 'Ciencias Naturales', 'flask-conical', '#1F8A5B', 0, 3),
  ('his', 'Historia', 'landmark', '#A16207', 0, 4),
  ('ing', 'Inglés', 'languages', '#6D3FC0', 0, 5);

-- calificaciones: 120 fila(s)
INSERT INTO calificaciones (id, estudiante_id, asignatura_id, nota, descripcion, fecha) VALUES
  (1, 2, 'mat', 5.0, 'Evaluación 1', '2026-08-13'),
  (2, 2, 'mat', 4.8, 'Evaluación 2', '2026-09-07'),
  (3, 2, 'mat', 5.6, 'Evaluación 3', '2026-10-02'),
  (4, 2, 'len', 6.2, 'Evaluación 1', '2026-08-13'),
  (5, 2, 'len', 6.5, 'Evaluación 2', '2026-09-07'),
  (6, 2, 'len', 6.0, 'Evaluación 3', '2026-10-02'),
  (7, 2, 'cie', 5.9, 'Evaluación 1', '2026-08-13'),
  (8, 2, 'cie', 6.3, 'Evaluación 2', '2026-09-07'),
  (9, 2, 'cie', 6.1, 'Evaluación 3', '2026-10-02'),
  (10, 2, 'his', 6.8, 'Evaluación 1', '2026-08-13'),
  (11, 2, 'his', 6.6, 'Evaluación 2', '2026-09-07'),
  (12, 2, 'his', 7.0, 'Evaluación 3', '2026-10-02'),
  (13, 2, 'ing', 6.0, 'Evaluación 1', '2026-08-13'),
  (14, 2, 'ing', 5.5, 'Evaluación 2', '2026-09-07'),
  (15, 2, 'ing', 6.2, 'Evaluación 3', '2026-10-02'),
  (16, 3, 'mat', 6.1, 'Evaluación 1', '2026-08-13'),
  (17, 3, 'mat', 5.8, 'Evaluación 2', '2026-09-07'),
  (18, 3, 'mat', 6.4, 'Evaluación 3', '2026-10-02'),
  (19, 3, 'len', 5.5, 'Evaluación 1', '2026-08-13'),
  (20, 3, 'len', 5.9, 'Evaluación 2', '2026-09-07'),
  (21, 3, 'len', 6.0, 'Evaluación 3', '2026-10-02'),
  (22, 3, 'cie', 5.2, 'Evaluación 1', '2026-08-13'),
  (23, 3, 'cie', 5.0, 'Evaluación 2', '2026-09-07'),
  (24, 3, 'cie', 5.6, 'Evaluación 3', '2026-10-02'),
  (25, 3, 'his', 6.0, 'Evaluación 1', '2026-08-13'),
  (26, 3, 'his', 6.3, 'Evaluación 2', '2026-09-07'),
  (27, 3, 'his', 5.8, 'Evaluación 3', '2026-10-02'),
  (28, 3, 'ing', 5.8, 'Evaluación 1', '2026-08-13'),
  (29, 3, 'ing', 6.1, 'Evaluación 2', '2026-09-07'),
  (30, 3, 'ing', 5.5, 'Evaluación 3', '2026-10-02'),
  (31, 4, 'mat', 3.8, 'Evaluación 1', '2026-08-13'),
  (32, 4, 'mat', 4.2, 'Evaluación 2', '2026-09-07'),
  (33, 4, 'mat', 4.4, 'Evaluación 3', '2026-10-02'),
  (34, 4, 'len', 5.6, 'Evaluación 1', '2026-08-13'),
  (35, 4, 'len', 6.0, 'Evaluación 2', '2026-09-07'),
  (36, 4, 'len', 5.8, 'Evaluación 3', '2026-10-02'),
  (37, 4, 'cie', 4.9, 'Evaluación 1', '2026-08-13'),
  (38, 4, 'cie', 5.3, 'Evaluación 2', '2026-09-07'),
  (39, 4, 'cie', 5.1, 'Evaluación 3', '2026-10-02'),
  (40, 4, 'his', 5.5, 'Evaluación 1', '2026-08-13'),
  (41, 4, 'his', 5.9, 'Evaluación 2', '2026-09-07'),
  (42, 4, 'his', 6.1, 'Evaluación 3', '2026-10-02'),
  (43, 4, 'ing', 4.8, 'Evaluación 1', '2026-08-13'),
  (44, 4, 'ing', 5.2, 'Evaluación 2', '2026-09-07'),
  (45, 4, 'ing', 5.0, 'Evaluación 3', '2026-10-02'),
  (46, 5, 'mat', 4.5, 'Evaluación 1', '2026-08-13'),
  (47, 5, 'mat', 5.0, 'Evaluación 2', '2026-09-07'),
  (48, 5, 'mat', 4.6, 'Evaluación 3', '2026-10-02'),
  (49, 5, 'len', 6.3, 'Evaluación 1', '2026-08-13'),
  (50, 5, 'len', 6.0, 'Evaluación 2', '2026-09-07'),
  (51, 5, 'len', 6.6, 'Evaluación 3', '2026-10-02'),
  (52, 5, 'cie', 6.0, 'Evaluación 1', '2026-08-13'),
  (53, 5, 'cie', 5.8, 'Evaluación 2', '2026-09-07'),
  (54, 5, 'cie', 6.4, 'Evaluación 3', '2026-10-02'),
  (55, 5, 'his', 6.9, 'Evaluación 1', '2026-08-13'),
  (56, 5, 'his', 6.7, 'Evaluación 2', '2026-09-07'),
  (57, 5, 'his', 6.8, 'Evaluación 3', '2026-10-02'),
  (58, 5, 'ing', 5.9, 'Evaluación 1', '2026-08-13'),
  (59, 5, 'ing', 6.2, 'Evaluación 2', '2026-09-07'),
  (60, 5, 'ing', 6.0, 'Evaluación 3', '2026-10-02'),
  (61, 6, 'mat', 6.8, 'Evaluación 1', '2026-08-13'),
  (62, 6, 'mat', 6.5, 'Evaluación 2', '2026-09-07'),
  (63, 6, 'mat', 7.0, 'Evaluación 3', '2026-10-02'),
  (64, 6, 'len', 6.6, 'Evaluación 1', '2026-08-13'),
  (65, 6, 'len', 6.9, 'Evaluación 2', '2026-09-07'),
  (66, 6, 'len', 6.4, 'Evaluación 3', '2026-10-02'),
  (67, 6, 'cie', 6.5, 'Evaluación 1', '2026-08-13'),
  (68, 6, 'cie', 6.7, 'Evaluación 2', '2026-09-07'),
  (69, 6, 'cie', 6.3, 'Evaluación 3', '2026-10-02'),
  (70, 6, 'his', 6.2, 'Evaluación 1', '2026-08-13'),
  (71, 6, 'his', 6.6, 'Evaluación 2', '2026-09-07'),
  (72, 6, 'his', 6.4, 'Evaluación 3', '2026-10-02'),
  (73, 6, 'ing', 6.9, 'Evaluación 1', '2026-08-13'),
  (74, 6, 'ing', 7.0, 'Evaluación 2', '2026-09-07'),
  (75, 6, 'ing', 6.7, 'Evaluación 3', '2026-10-02'),
  (76, 7, 'mat', 5.4, 'Evaluación 1', '2026-08-13'),
  (77, 7, 'mat', 5.8, 'Evaluación 2', '2026-09-07'),
  (78, 7, 'mat', 5.5, 'Evaluación 3', '2026-10-02'),
  (79, 7, 'len', 4.9, 'Evaluación 1', '2026-08-13'),
  (80, 7, 'len', 5.3, 'Evaluación 2', '2026-09-07'),
  (81, 7, 'len', 5.1, 'Evaluación 3', '2026-10-02'),
  (82, 7, 'cie', 5.6, 'Evaluación 1', '2026-08-13'),
  (83, 7, 'cie', 5.2, 'Evaluación 2', '2026-09-07'),
  (84, 7, 'cie', 5.8, 'Evaluación 3', '2026-10-02'),
  (85, 7, 'his', 5.0, 'Evaluación 1', '2026-08-13'),
  (86, 7, 'his', 5.4, 'Evaluación 2', '2026-09-07'),
  (87, 7, 'his', 5.7, 'Evaluación 3', '2026-10-02'),
  (88, 7, 'ing', 4.6, 'Evaluación 1', '2026-08-13'),
  (89, 7, 'ing', 5.0, 'Evaluación 2', '2026-09-07'),
  (90, 7, 'ing', 5.3, 'Evaluación 3', '2026-10-02'),
  (91, 8, 'mat', 5.9, 'Evaluación 1', '2026-08-13'),
  (92, 8, 'mat', 6.2, 'Evaluación 2', '2026-09-07'),
  (93, 8, 'mat', 6.0, 'Evaluación 3', '2026-10-02'),
  (94, 8, 'len', 6.4, 'Evaluación 1', '2026-08-13'),
  (95, 8, 'len', 6.1, 'Evaluación 2', '2026-09-07'),
  (96, 8, 'len', 6.7, 'Evaluación 3', '2026-10-02'),
  (97, 8, 'cie', 5.8, 'Evaluación 1', '2026-08-13'),
  (98, 8, 'cie', 6.0, 'Evaluación 2', '2026-09-07'),
  (99, 8, 'cie', 6.2, 'Evaluación 3', '2026-10-02'),
  (100, 8, 'his', 6.5, 'Evaluación 1', '2026-08-13'),
  (101, 8, 'his', 6.3, 'Evaluación 2', '2026-09-07'),
  (102, 8, 'his', 6.1, 'Evaluación 3', '2026-10-02'),
  (103, 8, 'ing', 6.2, 'Evaluación 1', '2026-08-13'),
  (104, 8, 'ing', 6.4, 'Evaluación 2', '2026-09-07'),
  (105, 8, 'ing', 6.6, 'Evaluación 3', '2026-10-02'),
  (106, 9, 'mat', 4.0, 'Evaluación 1', '2026-08-13'),
  (107, 9, 'mat', 3.6, 'Evaluación 2', '2026-09-07'),
  (108, 9, 'mat', 4.5, 'Evaluación 3', '2026-10-02'),
  (109, 9, 'len', 5.0, 'Evaluación 1', '2026-08-13'),
  (110, 9, 'len', 4.6, 'Evaluación 2', '2026-09-07'),
  (111, 9, 'len', 5.2, 'Evaluación 3', '2026-10-02'),
  (112, 9, 'cie', 4.8, 'Evaluación 1', '2026-08-13'),
  (113, 9, 'cie', 5.0, 'Evaluación 2', '2026-09-07'),
  (114, 9, 'cie', 4.4, 'Evaluación 3', '2026-10-02'),
  (115, 9, 'his', 5.3, 'Evaluación 1', '2026-08-13'),
  (116, 9, 'his', 5.6, 'Evaluación 2', '2026-09-07'),
  (117, 9, 'his', 5.0, 'Evaluación 3', '2026-10-02'),
  (118, 9, 'ing', 4.3, 'Evaluación 1', '2026-08-13'),
  (119, 9, 'ing', 4.9, 'Evaluación 2', '2026-09-07'),
  (120, 9, 'ing', 4.7, 'Evaluación 3', '2026-10-02');

-- temas: 7 fila(s)
INSERT INTO temas (id, asignatura_id, titulo, nivel, orden, icono, resumen, contenido, clave, error_comun, consejo_apoderado) VALUES
  ('mat-fracciones', 'mat', 'Suma y resta de fracciones', '6° básico', 1, 'pie-chart', 'Para sumar o restar fracciones necesitas que tengan el mismo denominador. Si no lo tienen, primero las transformas en fracciones equivalentes.', 'Una fracción representa partes de un entero. El número de abajo, el denominador, dice en cuántas partes iguales se dividió el entero; el de arriba, el numerador, dice cuántas de esas partes tomamos. En 3/8 el entero se dividió en 8 partes y tomamos 3.\n\nCuando dos fracciones tienen el mismo denominador, sumar es muy simple: se suman los numeradores y el denominador se mantiene. Es como juntar trozos del mismo tamaño: 3 octavos más 2 octavos son 5 octavos. Para restar se hace lo mismo, pero restando los numeradores.\n\nSi los denominadores son distintos, los trozos no son del mismo tamaño y no se pueden juntar directamente. Primero buscamos un denominador común, idealmente el mínimo común múltiplo (mcm) de los denominadores. Luego amplificamos cada fracción, multiplicando numerador y denominador por el mismo número, para que ambas queden con ese denominador.\n\nAl final conviene simplificar el resultado: dividir numerador y denominador por el mismo número hasta que no se pueda más. Por ejemplo, 3/6 se simplifica a 1/2 dividiendo ambos por 3. Una fracción simplificada vale lo mismo, solo que está escrita de la forma más corta.', 'Solo se suman o restan los numeradores cuando los denominadores son iguales. Si son distintos, primero iguálalos con fracciones equivalentes.', 'Sumar numeradores con numeradores y denominadores con denominadores: 1/2 + 1/4 NO es 2/6. Los denominadores no se suman nunca.', 'Usen comida para practicar: una pizza o un queque cortado en partes iguales. Pídale que muestre cuánto es 1/2 + 1/4 con trozos reales y que explique por qué el resultado es 3/4. Explicar en voz alta ayuda mucho a fijar la idea.'),
  ('mat-enteros', 'mat', 'Números enteros: suma y resta', '7° básico', 2, 'thermometer', 'Los números enteros incluyen a los negativos. Para sumarlos y restarlos, piensa en una recta numérica o en una temperatura que sube y baja.', 'Los números enteros son los positivos (1, 2, 3...), el cero y los negativos (−1, −2, −3...). Los negativos aparecen en la vida diaria: una temperatura bajo cero, un piso subterráneo o una deuda. En la recta numérica, los negativos están a la izquierda del cero y los positivos a la derecha.\n\nPara sumar números con el mismo signo, se suman sus valores y se conserva el signo: −5 + (−4) = −9, como bajar 5 grados y luego 4 más. Para sumar números con distinto signo, se restan sus valores (el mayor menos el menor) y se deja el signo del número que está más lejos del cero: −6 + 9 = 3.\n\nRestar un número es lo mismo que sumar su opuesto. Por eso 7 − (−3) se transforma en 7 + 3 = 10: quitar una deuda de 3 es como ganar 3. Esta regla evita tener que memorizar muchos casos, porque toda resta se puede convertir en suma.\n\nPara comparar enteros, mira la recta numérica: el que está más a la derecha es el mayor. Así, −3 es mayor que −8, aunque 8 parezca un número más grande. Entre los negativos, el que está más cerca del cero es el mayor.', 'Restar es sumar el opuesto: a − (−b) = a + b. Y en una suma de signos distintos, gana el signo del número más alejado del cero.', 'Pensar que −8 es mayor que −3 porque 8 es mayor que 3. En los negativos es al revés: −3 está más a la derecha en la recta, así que es mayor.', 'El termómetro y el ascensor son grandes aliados. Pregunte, por ejemplo: «si en Punta Arenas amaneció a −4 °C y subió 9 grados, ¿qué temperatura hay?». También sirve jugar con los pisos de un estacionamiento subterráneo.'),
  ('mat-porcentajes', 'mat', 'Porcentajes', '7° básico', 3, 'percent', 'Un porcentaje indica cuántas partes de cada 100 se toman. Calcular el 25 % de algo es encontrar 25 de cada 100 partes.', 'La palabra porcentaje viene de «por ciento»: de cada cien. El 30 % significa 30 de cada 100, y se puede escribir como fracción (30/100) o como decimal (0,3). El 100 % es el total y el 50 % es la mitad.\n\nPara calcular un porcentaje de una cantidad, multiplica la cantidad por el porcentaje y divide por 100. Por ejemplo, el 20 % de 350 es 350 × 20 ÷ 100 = 70. También puedes usar el decimal: 350 × 0,2 = 70.\n\nHay atajos muy útiles: el 50 % es la mitad, el 25 % es la cuarta parte, el 10 % es dividir por 10 y el 1 % es dividir por 100. Con el 10 % puedes armar otros: el 30 % es tres veces el 10 %.\n\nEn los descuentos, el porcentaje se calcula sobre el precio original y luego se resta. Para saber qué porcentaje es una parte del total, divide la parte por el total y multiplica por 100.', 'Porcentaje de una cantidad = cantidad × porcentaje ÷ 100. El 10 % es dividir por 10, y desde ahí puedes calcular casi cualquier porcentaje.', 'Olvidar restar el descuento: si algo cuesta $20.000 con 10 % de descuento, $2.000 es lo que te descuentan, no lo que pagas. El precio final es $18.000.', 'Aprovechen las ofertas del supermercado o de los catálogos: pídale que calcule cuánto se ahorra con un 10 %, 25 % o 50 % de descuento y cuánto se paga al final. Usar precios reales hace que el tema tenga sentido.'),
  ('mat-potencias', 'mat', 'Potencias', '7° básico', 4, 'superscript', 'Una potencia es una multiplicación abreviada: la base se multiplica por sí misma tantas veces como indica el exponente.', 'En 5^3 el 5 es la base y el 3 es el exponente. Se lee «cinco elevado a tres» o «cinco al cubo», y significa 5 × 5 × 5 = 125. El exponente no multiplica a la base: indica cuántas veces se repite la base como factor.\n\nAlgunas potencias tienen nombre propio. Elevar a 2 se llama «al cuadrado», porque 4^2 es el área de un cuadrado de lado 4. Elevar a 3 se llama «al cubo», porque 3^3 es el volumen de un cubo de arista 3. Además, cualquier número elevado a 1 es el mismo número.\n\nLas potencias de 10 son muy útiles: 10^2 = 100, 10^3 = 1.000 y 10^6 = 1.000.000. El exponente te dice cuántos ceros hay después del 1. Por eso se usan para escribir números muy grandes, como la distancia entre planetas.\n\nCuando multiplicas potencias de igual base, se conserva la base y se suman los exponentes: 2^3 × 2^4 = 2^7. Tiene lógica: son tres 2 multiplicados por otros cuatro 2, en total siete 2.', 'El exponente indica cuántas veces se multiplica la base por sí misma: 2^4 = 2 × 2 × 2 × 2 = 16, no 2 × 4.', 'Multiplicar la base por el exponente: 5^3 NO es 15. Es 5 × 5 × 5 = 125.', 'Pídale que arme un cuadrado con fósforos, legos o baldosas del piso: un cuadrado de 3 por 3 tiene 3^2 = 9 piezas. Luego pregunte cuántas tendría uno de 4 por 4. Ver la potencia hace que no se confunda con la multiplicación.'),
  ('mat-ecuaciones', 'mat', 'Ecuaciones de primer grado', '7° básico', 5, 'scale', 'Una ecuación es una igualdad con un valor desconocido. Resolverla es encontrar el número que hace verdadera la igualdad, manteniendo siempre el equilibrio.', 'Una ecuación es como una balanza en equilibrio: lo que está a la izquierda del signo igual pesa lo mismo que lo que está a la derecha. La letra, normalmente x, representa un número que no conocemos. Resolver la ecuación es descubrir cuánto vale x.\n\nPara despejar x usamos operaciones inversas: la suma se deshace con una resta, y la multiplicación con una división. En x + 9 = 20 restamos 9 a ambos lados y queda x = 11. En 4x = 28 dividimos ambos lados por 4 y queda x = 7.\n\nLa regla de oro es mantener el equilibrio: lo que haces a un lado del signo igual, lo haces también al otro. Si solo le quitas 9 a un lado, la balanza se desequilibra y el resultado cambia.\n\nCuando hay dos pasos, como en 2x + 1 = 9, primero se deshace la suma o resta y después la multiplicación o división: restamos 1 a ambos lados (2x = 8) y luego dividimos por 2 (x = 4). Siempre puedes comprobar reemplazando x en la ecuación original.', 'Lo que hagas a un lado del signo igual, hazlo también al otro. Primero se deshacen las sumas y restas; después, las multiplicaciones y divisiones.', 'Cambiar un número de lado sin cambiar la operación: en x + 9 = 20, el 9 pasa restando (x = 20 − 9), no sumando.', 'Jueguen a «adivina mi número»: «pensé un número, lo multipliqué por 3, le resté 5 y me dio 10». Pídale que descubra el número y que explique cómo lo hizo. Así practica despejar sin darse cuenta.'),
  ('mat-proporcionalidad', 'mat', 'Proporcionalidad directa', '7° básico', 6, 'trending-up', 'Dos cantidades son directamente proporcionales cuando, al multiplicar una por un número, la otra se multiplica por el mismo número. Su cociente siempre es constante.', 'Si un pasaje de micro cuesta $800, dos pasajes cuestan $1.600 y cuatro cuestan $3.200. Cuando la cantidad de pasajes se duplica, el precio también se duplica. Eso es proporcionalidad directa: ambas cantidades crecen (o disminuyen) al mismo ritmo.\n\nEn una relación proporcional, al dividir una cantidad por la otra siempre se obtiene el mismo número, llamado constante de proporcionalidad (k). En el ejemplo, 1.600 ÷ 2 = 800 y 3.200 ÷ 4 = 800: la constante es el precio de un pasaje.\n\nCon la constante puedes calcular cualquier valor: y = k × x. Si k = 800, entonces 10 pasajes cuestan 10 × 800 = 8.000. Otra estrategia es la reducción a la unidad: primero calculas cuánto vale 1 y luego multiplicas.\n\nEn una tabla de valores proporcionales, cada par de números tiene el mismo cociente, y si los dibujas en un gráfico forman una línea recta que parte del cero. Si el cociente cambia de una columna a otra, la relación no es proporcional.', 'Si una cantidad se multiplica por un número, la otra se multiplica por el mismo número. El cociente y ÷ x es siempre la misma constante k.', 'Sumar en vez de multiplicar: si 2 pasajes cuestan $1.600, 4 pasajes NO cuestan $1.600 + 2. Se duplica la cantidad, entonces se duplica el precio: $3.200.', 'Cocinen juntos una receta y pídale que la ajuste: si la receta es para 4 personas y serán 6, ¿cuánta harina se necesita? También sirve calcular cuánto cuesta 1 kg si 3 kg cuestan $4.500.'),
  ('mat-pitagoras', 'mat', 'Teorema de Pitágoras', '8° básico', 7, 'triangle-right', 'En todo triángulo rectángulo, el cuadrado de la hipotenusa es igual a la suma de los cuadrados de los catetos: a^2 + b^2 = c^2.', 'Un triángulo rectángulo tiene un ángulo de 90°, como la esquina de un cuaderno. Los dos lados que forman ese ángulo se llaman catetos, y el lado más largo, que está frente al ángulo recto, se llama hipotenusa.\n\nEl teorema de Pitágoras dice que si los catetos miden a y b, y la hipotenusa mide c, entonces a^2 + b^2 = c^2. Por ejemplo, con catetos 3 y 4: 3^2 + 4^2 = 9 + 16 = 25, y como 5^2 = 25, la hipotenusa mide 5.\n\nPara encontrar la hipotenusa, suma los cuadrados de los catetos y saca la raíz cuadrada del resultado. Para encontrar un cateto, resta: al cuadrado de la hipotenusa le quitas el cuadrado del otro cateto, y luego sacas la raíz. La raíz cuadrada de 25 es 5 porque 5 × 5 = 25.\n\nHay tríos de números enteros que cumplen el teorema, llamados tríos pitagóricos: (3, 4, 5), (6, 8, 10) y (5, 12, 13). Son útiles para comprobar si una esquina está bien «a escuadra», algo que usan los maestros constructores.', 'La hipotenusa es siempre el lado más largo y está frente al ángulo recto. Para hallarla se suman los cuadrados; para hallar un cateto, se restan.', 'Sumar los lados sin elevarlos al cuadrado: con catetos 3 y 4, la hipotenusa NO es 7. Es la raíz de 9 + 16 = 25, o sea 5.', 'Busquen triángulos rectángulos en la casa: una escalera apoyada en la pared, la diagonal de una mesa o de una pantalla. Midan los catetos con una huincha y comprueben juntos si la diagonal coincide con el teorema.');

-- ejemplos: 21 fila(s)
INSERT INTO ejemplos (id, tema_id, orden, titulo, enunciado, pasos, resultado, comprobacion) VALUES
  (1, 'mat-fracciones', 1, 'Mismo denominador', 'Calcula 2/7 + 3/7', '2/7 + 3/7 || Los denominadores son iguales (7).\n(2 + 3)/7 || Sumamos solo los numeradores.\n5/7 || El denominador se mantiene.', '5/7', 'Dibuja una barra dividida en 7 partes: pinta 2 y luego 3 más. Quedan 5 de 7 pintadas.'),
  (2, 'mat-fracciones', 2, 'Distinto denominador', 'Calcula 1/4 + 1/6', '1/4 + 1/6 || Los denominadores son distintos: 4 y 6.\nmcm(4, 6) = 12 || El menor número que es múltiplo de 4 y de 6.\n3/12 + 2/12 || 1/4 = 3/12 (por 3) y 1/6 = 2/12 (por 2).\n5/12 || Ahora sí sumamos los numeradores.', '5/12', '5/12 ya no se puede simplificar: 5 y 12 no tienen divisores comunes.'),
  (3, 'mat-fracciones', 3, 'Resta y simplificación', 'Calcula 7/10 − 1/5', '7/10 − 1/5 || Denominadores distintos: 10 y 5.\n7/10 − 2/10 || 1/5 = 2/10 (amplificamos por 2).\n5/10 || Restamos los numeradores: 7 − 2 = 5.\n1/2 || Simplificamos dividiendo ambos por 5.', '1/2', 'Suma para comprobar: 1/2 + 1/5 = 5/10 + 2/10 = 7/10. ¡Coincide!'),
  (4, 'mat-enteros', 1, 'Signos distintos', 'Calcula −6 + 9', '−6 + 9 || Los signos son distintos.\n9 − 6 = 3 || Restamos los valores: el mayor menos el menor.\n+3 || Gana el signo del 9, que está más lejos del cero.', '3', 'En la recta: parte en −6 y avanza 9 pasos a la derecha. Llegas a 3.'),
  (5, 'mat-enteros', 2, 'Mismo signo negativo', 'Calcula −5 + (−4)', '−5 + (−4) || Ambos son negativos.\n5 + 4 = 9 || Sumamos los valores.\n−9 || Conservamos el signo negativo.', '−9', 'Si debes $5.000 y te prestan $4.000 más, ahora debes $9.000.'),
  (6, 'mat-enteros', 3, 'Restar un negativo', 'Calcula 4 − (−6)', '4 − (−6) || Restar un número es sumar su opuesto.\n4 + 6 || El opuesto de −6 es 6.\n10 || Ahora es una suma normal.', '10', 'Comprueba: 10 + (−6) = 4. ¡Vuelves al inicio!'),
  (7, 'mat-porcentajes', 1, 'El 10 % como atajo', 'Calcula el 30 % de 250', '10 % de 250 = 25 || El 10 % es dividir por 10.\n30 % = 3 × 10 % || El 30 % son tres veces el 10 %.\n3 × 25 = 75 || Multiplicamos.', '75', 'Con la fórmula: 250 × 30 ÷ 100 = 7.500 ÷ 100 = 75.'),
  (8, 'mat-porcentajes', 2, 'Precio con descuento', 'Una polera cuesta $12.000 y tiene 25 % de descuento. ¿Cuánto pagas?', '25 % de 12.000 || El 25 % es la cuarta parte.\n12.000 ÷ 4 = 3.000 || Este es el descuento.\n12.000 − 3.000 = 9.000 || Restamos el descuento al precio.', '$9.000', 'Pagas el 75 % del precio: 12.000 × 0,75 = 9.000.'),
  (9, 'mat-porcentajes', 3, '¿Qué porcentaje es?', 'En un curso de 40 estudiantes, 10 llegan en bicicleta. ¿Qué porcentaje es?', '10 ÷ 40 = 0,25 || Parte dividida por el total.\n0,25 × 100 = 25 || Multiplicamos por 100.', '25 %', '10 es la cuarta parte de 40, y la cuarta parte es el 25 %.'),
  (10, 'mat-potencias', 1, 'Calcular una potencia', 'Calcula 2^5', '2^5 || Base 2, exponente 5.\n2 × 2 × 2 × 2 × 2 || El 2 se repite 5 veces.\n4 × 4 × 2 || Agrupamos de a dos: 2 × 2 = 4.\n32 || 4 × 4 = 16 y 16 × 2 = 32.', '32', 'Revisa que no sea 2 × 5 = 10: el exponente no multiplica a la base.'),
  (11, 'mat-potencias', 2, 'Potencias de 10', 'Escribe 10^4 como número', '10^4 || Base 10, exponente 4.\n10 × 10 × 10 × 10 || El 10 se repite 4 veces.\n10.000 || Un 1 seguido de 4 ceros.', '10.000', 'Cuenta los ceros: son 4, igual que el exponente.'),
  (12, 'mat-potencias', 3, 'Igual base', 'Escribe 3^2 × 3^2 como una sola potencia y calcula su valor', '3^2 × 3^2 || Las dos potencias tienen base 3.\n3^4 || Conservamos la base y sumamos los exponentes: 2 + 2 = 4.\n3 × 3 × 3 × 3 = 81 || Calculamos el valor.', '81', 'Directo: 3^2 = 9 y 9 × 9 = 81. ¡Coincide!'),
  (13, 'mat-ecuaciones', 1, 'Un paso con suma', 'Resuelve x + 7 = 15', 'x + 7 = 15 || El 7 está sumando a la x.\nx + 7 − 7 = 15 − 7 || Restamos 7 a ambos lados.\nx = 8 || Queda la x sola.', 'x = 8', 'Reemplaza: 8 + 7 = 15. ¡Correcto!'),
  (14, 'mat-ecuaciones', 2, 'Un paso con multiplicación', 'Resuelve 5x = 35', '5x = 35 || 5x significa 5 × x.\n5x ÷ 5 = 35 ÷ 5 || Dividimos ambos lados por 5.\nx = 7 || Resultado.', 'x = 7', 'Reemplaza: 5 × 7 = 35. ¡Correcto!'),
  (15, 'mat-ecuaciones', 3, 'Dos pasos', 'Resuelve 2x + 3 = 11', '2x + 3 = 11 || Primero deshacemos la suma.\n2x = 11 − 3 = 8 || Restamos 3 a ambos lados.\nx = 8 ÷ 2 || Luego dividimos por 2.\nx = 4 || Resultado.', 'x = 4', 'Reemplaza: 2 × 4 + 3 = 8 + 3 = 11. ¡Correcto!'),
  (16, 'mat-proporcionalidad', 1, 'Reducción a la unidad', '3 kg de manzanas cuestan $4.500. ¿Cuánto cuestan 5 kg?', '3 kg cuestan 4.500 || Dato conocido.\n1 kg: 4.500 ÷ 3 = 1.500 || Calculamos el valor de 1 kg.\n5 kg: 5 × 1.500 = 7.500 || Multiplicamos por 5.', '$7.500', 'La constante se mantiene: 7.500 ÷ 5 = 1.500 y 4.500 ÷ 3 = 1.500.'),
  (17, 'mat-proporcionalidad', 2, 'Encontrar la constante', '2 cuadernos cuestan $2.400 y 6 cuadernos $7.200. ¿Es proporcional? ¿Cuánto vale k?', '2.400 ÷ 2 = 1.200 || Primer cociente.\n7.200 ÷ 6 = 1.200 || Segundo cociente.\nk = 1.200 || Los cocientes son iguales: es proporcional.', 'k = 1.200', 'k es el precio de un cuaderno.'),
  (18, 'mat-proporcionalidad', 3, 'Velocidad constante', 'Un bus viaja a 80 km por hora. ¿Cuántos km recorre en 4 horas?', '1 hora: 80 km || La constante es 80.\n4 horas: 4 × 80 || Cuatro veces más tiempo, cuatro veces más distancia.\n320 km || Resultado.', '320 km', '320 ÷ 4 = 80: se mantiene la constante.'),
  (19, 'mat-pitagoras', 1, 'Encontrar la hipotenusa', 'Los catetos miden 6 cm y 8 cm. ¿Cuánto mide la hipotenusa?', 'c^2 = 6^2 + 8^2 || Aplicamos a^2 + b^2 = c^2.\nc^2 = 36 + 64 = 100 || Calculamos los cuadrados y sumamos.\nc = √100 || Sacamos la raíz cuadrada.\nc = 10 cm || Porque 10 × 10 = 100.', '10 cm', '(6, 8, 10) es el doble del trío (3, 4, 5).'),
  (20, 'mat-pitagoras', 2, 'Encontrar un cateto', 'La hipotenusa mide 13 cm y un cateto 5 cm. ¿Cuánto mide el otro cateto?', 'b^2 = 13^2 − 5^2 || Para un cateto, restamos.\nb^2 = 169 − 25 = 144 || Calculamos.\nb = √144 = 12 || Porque 12 × 12 = 144.', '12 cm', '5^2 + 12^2 = 25 + 144 = 169 = 13^2. ¡Correcto!'),
  (21, 'mat-pitagoras', 3, 'Una rampa', 'Una rampa mide 15 m de largo y su base horizontal mide 12 m. ¿Qué altura alcanza?', '15 m es la hipotenusa || La rampa está frente al ángulo recto.\nh^2 = 15^2 − 12^2 || Buscamos un cateto: restamos.\nh^2 = 225 − 144 = 81 || Calculamos.\nh = √81 = 9 m || Porque 9 × 9 = 81.', '9 m', '9^2 + 12^2 = 81 + 144 = 225 = 15^2.');

-- preguntas: 35 fila(s)
INSERT INTO preguntas (id, tema_id, orden, enunciado, tipo, alternativas, respuesta, pista, explicacion) VALUES
  (1, 'mat-fracciones', 1, 'Calcula 3/8 + 2/8', 'numerica', '', '5/8', 'Los denominadores ya son iguales: suma solo los numeradores.', '3 + 2 = 5 y el denominador 8 se mantiene: 5/8.'),
  (2, 'mat-fracciones', 2, '¿Cuál es el mínimo común múltiplo de 4 y 6?', 'alternativas', '10|12|24|2', '12', 'Escribe los múltiplos de 6 (6, 12, 18...) y busca el primero que también sea múltiplo de 4.', 'Múltiplos de 4: 4, 8, 12... Múltiplos de 6: 6, 12... El primero que se repite es 12.'),
  (3, 'mat-fracciones', 3, 'Calcula 1/2 + 1/4', 'numerica', '', '3/4', 'Transforma 1/2 en cuartos: 1/2 = 2/4.', '1/2 = 2/4, entonces 2/4 + 1/4 = 3/4.'),
  (4, 'mat-fracciones', 4, 'Calcula 5/6 − 1/3 y simplifica el resultado', 'numerica', '', '1/2', 'Transforma 1/3 en sextos: 1/3 = 2/6.', '5/6 − 2/6 = 3/6, que simplificado es 1/2.'),
  (5, 'mat-fracciones', 5, 'Martina comió 1/3 de una torta y su hermano 1/2. ¿Qué parte de la torta comieron entre los dos?', 'alternativas', '2/5|5/6|1/6|2/6', '5/6', 'Busca un denominador común para 3 y 2.', '1/3 = 2/6 y 1/2 = 3/6. Juntos: 2/6 + 3/6 = 5/6 de la torta.'),
  (6, 'mat-enteros', 1, 'Calcula −8 + 11', 'numerica', '', '3', 'Signos distintos: resta 11 − 8 y deja el signo del número más lejos del cero.', '11 − 8 = 3 y gana el signo del 11 (positivo): 3.'),
  (7, 'mat-enteros', 2, 'Calcula −3 + (−7)', 'numerica', '', '-10', 'Ambos son negativos: suma los valores y conserva el signo.', '3 + 7 = 10 y se conserva el signo negativo: −10.'),
  (8, 'mat-enteros', 3, 'Calcula 7 − (−3)', 'numerica', '', '10', 'Restar un negativo es sumar su opuesto.', '7 − (−3) = 7 + 3 = 10.'),
  (9, 'mat-enteros', 4, '¿Cuál de estos números es el mayor?', 'alternativas', '−8|−3|−12|−5', '−3', 'El mayor es el que está más cerca del cero, más a la derecha en la recta.', 'En la recta numérica −3 está más a la derecha que −5, −8 y −12, por eso es el mayor.'),
  (10, 'mat-enteros', 5, 'En Punta Arenas amaneció a −4 °C y durante el día la temperatura subió 9 grados. ¿Qué temperatura hubo en la tarde?', 'numerica', '', '5', 'Calcula −4 + 9.', '−4 + 9 = 5. En la tarde hubo 5 °C.'),
  (11, 'mat-porcentajes', 1, '¿Cuánto es el 10 % de 450?', 'numerica', '', '45', 'El 10 % es dividir por 10.', '450 ÷ 10 = 45.'),
  (12, 'mat-porcentajes', 2, '¿Cuánto es el 25 % de 80?', 'numerica', '', '20', 'El 25 % es la cuarta parte: divide por 4.', '80 ÷ 4 = 20.'),
  (13, 'mat-porcentajes', 3, '¿Cómo se escribe 30 % como número decimal?', 'alternativas', '3,0|0,3|0,03|30,0', '0,3', '30 % es 30 de cada 100: divide 30 por 100.', '30 ÷ 100 = 0,3.'),
  (14, 'mat-porcentajes', 4, 'Unas zapatillas cuestan $40.000 y tienen 20 % de descuento. ¿Cuánto pagas?', 'numerica', '', '32000', 'Primero calcula el descuento (20 % de 40.000) y luego réstalo.', '20 % de 40.000 = 8.000. Pagas 40.000 − 8.000 = $32.000.'),
  (15, 'mat-porcentajes', 5, 'En una prueba de 30 preguntas, Javiera contestó 6 mal. ¿Qué porcentaje de las preguntas contestó mal?', 'numerica', '', '20', 'Divide 6 por 30 y multiplica por 100.', '6 ÷ 30 = 0,2 y 0,2 × 100 = 20 %.'),
  (16, 'mat-potencias', 1, 'Calcula 5^3', 'numerica', '', '125', 'Multiplica 5 × 5 × 5.', '5 × 5 = 25 y 25 × 5 = 125.'),
  (17, 'mat-potencias', 2, '¿Qué significa 6^2?', 'alternativas', '6 × 2|6 × 6|6 + 6|2 × 2 × 2 × 2 × 2 × 2', '6 × 6', 'El exponente dice cuántas veces se repite la base.', '6^2 = 6 × 6 = 36: el 6 se repite 2 veces.'),
  (18, 'mat-potencias', 3, 'Calcula 2^6', 'numerica', '', '64', 'Duplica partiendo de 2: 2, 4, 8...', '2, 4, 8, 16, 32, 64: 2^6 = 64.'),
  (19, 'mat-potencias', 4, '¿Cómo se escribe 4^2 × 4^3 como una sola potencia?', 'alternativas', '4^5|4^6|16^5|8^5', '4^5', 'Con igual base, se conserva la base y se suman los exponentes.', 'Se conserva la base 4 y se suman los exponentes: 2 + 3 = 5. Resultado: 4^5.'),
  (20, 'mat-potencias', 5, 'Una caja con forma de cubo mide 3 cm por lado. ¿Cuántos cubitos de 1 cm caben dentro? (Calcula 3^3)', 'numerica', '', '27', 'Un cubo de lado 3 tiene 3 × 3 × 3 cubitos.', '3^3 = 3 × 3 × 3 = 27 cubitos.'),
  (21, 'mat-ecuaciones', 1, 'Resuelve x + 9 = 20', 'numerica', '', '11', 'Resta 9 a ambos lados.', 'x = 20 − 9 = 11. Comprobación: 11 + 9 = 20.'),
  (22, 'mat-ecuaciones', 2, 'Resuelve 3x − 5 = 10', 'numerica', '', '5', 'Primero suma 5 a ambos lados; después divide por 3.', '3x = 15, entonces x = 15 ÷ 3 = 5.'),
  (23, 'mat-ecuaciones', 3, 'Resuelve x ÷ 4 = 3', 'numerica', '', '12', 'La división se deshace multiplicando: multiplica ambos lados por 4.', 'x = 3 × 4 = 12. Comprobación: 12 ÷ 4 = 3.'),
  (24, 'mat-ecuaciones', 4, '¿Cuál es la solución de 2x + 7 = 19?', 'alternativas', 'x = 13|x = 6|x = 12|x = 26', 'x = 6', 'Resta 7 y después divide por 2.', '2x = 19 − 7 = 12, y x = 12 ÷ 2 = 6.'),
  (25, 'mat-ecuaciones', 5, 'Resuelve 4x + 3 = 31', 'numerica', '', '7', 'Resta 3 a ambos lados y luego divide por 4.', '4x = 28, entonces x = 28 ÷ 4 = 7.'),
  (26, 'mat-proporcionalidad', 1, 'Si 2 entradas al cine cuestan $7.000, ¿cuánto cuestan 5 entradas?', 'numerica', '', '17500', 'Calcula primero cuánto cuesta 1 entrada.', '1 entrada: 7.000 ÷ 2 = 3.500. 5 entradas: 5 × 3.500 = $17.500.'),
  (27, 'mat-proporcionalidad', 2, '¿Cuál de estas tablas muestra una relación directamente proporcional?', 'alternativas', '(1, 3) (2, 6) (3, 9)|(1, 3) (2, 5) (3, 7)|(1, 2) (2, 2) (3, 2)|(1, 4) (2, 6) (3, 8)', '(1, 3) (2, 6) (3, 9)', 'Divide el segundo número por el primero en cada par: ¿da siempre lo mismo?', 'En (1, 3) (2, 6) (3, 9) el cociente siempre es 3. En las demás cambia.'),
  (28, 'mat-proporcionalidad', 3, 'Un auto avanza a velocidad constante de 60 km por hora. ¿Cuántos km recorre en 3 horas?', 'numerica', '', '180', 'Multiplica los km de una hora por la cantidad de horas.', '3 × 60 = 180 km.'),
  (29, 'mat-proporcionalidad', 4, 'Una receta para 4 personas usa 300 g de arroz. ¿Cuántos gramos se necesitan para 6 personas?', 'numerica', '', '450', 'Calcula cuánto arroz corresponde a 1 persona.', '300 ÷ 4 = 75 g por persona, y 6 × 75 = 450 g.'),
  (30, 'mat-proporcionalidad', 5, 'Si y = 5 × x, ¿cuánto vale y cuando x = 8?', 'alternativas', '13|40|85|3', '40', 'Reemplaza x por 8 en la fórmula.', 'y = 5 × 8 = 40.'),
  (31, 'mat-pitagoras', 1, 'Los catetos de un triángulo rectángulo miden 3 cm y 4 cm. ¿Cuánto mide la hipotenusa?', 'numerica', '', '5', 'Calcula 3^2 + 4^2 y luego saca la raíz cuadrada.', '3^2 + 4^2 = 9 + 16 = 25, y √25 = 5 cm.'),
  (32, 'mat-pitagoras', 2, 'En un triángulo rectángulo, ¿cuál lado es la hipotenusa?', 'alternativas', 'El lado más corto|El lado opuesto al ángulo recto|Cualquiera de los catetos|El lado de la base', 'El lado opuesto al ángulo recto', 'Mira qué lado queda frente a la esquina de 90°.', 'La hipotenusa está frente al ángulo recto y es siempre el lado más largo.'),
  (33, 'mat-pitagoras', 3, 'La hipotenusa mide 10 cm y un cateto mide 6 cm. ¿Cuánto mide el otro cateto?', 'numerica', '', '8', 'Resta 10^2 − 6^2 y luego saca la raíz.', '100 − 36 = 64 y √64 = 8 cm.'),
  (34, 'mat-pitagoras', 4, '¿Cuál de estos tríos de medidas forma un triángulo rectángulo?', 'alternativas', '(2, 3, 4)|(9, 12, 15)|(4, 5, 7)|(5, 6, 8)', '(9, 12, 15)', 'Comprueba si el cuadrado del mayor es igual a la suma de los cuadrados de los otros dos.', '9^2 + 12^2 = 81 + 144 = 225 = 15^2.'),
  (35, 'mat-pitagoras', 5, 'Una escalera de 5 m se apoya en una pared y su base queda a 3 m de la pared. ¿A qué altura de la pared llega la escalera?', 'numerica', '', '4', 'La escalera es la hipotenusa. Calcula 5^2 − 3^2.', '25 − 9 = 16 y √16 = 4 m.');

-- refuerzos: 7 fila(s)
INSERT INTO refuerzos (id, estudiante_id, tema_id, estado, mensaje, desbloqueado_por, desbloqueado_en, actualizado_en, activo) VALUES
  (1, 2, 'mat-ecuaciones', 'en_progreso', 'Sofía, repasa ecuaciones antes de la prueba del viernes. ¡Tú puedes!', 1, '2026-09-22 09:00:00', '2026-09-23 18:00:00', 1),
  (2, 2, 'mat-fracciones', 'logrado', '', 1, '2026-09-07 09:00:00', '2026-09-08 18:00:00', 1),
  (3, 4, 'mat-enteros', 'disponible', 'Camila, empieza por los ejemplos resueltos. Vas bien.', 1, '2026-09-25 09:00:00', '2026-09-26 18:00:00', 1),
  (4, 4, 'mat-fracciones', 'en_progreso', '', 1, '2026-09-15 09:00:00', '2026-09-16 18:00:00', 1),
  (5, 5, 'mat-porcentajes', 'disponible', '', 1, '2026-09-24 09:00:00', '2026-09-25 18:00:00', 1),
  (6, 9, 'mat-ecuaciones', 'disponible', 'Matías, mira los ejemplos antes de la prueba del viernes.', 1, '2026-09-26 09:00:00', '2026-09-27 18:00:00', 1),
  (7, 9, 'mat-enteros', 'en_progreso', '', 1, '2026-09-18 09:00:00', '2026-09-19 18:00:00', 1);

-- intentos: 4 fila(s)
INSERT INTO intentos (id, codigo, estudiante_id, tema_id, correctas, total, porcentaje, nota, realizado_en, origen) VALUES
  (1, 'demo-intento-1', 2, 'mat-fracciones', 4, 5, 80, 5.5, '2026-09-12 19:00:00', 'app'),
  (2, 'demo-intento-2', 2, 'mat-ecuaciones', 2, 5, 40, 3.0, '2026-09-25 19:00:00', 'app'),
  (3, 'demo-intento-3', 4, 'mat-fracciones', 2, 5, 40, 3.0, '2026-09-19 19:00:00', 'app'),
  (4, 'demo-intento-4', 9, 'mat-enteros', 2, 5, 40, 3.0, '2026-09-21 19:00:00', 'app');

-- avisos: 3 fila(s)
INSERT INTO avisos (id, codigo, curso_id, estudiante_id, autor_id, titulo, cuerpo, tipo, creado_en) VALUES
  (1, 'demo-aviso-1', 1, NULL, 1, 'Prueba de ecuaciones el viernes 2 de octubre', 'Estimadas familias: el viernes 2 de octubre el 7° Básico B rendirá la prueba de ecuaciones de primer grado. En Tutor Educa dejé material de repaso desbloqueado para quienes lo necesitan. Les pido acompañar 15 minutos de estudio diario esta semana.', 'evaluacion', '2026-09-24 16:00:00'),
  (2, 'demo-aviso-2', 1, 4, 1, 'Refuerzo de números enteros', 'Camila tiene disponible el tema Números enteros. Les sugiero practicar 15 minutos al día con ejemplos de temperaturas o pisos de un edificio. Cualquier duda, me escriben por la agenda.', 'refuerzo', '2026-09-25 12:00:00'),
  (3, 'demo-aviso-3', 1, 2, 1, 'Sofía logró el tema de fracciones', 'Sofía obtuvo 80 % en la prueba de suma y resta de fracciones. Ahora le desbloqueé ecuaciones para reforzar antes de la evaluación. ¡Gracias por el apoyo en casa!', 'logro', '2026-09-26 11:00:00');

-- avisos_leidos: 1 fila(s)
INSERT INTO avisos_leidos (aviso_id, usuario_id, leido_en) VALUES
  (1, 10, '2026-09-25 21:00:00');

SET FOREIGN_KEY_CHECKS = 1;

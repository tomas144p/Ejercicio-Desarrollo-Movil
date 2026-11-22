-- ===============================================================
-- Tutor Educa: migración del calendario (tareas 20 y 24)
-- Generado el 21-11-2026 con herramientas/generar_sql_mysql.py --migracion-calendario
--
-- Qué hace: agrega la columna cursos.clases_sabado (apagada: ningún curso cambia) y crea las tablas
-- asistencia_dias (días en que se pasó lista), asistencia (solo las inasistencias) y eventos (feriados y
-- eventos). No cambia ni borra ningún dato existente. Si tu base es anterior, ejecuta ANTES las otras migraciones.
-- IMPORTANTE: haz un respaldo antes. Ejecútalo UNA sola vez.
-- ===============================================================

SET NAMES utf8mb4;
USE tutor_educa;

ALTER TABLE cursos ADD COLUMN clases_sabado INT NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS asistencia_dias (
  curso_id INT NOT NULL,
  fecha DATE NOT NULL,
  registrado_por INT,
  registrado_en DATETIME,
  PRIMARY KEY (curso_id, fecha),
  FOREIGN KEY (curso_id) REFERENCES cursos(id) ON DELETE CASCADE,
  FOREIGN KEY (registrado_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Días en que se pasó lista en cada curso. Un día sin fila aquí no cuenta para la asistencia';

CREATE TABLE IF NOT EXISTS asistencia (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  estudiante_id INT NOT NULL,
  fecha DATE NOT NULL,
  estado ENUM('ausente', 'justificado') NOT NULL,
  registrado_por INT,
  registrado_en DATETIME,
  UNIQUE (estudiante_id, fecha),
  FOREIGN KEY (estudiante_id) REFERENCES estudiantes(usuario_id) ON DELETE CASCADE,
  FOREIGN KEY (registrado_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Solo las excepciones: quién faltó ese día. En un día con lista, quien no aparece aquí estuvo presente';

CREATE TABLE IF NOT EXISTS eventos (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  codigo VARCHAR(40) NOT NULL UNIQUE,
  colegio_id INT NOT NULL,
  curso_id INT,
  titulo VARCHAR(120) NOT NULL,
  descripcion TEXT,
  tipo ENUM('feriado', 'sin_clases', 'celebracion', 'evaluacion', 'reunion', 'otro') NOT NULL DEFAULT 'otro',
  fecha_inicio DATE NOT NULL,
  fecha_fin DATE NOT NULL,
  hay_clases INT NOT NULL DEFAULT 1,
  creado_por INT,
  creado_en DATETIME,
  activo INT NOT NULL DEFAULT 1,
  FOREIGN KEY (colegio_id) REFERENCES colegios(id),
  FOREIGN KEY (curso_id) REFERENCES cursos(id) ON DELETE CASCADE,
  FOREIGN KEY (creado_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Eventos y feriados. curso_id NULL = todo el colegio. Un evento con hay_clases=0 no permite pasar lista';

CREATE INDEX idx_asistencia_estudiante_id ON asistencia (estudiante_id);
CREATE INDEX idx_eventos_colegio_id ON eventos (colegio_id);
CREATE INDEX idx_eventos_curso_id ON eventos (curso_id);
CREATE INDEX idx_eventos_fecha_inicio ON eventos (fecha_inicio);

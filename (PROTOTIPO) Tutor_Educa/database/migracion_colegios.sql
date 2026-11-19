-- ===============================================================
-- Tutor Educa: migración de la versión 0.3 a la 0.4 (colegios)
-- Generado el 08-11-2026 con herramientas/generar_sql_mysql.py --migracion
--
-- Qué hace: crea la tabla colegios, agrega colegio_id a usuarios y cursos, crea UN colegio con el nombre
-- que escribas abajo y le asigna todas las cuentas y cursos que ya existen.
-- Si tu base ya mezclaba varios colegios, asigna cada cuenta y curso con UPDATE antes del último paso.
--
-- IMPORTANTE: haz un respaldo de la base antes. Ejecútalo UNA sola vez.
-- ===============================================================

SET NAMES utf8mb4;
USE tutor_educa;

CREATE TABLE IF NOT EXISTS colegios (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL UNIQUE,
  activo INT NOT NULL DEFAULT 1,
  creado_en DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Cada colegio es un espacio separado: sus cursos, docentes, estudiantes y apoderados no se mezclan';

ALTER TABLE usuarios ADD COLUMN colegio_id INT NULL, ADD KEY idx_usuarios_colegio_id (colegio_id),
  ADD CONSTRAINT fk_usuarios_colegio FOREIGN KEY (colegio_id) REFERENCES colegios (id);
ALTER TABLE cursos ADD COLUMN colegio_id INT NULL, ADD KEY idx_cursos_colegio_id (colegio_id),
  ADD CONSTRAINT fk_cursos_colegio FOREIGN KEY (colegio_id) REFERENCES colegios (id);

-- >>> CAMBIA ESTE NOMBRE por el de tu colegio <<<
INSERT INTO colegios (nombre, activo, creado_en) VALUES ('NOMBRE DE TU COLEGIO', 1, NOW());
SET @colegio = LAST_INSERT_ID();
UPDATE usuarios SET colegio_id = @colegio WHERE colegio_id IS NULL;
UPDATE cursos SET colegio_id = @colegio WHERE colegio_id IS NULL;

-- Desde ahora todo curso debe pertenecer a un colegio.
ALTER TABLE cursos MODIFY colegio_id INT NOT NULL;

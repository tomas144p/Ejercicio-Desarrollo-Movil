-- ===============================================================
-- Tutor Educa: migración para el registro de errores de la app
-- Generado el 18-11-2026 con herramientas/generar_sql_mysql.py --migracion-errores
--
-- Qué hace: crea la tabla errores_app (errores y cierres inesperados, sin datos personales).
-- No cambia ni borra ningún dato existente. Si tu base es anterior, ejecuta ANTES las otras migraciones.
-- IMPORTANTE: haz un respaldo antes. Ejecútalo UNA sola vez.
-- ===============================================================

SET NAMES utf8mb4;
USE tutor_educa;

CREATE TABLE IF NOT EXISTS errores_app (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  codigo VARCHAR(40) NOT NULL UNIQUE,
  colegio_id INT,
  rol VARCHAR(20),
  creado_en DATETIME NOT NULL,
  recibido_en DATETIME NOT NULL,
  version VARCHAR(20),
  plataforma VARCHAR(20),
  pantalla VARCHAR(40),
  tipo VARCHAR(80) NOT NULL,
  mensaje TEXT,
  traza TEXT,
  huella VARCHAR(16) NOT NULL,
  FOREIGN KEY (colegio_id) REFERENCES colegios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Errores y cierres inesperados de la app. Sin datos personales: solo colegio, perfil y causa';

CREATE INDEX idx_errores_app_colegio_id ON errores_app (colegio_id);
CREATE INDEX idx_errores_app_huella ON errores_app (huella);
CREATE INDEX idx_errores_app_creado_en ON errores_app (creado_en);

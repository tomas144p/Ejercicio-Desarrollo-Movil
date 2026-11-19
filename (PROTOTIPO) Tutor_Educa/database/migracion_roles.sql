-- ===============================================================
-- Tutor Educa: migración de colegios a administradores e invitaciones
-- Generado el 08-11-2026 con herramientas/generar_sql_mysql.py --migracion-roles
--
-- Qué hace: permite los perfiles «admin» y «superadmin» en la tabla usuarios y crea la tabla invitaciones
-- (códigos de un solo uso para activar cuentas). No cambia ni borra ningún dato existente.
-- Si tu base es de la versión 0.3, ejecuta ANTES database/migracion_colegios.sql.
-- IMPORTANTE: haz un respaldo antes. Ejecútalo UNA sola vez.
-- ===============================================================

SET NAMES utf8mb4;
USE tutor_educa;

ALTER TABLE usuarios MODIFY rol ENUM('estudiante', 'docente', 'apoderado', 'admin', 'superadmin') NOT NULL;

CREATE TABLE IF NOT EXISTS invitaciones (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  usuario_id INT NOT NULL,
  codigo_hash VARCHAR(64) NOT NULL UNIQUE,
  creada_por INT,
  creado_en DATETIME,
  vence_en DATETIME NOT NULL,
  usada_en DATETIME,
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
  FOREIGN KEY (creada_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Códigos de un solo uso para activar una cuenta o cambiar la contraseña; solo se guarda su huella';

-- ===============================================================
-- Tutor Educa: migración del reloj del servidor
-- Generado el 21-11-2026 con herramientas/generar_sql_mysql.py --migracion-reloj
--
-- Qué hace: crea la tabla estado_servidor. El servidor anota ahí la última hora que vio su reloj y, si de
-- pronto marca una hora anterior (reinicio o corte de luz), no registra asistencia hasta que se corrija.
-- No cambia ni borra ningún dato existente. Ejecútalo UNA sola vez (después de migracion_calendario.sql).
-- ===============================================================

SET NAMES utf8mb4;
USE tutor_educa;

CREATE TABLE IF NOT EXISTS estado_servidor (
  clave VARCHAR(40) NOT NULL PRIMARY KEY,
  valor VARCHAR(80)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Valores internos del servidor. Hoy: la última hora que vio su reloj (para detectar un reloj atrasado)';

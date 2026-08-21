-- Migración: garantizar que todo hospedaje tenga destino y evitar destinos duplicados.
-- Aplicar a bases existentes (dev y testing). Las bases nuevas ya incluyen esto en schema.sql.

-- 1) Evitar destinos duplicados por ciudad/pais normalizados
CREATE UNIQUE INDEX IF NOT EXISTS idx_destinos_ciudad_pais_normalizado
ON destinos (LOWER(TRIM(ciudad)), LOWER(TRIM(pais)));

-- 2) Limpiar hospedajes huérfanos antes de exigir destino_id
DELETE FROM hospedajes WHERE destino_id IS NULL;

-- 3) Exigir destino en todo hospedaje
ALTER TABLE hospedajes ALTER COLUMN destino_id SET NOT NULL;
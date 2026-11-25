-- Separa la descripción del alojamiento de su dirección.
-- Las bases anteriores guardaban la descripción de Google Hotels en `direccion`;
-- se mueve una sola vez a la columna nueva.
ALTER TABLE hospedajes
    ADD COLUMN IF NOT EXISTS descripcion TEXT;

UPDATE hospedajes
SET descripcion = direccion,
    direccion = NULL
WHERE descripcion IS NULL
  AND direccion IS NOT NULL;

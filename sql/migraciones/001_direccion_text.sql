-- Aplica este cambio una sola vez sobre bases creadas con el esquema anterior.
-- La descripción de Google Hotels puede superar los 200 caracteres.
ALTER TABLE hospedajes
ALTER COLUMN direccion TYPE TEXT;

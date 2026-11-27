-- Coordenadas del destino (centro de la ciudad) para calcular distancias.
-- Se resuelven con Nominatim y se guardan para no repetir la consulta.
ALTER TABLE destinos
    ADD COLUMN IF NOT EXISTS latitud DECIMAL(10, 8),
    ADD COLUMN IF NOT EXISTS longitud DECIMAL(11, 8);

CREATE INDEX IF NOT EXISTS idx_destinos_coordenadas
    ON destinos (latitud, longitud)
    WHERE latitud IS NOT NULL AND longitud IS NOT NULL;

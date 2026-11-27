-- Coordenadas geográficas del hotel para calcular distancias reales.
-- gps_coordinates de Google Hotels llega como latitud/longitud decimales.
ALTER TABLE hospedajes
    ADD COLUMN IF NOT EXISTS latitud DECIMAL(10, 8),
    ADD COLUMN IF NOT EXISTS longitud DECIMAL(11, 8);

CREATE INDEX IF NOT EXISTS idx_hospedajes_coordenadas
    ON hospedajes (latitud, longitud)
    WHERE latitud IS NOT NULL AND longitud IS NOT NULL;

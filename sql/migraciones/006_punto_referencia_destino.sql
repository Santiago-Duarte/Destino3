-- Punto de referencia específico del usuario (ej. "estación metro Poblado", "aeropuerto JMC").
-- Si es NULL, las distancias se miden desde el centro de la ciudad (latitud/longitud).
ALTER TABLE destinos
    ADD COLUMN IF NOT EXISTS latitud_ref DECIMAL(10, 8),
    ADD COLUMN IF NOT EXISTS longitud_ref DECIMAL(11, 8),
    ADD COLUMN IF NOT EXISTS punto_referencia_usado TEXT;

CREATE INDEX IF NOT EXISTS idx_destinos_coordenadas_ref
    ON destinos (latitud_ref, longitud_ref)
    WHERE latitud_ref IS NOT NULL AND longitud_ref IS NOT NULL;
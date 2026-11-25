-- Versiona el análisis intrínseco para invalidarlo cuando cambie el prompt.
ALTER TABLE analisis_ia
    ADD COLUMN IF NOT EXISTS version INT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;

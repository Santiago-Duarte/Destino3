-- Migracion aditiva: identificar hoteles por Google Places sin borrar datos.

ALTER TABLE hospedajes
    ADD COLUMN IF NOT EXISTS google_place_id TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_hospedajes_google_place_id_unico
    ON hospedajes (google_place_id);

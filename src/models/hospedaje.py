from decimal import Decimal


class Hospedaje:
    def __init__(
            self,
            nombre: str,
            tipo: str | None,
            precio_noche: float | Decimal | None,
            calificacion: float | Decimal | None,
            direccion: str | None,
            url_reserva: str | None,
            destino_id: int | None,
            id: int | None = None,
            google_place_id: str | None = None,
            descripcion: str | None = None,
            latitud: float | Decimal | None = None,
            longitud: float | Decimal | None = None,
    ) -> None:
        self.nombre = nombre
        self.tipo = tipo
        self.precio_noche = precio_noche
        self.calificacion = calificacion
        self.direccion = direccion
        self.url_reserva = url_reserva
        self.destino_id = destino_id
        self.id = id
        self.google_place_id = google_place_id
        self.descripcion = descripcion
        self.latitud = latitud
        self.longitud = longitud

        # Datos calculados en cada búsqueda; no se persisten porque dependen
        # del punto de referencia elegido.
        self.distancia_km: float | None = None
        self.tiempo_auto_min: int | None = None
        self.tiempo_transit_min: int | None = None
        self.tiempo_walking_min: int | None = None

    def coordenadas(self) -> tuple[float, float] | None:
        """Devuelve ``(latitud, longitud)`` si ambas están presentes."""
        if self.latitud is None or self.longitud is None:
            return None
        return float(self.latitud), float(self.longitud)

from decimal import Decimal


class Hospedaje:
    def __init__(
            self,
            nombre: str,
            tipo: str,
            precio_noche: float | Decimal | None,
            calificacion: float | Decimal | None,
            direccion: str | None,
            url_reserva: str | None,
            destino_id: int,
            id: int | None = None,
            google_place_id: str | None = None,
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

from decimal import Decimal


class Destino:
    def __init__(
            self,
            ciudad: str | None,
            pais: str | None,
            id: int | None = None,
            latitud: float | Decimal | None = None,
            longitud: float | Decimal | None = None,
            latitud_ref: float | Decimal | None = None,
            longitud_ref: float | Decimal | None = None,
            punto_referencia_usado: str | None = None,
    ) -> None:
        self.id = id
        self.ciudad = ciudad
        self.pais = pais
        self.latitud = latitud
        self.longitud = longitud
        self.latitud_ref = latitud_ref
        self.longitud_ref = longitud_ref
        self.punto_referencia_usado = punto_referencia_usado

    def coordenadas(self) -> tuple[float, float] | None:
        """Devuelve ``(latitud, longitud)`` del centro de la ciudad si ambas están presentes."""
        if self.latitud is None or self.longitud is None:
            return None
        return (float(self.latitud), float(self.longitud))

    def coordenadas_referencia(self) -> tuple[float, float] | None:
        """Devuelve ``(latitud, longitud)`` del punto de referencia si ambas están presentes."""
        if self.latitud_ref is None or self.longitud_ref is None:
            return None
        return (float(self.latitud_ref), float(self.longitud_ref))

    def tiene_referencia(self) -> bool:
        return self.coordenadas_referencia() is not None

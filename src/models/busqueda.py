from datetime import date


class Busqueda:
    def __init__(
            self,
            id: int | None,
            usuario_id: int,
            destino_id: int,
            zona: str,
            presupuesto: float,
            fecha_inicio: str | date,
            fecha_fin: str | date,
    ) -> None:
        self.id = id
        self.usuario_id = usuario_id
        self.destino_id = destino_id
        self.zona = zona
        self.presupuesto = presupuesto
        self.fecha_inicio = fecha_inicio
        self.fecha_fin = fecha_fin

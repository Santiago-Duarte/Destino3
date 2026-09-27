class Evaluacion:
    def __init__(
            self,
            resumen_ejecutivo: str,
            puntos_fuertes: str,
            puntos_debiles: str,
            score_calidad_precio: int,
            hospedaje_id: int,
            id: int | None = None,
    ) -> None:
        self.resumen_ejecutivo = resumen_ejecutivo
        self.puntos_fuertes = puntos_fuertes
        self.puntos_debiles = puntos_debiles
        self.score_calidad_precio = score_calidad_precio
        self.hospedaje_id = hospedaje_id
        self.id = id

    def __str__(self) -> str:
        return f"""
                {self.id} - Hospedaje: {self.hospedaje_id}
                Score: {self.score_calidad_precio}
                Resumen: {self.resumen_ejecutivo}
                Fuertes: {self.puntos_fuertes}
                Debiles: {self.puntos_debiles}
        """

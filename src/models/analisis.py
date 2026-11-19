from src.models.analisis_ia import AnalisisIAOutput


class Analisis:
    """Fila de ``analisis_ia``; el score no se guarda porque depende de cada búsqueda."""

    def __init__(
            self,
            resumen_ejecutivo: str,
            puntos_fuertes: str,
            puntos_debiles: str,
            hospedaje_id: int,
            id: int | None = None,
    ) -> None:
        self.resumen_ejecutivo = resumen_ejecutivo
        self.puntos_fuertes = puntos_fuertes
        self.puntos_debiles = puntos_debiles
        self.hospedaje_id = hospedaje_id
        self.id = id

    @classmethod
    def desde_ia(cls, analisis_ia: AnalisisIAOutput) -> "Analisis":
        return cls(
            resumen_ejecutivo=analisis_ia.resumen_ejecutivo,
            puntos_fuertes=analisis_ia.puntos_fuertes,
            puntos_debiles=analisis_ia.puntos_debiles,
            hospedaje_id=analisis_ia.hospedaje_id,
        )

from src.models.evaluacion_ia import EvaluacionIAOutput


class Evaluacion:
    """Fila de ``evaluaciones_ia``; el ``id_temporal`` de la IA no llega aquí."""

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

    @classmethod
    def desde_ia(cls, evaluacion_ia: EvaluacionIAOutput, hospedaje_id: int) -> "Evaluacion":
        return cls(
            resumen_ejecutivo=evaluacion_ia.resumen_ejecutivo,
            puntos_fuertes=evaluacion_ia.puntos_fuertes,
            puntos_debiles=evaluacion_ia.puntos_debiles,
            score_calidad_precio=evaluacion_ia.score_calidad_precio,
            hospedaje_id=hospedaje_id,
        )

from src.exceptions.GeminiError import GeminiError


class EvaluacionIALoteError(GeminiError):
    """Indica que un lote de evaluación IA falló tras agotar sus reintentos."""

    def __init__(self, operacion: str, detalle: str):
        super().__init__(operacion, detalle)
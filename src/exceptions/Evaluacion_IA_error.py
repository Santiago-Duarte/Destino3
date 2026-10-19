from src.exceptions.GeminiError import GeminiError


class EvaluacionIALoteError(GeminiError):
    """Indica que un lote de evaluación IA falló tras agotar sus reintentos."""

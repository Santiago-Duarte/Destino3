from src.exceptions.GeminiError import GeminiError


class LoteIAError(GeminiError):
    """Indica que una respuesta por lotes de la IA falló tras agotar sus reintentos."""

    def __init__(self, operacion: str, detalle: str):
        super().__init__(operacion, detalle)

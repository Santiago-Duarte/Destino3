from src.exceptions.Destino3Error import Destino3Error


class GeminiError(Destino3Error):
    """Error al solicitar o validar una respuesta de Gemini."""

    def __init__(self, operacion: str, detalle: str):
        super().__init__("Gemini", operacion, detalle)
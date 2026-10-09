from src.exceptions.base import Destino3Error


class SerpApiError(Destino3Error):
    """Error al consultar o configurar el proveedor SerpAPI."""


class GeminiError(Destino3Error):
    """Error al solicitar o validar una respuesta de Gemini."""


class PersistenciaError(Destino3Error):
    """Error de persistencia contextualizado por proveedor y operación."""

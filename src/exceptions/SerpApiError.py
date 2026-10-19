from src.exceptions.Destino3Error import Destino3Error


class SerpApiError(Destino3Error):
    """Error al consultar o configurar el proveedor SerpAPI."""

    def __init__(self, operacion: str, detalle: str):
        super().__init__("SerpAPI",  operacion, detalle)
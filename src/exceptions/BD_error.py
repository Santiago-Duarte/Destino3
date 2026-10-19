from src.exceptions.Destino3Error import Destino3Error


class PersistenciaError(Destino3Error):
    """Error de persistencia contextualizado por proveedor y operación."""

    def __init__(self, proveedor: str, operacion: str, detalle: str):
        super().__init__(proveedor, operacion, detalle)
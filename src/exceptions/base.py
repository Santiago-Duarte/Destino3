class Destino3Error(Exception):
    """Error de dominio con proveedor, operación y detalle identificables."""

    def __init__(self, proveedor: str, operacion: str, detalle: str) -> None:
        self.proveedor = proveedor
        self.operacion = operacion
        self.detalle = detalle
        super().__init__(f"[{proveedor}] {operacion}: {detalle}")

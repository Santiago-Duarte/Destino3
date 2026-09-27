class Destino:
    def __init__(self, ciudad: str, pais: str, id: int | None = None) -> None:
        self.id = id
        self.ciudad = ciudad
        self.pais = pais

    def __str__(self) -> str:
        return f"{self.id} - Ciudad: {self.ciudad}, Pais: {self.pais}"

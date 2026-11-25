class Destino:
    def __init__(
            self,
            ciudad: str | None,
            pais: str | None,
            id: int | None = None,
    ) -> None:
        self.id = id
        self.ciudad = ciudad
        self.pais = pais

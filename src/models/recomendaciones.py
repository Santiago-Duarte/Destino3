class Recomendaciones:
    def __init__(self, id: int | None, busqueda_id: int, hospedaje_id: int, posicion: int) -> None:
        self.id = id
        self.busqueda_id = busqueda_id
        self.hospedaje_id = hospedaje_id
        self.posicion = posicion

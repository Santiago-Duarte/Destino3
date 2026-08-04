class Destino:
    def __init__(self, ciudad, pais, id=None):
        self.id = id
        self.ciudad = ciudad
        self.pais = pais

    def __str__(self):
        return f"{self.id} - Ciudad: {self.ciudad}, Pais: {self.pais}"
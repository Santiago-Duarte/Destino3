class Hospedaje:
    def __init__(self, nombre, tipo, precio_noche, calificacion, direccion, url_reserva, destino_id, id=None):
        self.nombre = nombre
        self.tipo = tipo
        self.precio_noche = precio_noche
        self.calificacion = calificacion
        self.direccion = direccion
        self.url_reserva = url_reserva
        self.destino_id = destino_id
        self.id = id

    def __str__(self):
        return f"""
                {self.id} - {self.nombre} - {self.tipo}
                {self.precio_noche} - {self.calificacion} - {self.direccion}
                {self.url_reserva} - {self.destino_id}
        """
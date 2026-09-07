class Evaluacion:
    def __init__(self, resumen_ejecutivo, puntos_fuertes, puntos_debiles, score_calidad_precio, hospedaje_id, id=None):
        self.resumen_ejecutivo = resumen_ejecutivo
        self.puntos_fuertes = puntos_fuertes
        self.puntos_debiles = puntos_debiles
        self.score_calidad_precio = score_calidad_precio
        self.hospedaje_id = hospedaje_id
        self.id = id

    def __str__(self):
        return f"""
                {self.id} - Hospedaje: {self.hospedaje_id}
                Score: {self.score_calidad_precio}
                Resumen: {self.resumen_ejecutivo}
                Fuertes: {self.puntos_fuertes}
                Debiles: {self.puntos_debiles}
        """

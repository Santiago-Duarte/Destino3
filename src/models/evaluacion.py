class Evaluacion:
    """Entidad de dominio de una evaluación de IA ya persistida.

    Es la contraparte de ``EvaluacionIAOutput`` (``src/models/evaluacion_ia.py``):
    mientras ese modelo es el DTO de la respuesta de Gemini que solo vive en
    memoria, esta entidad representa una fila de la tabla ``evaluaciones_ia``.

    Diferencias clave con el DTO de IA:
        - ``id`` lo genera PostgreSQL (nunca la IA).
        - ``hospedaje_id`` es la FK real al hospedaje persistido.
        - No tiene ``id_temporal``: ese token de correlación jamás llega a la
            base de datos (AGENTS.md #7).

    Attributes:
        resumen_ejecutivo: Resumen breve del hospedaje.
        puntos_fuertes: Aspectos favorables del hospedaje.
        puntos_debiles: Aspectos desfavorables del hospedaje.
        score_calidad_precio: Puntuación de calidad-precio entre 1 y 10.
        hospedaje_id: Identificador persistente del hospedaje evaluado (FK).
        id: Identificador generado por PostgreSQL; ``None`` antes de guardar.
    """

    def __init__(
            self,
            resumen_ejecutivo: str,
            puntos_fuertes: str,
            puntos_debiles: str,
            score_calidad_precio: int,
            hospedaje_id: int,
            id: int | None = None,
    ) -> None:
        self.resumen_ejecutivo = resumen_ejecutivo
        self.puntos_fuertes = puntos_fuertes
        self.puntos_debiles = puntos_debiles
        self.score_calidad_precio = score_calidad_precio
        self.hospedaje_id = hospedaje_id
        self.id = id

    def __str__(self) -> str:
        return f"""
                {self.id} - Hospedaje: {self.hospedaje_id}
                Score: {self.score_calidad_precio}
                Resumen: {self.resumen_ejecutivo}
                Fuertes: {self.puntos_fuertes}
                Debiles: {self.puntos_debiles}
        """

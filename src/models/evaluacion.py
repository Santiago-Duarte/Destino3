from src.models.evaluacion_ia import EvaluacionIAOutput


class Evaluacion:
    """Entidad de dominio de una evaluación de IA ya persistida.

    Es la contraparte de ``EvaluacionIAOutput`` (``src/models/evaluacion_ia.py``):
    mientras ese modelo es el DTO de la respuesta de Gemini que solo vive en
    memoria, esta entidad representa una fila de la tabla ``evaluaciones_ia``.

    Diferencias clave con el DTO de IA:
        - ``id`` lo genera PostgreSQL (nunca la IA).
        - ``hospedaje_id`` es la FK real al hospedaje persistido.
        - No tiene ``id_temporal``: ese token de correlación jamás llega a la
            base de datos (constitución #4).

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

    @classmethod
    def desde_ia(cls, evaluacion_ia: EvaluacionIAOutput, hospedaje_id: int) -> "Evaluacion":
        """Copia los campos de negocio de la respuesta de la IA, sin ``id_temporal``."""
        return cls(
            resumen_ejecutivo=evaluacion_ia.resumen_ejecutivo,
            puntos_fuertes=evaluacion_ia.puntos_fuertes,
            puntos_debiles=evaluacion_ia.puntos_debiles,
            score_calidad_precio=evaluacion_ia.score_calidad_precio,
            hospedaje_id=hospedaje_id,
        )

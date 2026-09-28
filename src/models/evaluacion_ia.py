from pydantic import BaseModel, Field


class EvaluacionIAOutput(BaseModel):
    """Evaluación de un hospedaje devuelta por Gemini, validada antes de usarse.

    Attributes:
        id_temporal: Identificador efímero usado solo para correlacionar la
            solicitud y la respuesta de la IA. Nunca se persiste.
        resumen_ejecutivo: Resumen breve del hospedaje.
        puntos_fuertes: Aspectos favorables del hospedaje.
        puntos_debiles: Aspectos desfavorables del hospedaje.
        score_calidad_precio: Puntuación de calidad-precio entre 1 y 10.
    """

    id_temporal: int
    resumen_ejecutivo: str
    puntos_fuertes: str
    puntos_debiles: str
    score_calidad_precio: int = Field(ge=1, le=10, strict=True)


class LoteEvaluacionesIA(BaseModel):
    """Respuesta completa de Gemini para un lote de candidatos enviados juntos.

    Attributes:
        evaluaciones: Evaluaciones validadas del lote, una por candidato.
    """

    evaluaciones: list[EvaluacionIAOutput]

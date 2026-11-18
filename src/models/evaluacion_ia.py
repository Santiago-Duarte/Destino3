from pydantic import BaseModel, Field


class EvaluacionIAOutput(BaseModel):
    """Contrato de salida de Gemini; ``id_temporal`` solo existe en memoria."""

    id_temporal: int
    resumen_ejecutivo: str
    puntos_fuertes: str
    puntos_debiles: str
    score_calidad_precio: int = Field(ge=1, le=10, strict=True)


class LoteEvaluacionesIA(BaseModel):
    evaluaciones: list[EvaluacionIAOutput]

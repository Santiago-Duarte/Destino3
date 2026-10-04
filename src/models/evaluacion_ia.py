from pydantic import BaseModel, Field


class EvaluacionIAOutput(BaseModel):
    """DTO de una evaluación de un hospedaje devuelta por Gemini, validada antes de usarse.

    Es el contrato de entrada/salida con la IA (constitución #5) y solo vive
    en memoria durante el ciclo request/response. La entidad persistida
    equivalente es ``Evaluacion`` (``src/models/evaluacion.py``), que sí
    lleva ``id`` de PostgreSQL y ``hospedaje_id``.

    Attributes:
        id_temporal: Token de correlación del ciclo con Gemini (no es un ID
            de base de datos): se asigna al construir el prompt, la IA debe
            devolverlo intacto en cada evaluación y así se traduce cada
            respuesta al hospedaje original. Nunca se persiste (AGENTS.md #7).
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

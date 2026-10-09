"""Excepciones específicas del dominio de Destino3."""

from src.exceptions.base import Destino3Error
from src.exceptions.evaluacion_ia import EvaluacionIALoteError
from src.exceptions.integracion import GeminiError, PersistenciaError, SerpApiError

__all__ = [
    "Destino3Error",
    "EvaluacionIALoteError",
    "GeminiError",
    "PersistenciaError",
    "SerpApiError",
]

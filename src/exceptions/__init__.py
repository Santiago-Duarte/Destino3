"""Excepciones específicas del dominio de Destino3."""

from src.exceptions.BD_error import PersistenciaError
from src.exceptions.Destino3Error import Destino3Error
from src.exceptions.Evaluacion_IA_error import EvaluacionIALoteError
from src.exceptions.GeminiError import GeminiError
from src.exceptions.SerpApiError import SerpApiError

__all__ = [
    "Destino3Error",
    "EvaluacionIALoteError",
    "GeminiError",
    "PersistenciaError",
    "SerpApiError",
]

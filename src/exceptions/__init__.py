"""Excepciones específicas del dominio de Destino3."""

from src.exceptions.BD_error import PersistenciaError
from src.exceptions.Destino3Error import Destino3Error
from src.exceptions.GeminiError import GeminiError
from src.exceptions.LoteIAError import LoteIAError
from src.exceptions.SerpApiError import SerpApiError

__all__ = [
    "Destino3Error",
    "GeminiError",
    "LoteIAError",
    "PersistenciaError",
    "SerpApiError",
]

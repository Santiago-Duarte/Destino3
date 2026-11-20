import logging
import time

from google import genai
from google.genai import types

from src.config import settings
from src.exceptions.LoteIAError import LoteIAError

logger = logging.getLogger(__name__)

MODELO_IA = "gemini-3.6-flash"


def crear_cliente():
    """Cliente único de Gemini; sin timeout una llamada colgada bloquea el CLI."""
    if not settings.GEMINI_API_KEY:
        raise ValueError("Falta la credencial del proveedor de IA")
    return genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(
            timeout=int(settings.GEMINI_TIMEOUT * 1000),
        ),
    )


def _generar(cliente, prompt: str, schema):
    """Una sola llamada a Gemini con respuesta validada por ``schema``."""
    respuesta = cliente.models.generate_content(
        model=MODELO_IA,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    return schema.model_validate_json(respuesta.text)


def generar(
        cliente,
        prompt: str,
        schema,
        operacion: str,
        hospedaje_ids: set[int] | None = None,
):
    """Reintenta ante error o respuesta incompleta y devuelve lo mejor obtenido.

    Sin ``hospedaje_ids`` la respuesta debe llegar completa; con ellos se acepta
    una respuesta parcial tras agotar los reintentos.
    """
    mejor_parcial = None

    for intento in range(settings.GEMINI_MAX_REINTENTOS + 1):
        try:
            lote = _generar(cliente, prompt, schema)
            if hospedaje_ids is None:
                return lote

            faltantes = hospedaje_ids - lote.hospedaje_ids()
            if not faltantes:
                return lote
            logger.warning(
                "Respuesta de Gemini incompleta: faltan %s de %s",
                len(faltantes), len(hospedaje_ids),
            )
            if mejor_parcial is None or len(lote) > len(mejor_parcial):
                mejor_parcial = lote
        except Exception as error:
            logger.error("Error al consultar Gemini: tipo=%s", type(error).__name__)

        if intento < settings.GEMINI_MAX_REINTENTOS:
            time.sleep(settings.GEMINI_BACKOFF_BASE * (2 ** intento))

    if mejor_parcial is not None:
        return mejor_parcial

    raise LoteIAError(operacion, "El lote agotó los reintentos")

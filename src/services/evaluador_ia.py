import json
import logging
import time

from google import genai
from google.genai import types

from src.config import settings
from src.exceptions.Evaluacion_IA_error import EvaluacionIALoteError
from src.models.evaluacion_ia import LoteEvaluacionesIA
from src.models.hospedaje import Hospedaje

logger = logging.getLogger(__name__)

MODELO_IA = "gemini-3.6-flash"
MAX_CANDIDATOS_IA = 10


def preseleccionar_candidatos(
        hospedajes: list[Hospedaje],
        presupuesto_maximo_noche: float,
) -> list[Hospedaje]:
    en_presupuesto = [
        hospedaje
        for hospedaje in hospedajes
        if hospedaje.precio_noche is not None
        and hospedaje.precio_noche <= presupuesto_maximo_noche
    ]

    return sorted(
        en_presupuesto,
        key=lambda hospedaje: (-(hospedaje.calificacion or 0), hospedaje.precio_noche),
    )[:MAX_CANDIDATOS_IA]


def _prompt_evaluacion(
        resumen_candidatos: list[dict],
        presupuesto_maximo_noche: float,
        preferencias: str,
) -> str:
    return f"""
                Eres un asistente experto en viajes. Revisa la siguiente lista de hospedajes en formato JSON:
                {json.dumps(resumen_candidatos, ensure_ascii=False, indent=4)}

                Criterios del usuario:
                - Presupuesto máximo por noche: USD ${presupuesto_maximo_noche}
                - Preferencias adicionales: {preferencias if preferencias else "Ninguna especificada"}

                Instrucciones:
                1. Selecciona las **3 mejores opciones** de hospedaje de la lista que cumplan con el presupuesto.
                2. Para cada opción, utiliza el `id_temporal` exacto del JSON para mantener la relación.
                3. Proporciona para cada una: un resumen ejecutivo, puntos fuertes, puntos débiles y un `score_calidad_precio` del 1 al 10.
                4. Usa únicamente las URLs de reserva provistas en los datos de entrada, sin inventar ni modificar enlaces.
                """


class EvaluadorIA:

    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise ValueError("Falta la credencial del proveedor de IA")
        self._cliente = genai.Client(api_key=settings.GEMINI_API_KEY)

    def evaluar_lote(
            self,
            hospedajes: list[Hospedaje],
            presupuesto_maximo_noche: float,
            preferencias: str,
    ) -> tuple[LoteEvaluacionesIA, dict[int, Hospedaje]] | None:
        candidatos = preseleccionar_candidatos(hospedajes, presupuesto_maximo_noche)

        if not candidatos:
            logger.warning("No se encontraron hospedajes dentro del presupuesto.")
            return None

        hospedaje_por_id_temporal = {}
        resumen_candidatos = []
        for id_temporal, hospedaje in enumerate(candidatos, start=1):
            hospedaje_por_id_temporal[id_temporal] = hospedaje
            resumen_candidatos.append({
                "id_temporal": id_temporal,
                "nombre": hospedaje.nombre,
                "precio_noche": hospedaje.precio_noche,
                "calificacion": hospedaje.calificacion,
                "direccion": hospedaje.direccion,
                "url_reserva": hospedaje.url_reserva,
            })

        prompt = _prompt_evaluacion(
            resumen_candidatos, presupuesto_maximo_noche, preferencias
        )

        for intento in range(settings.GEMINI_MAX_REINTENTOS + 1):
            try:
                respuesta_gemini = self._cliente.models.generate_content(
                    model=MODELO_IA,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=LoteEvaluacionesIA,
                    ),
                )
                lote_evaluado = LoteEvaluacionesIA.model_validate_json(respuesta_gemini.text)
                return lote_evaluado, hospedaje_por_id_temporal
            except Exception as error:
                logger.error("Error al evaluar el lote de hospedajes: tipo=%s", type(error).__name__)
                if intento >= settings.GEMINI_MAX_REINTENTOS:
                    raise EvaluacionIALoteError(
                        "evaluar_lote",
                        "El lote agotó los reintentos",
                    ) from error

                time.sleep(settings.GEMINI_BACKOFF_BASE * (2 ** intento))

        return None

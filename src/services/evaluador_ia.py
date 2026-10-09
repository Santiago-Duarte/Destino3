import json
import logging
import time

from google import genai
from google.genai import types

from src.config import settings
from src.exceptions.evaluacion_ia import EvaluacionIALoteError
from src.models.evaluacion_ia import LoteEvaluacionesIA
from src.models.hospedaje import Hospedaje

logger = logging.getLogger(__name__)


def seleccionar_candidatos(hospedajes: list[Hospedaje], presupuesto_max: float) -> list[Hospedaje]:
    """Preselecciona los hospedajes que pasarán a la evaluación del modelo.

    Filtra los que exceden el presupuesto o no tienen precio y luego ordena por
    calificación descendente (los empates se resuelven por precio ascendente),
    quedándose con los 5 primeros.

    Args:
        hospedajes: Hospedajes disponibles obtenidos de la búsqueda.
        presupuesto_max: Precio por noche máximo en USD.

    Returns:
        Hasta 5 hospedajes ordenados de mejor a peor relación calidad-precio;
        vacía si ninguno cumple el presupuesto.
    """
    dentro_de_presupuesto = [
        h for h in hospedajes
        if h.precio_noche is not None and h.precio_noche <= presupuesto_max
    ]

    return sorted(
        dentro_de_presupuesto,
        key=lambda h: (-(h.calificacion or 0), h.precio_noche)
    )[:5]


def _construir_prompt(resumen_candidatos: list[dict], presupuesto_max: float, preferencias: str) -> str:
    return f"""
                Eres un asistente experto en viajes. Revisa la siguiente lista de hospedajes en formato JSON:
                {json.dumps(resumen_candidatos, ensure_ascii=False, indent=4)}

                Criterios del usuario:
                - Presupuesto máximo por noche: USD ${presupuesto_max}
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
            raise ValueError("GEMINI_API_KEY no está definida")
        self._cliente = genai.Client(api_key=settings.GEMINI_API_KEY)

    def evaluar_lote(
            self,
            hospedajes: list[Hospedaje],
            presupuesto_max: float,
            preferencias: str,
    ) -> tuple[LoteEvaluacionesIA, dict[int, Hospedaje]] | None:
        """Pide a Gemini que elija y puntúe los 3 mejores hospedajes de la lista.

        Asigna a cada candidato un ``id_temporal`` correlativo para que el modelo
        responda con JSON estructurado sin riesgo de confundir registros, y
        conserva el mapeo id_temporal -> hospedaje para traducir la respuesta.

        Args:
            hospedajes: Candidatos disponibles.
            presupuesto_max: Presupuesto máximo por noche en USD, incluido en el prompt.
            preferencias: Criterios adicionales del usuario (vista, parqueadero, etc.).

        Returns:
            Una tupla ``(respuesta_ia, hospedajes_por_id_temporal)`` donde
            ``respuesta_ia`` contiene el top 3 y el segundo elemento traduce
            cada ``id_temporal`` a su hospedaje original, o ``None`` si no hay
            candidatos.

        Raises:
            EvaluacionIALoteError: si Gemini sigue fallando después de agotar
                los reintentos configurados.
        """
        candidatos = seleccionar_candidatos(hospedajes, presupuesto_max)

        if not candidatos:
            logger.warning("No se encontraron hospedajes dentro del presupuesto.")
            return None

        hospedajes_por_id_temporal = {}
        resumen_candidatos = []
        for id_temporal, hospedaje in enumerate(candidatos, start=1):
            hospedajes_por_id_temporal[id_temporal] = hospedaje
            resumen_candidatos.append({
                "id_temporal": id_temporal,
                "nombre": hospedaje.nombre,
                "precio_noche": hospedaje.precio_noche,
                "calificacion": hospedaje.calificacion,
                "direccion": hospedaje.direccion,
                "url_reserva": hospedaje.url_reserva
            })

        prompt = _construir_prompt(resumen_candidatos, presupuesto_max, preferencias)

        for intento in range(settings.GEMINI_MAX_REINTENTOS + 1):
            try:
                response = self._cliente.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=LoteEvaluacionesIA,
                    ),
                )
                respuesta = LoteEvaluacionesIA.model_validate_json(response.text)
                return respuesta, hospedajes_por_id_temporal
            except Exception as error:
                logger.error("Error al evaluar el lote de hospedajes: %s", error)
                if intento >= settings.GEMINI_MAX_REINTENTOS:
                    raise EvaluacionIALoteError(
                        "Gemini",
                        "evaluar_lote",
                        "El lote agotó los reintentos",
                    ) from error

                espera = settings.GEMINI_BACKOFF_BASE * (2 ** intento)
                time.sleep(espera)

        return None

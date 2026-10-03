import os
import json

from google import genai
from google.genai import types
from src.models.hospedaje import Hospedaje
from src.models.evaluacion import Evaluacion
from src.models.evaluacion_ia import EvaluacionIAOutput, LoteEvaluacionesIA


def convertir_a_evaluacion(dto: EvaluacionIAOutput, hospedaje_id: int) -> Evaluacion:
    return Evaluacion(
        resumen_ejecutivo=dto.resumen_ejecutivo,
        puntos_fuertes=dto.puntos_fuertes,
        puntos_debiles=dto.puntos_debiles,
        score_calidad_precio=dto.score_calidad_precio,
        hospedaje_id=hospedaje_id,
    )


def seleccionar_candidatos(s: list[Hospedaje], presupuesto_max: float) -> list[Hospedaje]:
    """Preselecciona los hospedajes que pasarán a la evaluación del modelo.

    Filtra los que exceden el presupuesto o no tienen precio y luego ordena por
    calificación descendente (los empates se resuelven por precio ascendente),
    quedándose con los 5 primeros.

    Args:
        s: Hospedajes disponibles obtenidos de la búsqueda.
        presupuesto_max: Precio por noche máximo en USD.

    Returns:
        Hasta 5 hospedajes ordenados de mejor a peor relación calidad-precio;
        vacía si ninguno cumple el presupuesto.
    """
    candidatos_validos = [
        h for h in s
        if h.precio_noche is not None and h.precio_noche <= presupuesto_max
    ]
    candidatos_ordenados = sorted(
        candidatos_validos,
        key=lambda h: (-(h.calificacion or 0), h.precio_noche)
    )[:5]

    return candidatos_ordenados


class AIEvaluator:

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está definida")
        self.client = genai.Client(api_key=api_key)

    def evaluar_hospedaje(
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
            Una tupla ``(respuesta_ia, mapping)`` donde ``respuesta_ia`` contiene
            el top 3 y ``mapping`` traduce cada ``id_temporal`` a su hospedaje
            original, o ``None`` si no hay candidatos o Gemini falla.

        Raises:
            ValueError: Si la variable de entorno ``GEMINI_API_KEY`` no está definida.
        """

        mejores = seleccionar_candidatos(hospedajes, presupuesto_max)

        if not mejores:
            print("No se encontraron hospedajes dentro del presupuesto.")
            return None

        mapping = {}
        lista_resumida = []
        for i, hospedaje in enumerate(mejores, start=1):
            mapping[i] = hospedaje
            lista_resumida.append({
                "id_temporal": i,
                "nombre": hospedaje.nombre,
                "precio_noche": hospedaje.precio_noche,
                "calificacion": hospedaje.calificacion,
                "direccion": hospedaje.direccion,
                "url_reserva": hospedaje.url_reserva
            })

        prompt = f"""
                Eres un asistente experto en viajes. Revisa la siguiente lista de hospedajes en formato JSON:
                {json.dumps(lista_resumida, ensure_ascii=False, indent=4)}

                Criterios del usuario:
                - Presupuesto máximo por noche: USD ${presupuesto_max}
                - Preferencias adicionales: {preferencias if preferencias else "Ninguna especificada"}

                Instrucciones:
                1. Selecciona las **3 mejores opciones** de hospedaje de la lista que cumplan con el presupuesto.
                2. Para cada opción, utiliza el `id_temporal` exacto del JSON para mantener la relación.
                3. Proporciona para cada una: un resumen ejecutivo, puntos fuertes, puntos débiles y un `score_calidad_precio` del 1 al 10.
                4. Usa únicamente las URLs de reserva provistas en los datos de entrada, sin inventar ni modificar enlaces.
                """

        try:
            response = self.client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=LoteEvaluacionesIA,
                ),
            )
            respuesta = LoteEvaluacionesIA.model_validate_json(response.text)
            return respuesta, mapping
        except Exception as e:
            print(f"Error al evaluar hospedaje: {e}")
            return None



import os
import json
from pathlib import Path

from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai
from google.genai import types
from src.models.hospedaje import Hospedaje
from src.services.api_searcher import construir_link_google_hotels

load_dotenv()


class EvaluacionIAOutput(BaseModel):
    id_temporal: int
    resumen_ejecutivo: str
    puntos_fuertes: str
    puntos_debiles: str
    score_calidad_precio: int = Field(ge=1, le=10)


class Top3Evaluaciones(BaseModel):
    top_3: list[EvaluacionIAOutput]


def seleccionar_candidatos( s: list, presupuesto_max: float) -> list:
    candidatos_validos = [
        h for h in hospedajes
        if h.precio_noche is not None and h.precio_noche <= presupuesto_max
    ]
    candidatos_ordenados = sorted(
        candidatos_validos,
        key=lambda h: (-(h.calificacion or 0), h.precio_noche)
    )[:5]

    return candidatos_ordenados


class AIEvaluator:

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está definida")
        self.client = genai.Client(api_key=api_key)

    def evaluar_hospedaje(self, hospedajes: list[Hospedaje], presupuesto_max: float, preferencias: str):

        mejores = seleccionar_candidatos(hospedajes, presupuesto_max)

        if not mejores:
            print("No se encontraron hospedajes dentro del presupuesto.")
            return None

        lista_resumida = []
        for i, hospedaje in enumerate(mejores, start=1):
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
                    response_schema=Top3Evaluaciones,
                ),
            )
            return Top3Evaluaciones.model_validate_json(response.text)
        except Exception as e:
            print(f"Error al evaluar hospedaje: {e}")
            return None


if __name__ == "__main__":

    ruta_json = Path(__file__).resolve().parents[2] / "respuesta_prueba.json"
    with open(ruta_json, "r", encoding="utf-8") as f:
        datos = json.load(f)

    hospedajes = []
    parametros_busqueda = datos.get("search_parameters", {})
    fecha_inicio = parametros_busqueda.get("check_in_date")
    fecha_fin = parametros_busqueda.get("check_out_date")

    for p in datos.get("properties", []):
        rate = p.get("rate_per_night", {})
        property_token = p.get("property_token")
        if property_token and fecha_inicio and fecha_fin:
            url_reserva = construir_link_google_hotels(
                property_token,
                fecha_inicio,
                fecha_fin,
                parametros_busqueda.get("q", "")
            )
        else:
            url_reserva = p.get("link", "")
        h = Hospedaje (
            destino_id=None,
            nombre=p.get("name", "sin nombre"),
            tipo="hotel",
            precio_noche=float(rate.get("extracted_lowest", 0)),
            calificacion=p.get("overall_rating", 0.0),
            direccion=p.get("description", "Sin dirección"),
            url_reserva=url_reserva
        )
        hospedajes.append(h)

    evaluador = AIEvaluator()
    analisis = evaluador.evaluar_hospedaje(
        hospedajes,
        80,
        "Con parqueadero, vista al mar, dos cuartos, para cuatro personas"
    )

    print("\n--- Resultado del Análisis de Gemini ---")
    print(analisis.model_dump_json(indent=4) if analisis else "sin resultados")
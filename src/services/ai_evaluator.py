import os
import json
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from src.models.hospedaje import Hospedaje
from src.services.api_searcher import construir_link_google_hotels

load_dotenv()

class AIEvaluator:

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está definida")
        self.client = genai.Client(api_key=api_key)

    def evaluar_hospedaje(self, hospedajes: list[Hospedaje], presupuesto_max: float, preferencias: str):
        dentro_del_presupuesto = [
            hospedaje for hospedaje in hospedajes
            if hospedaje.precio_noche is not None and hospedaje.precio_noche <= presupuesto_max
        ]

        if not dentro_del_presupuesto:
            print("No se encontraron hospedajes dentro del presupuesto.")
            return None

        mejores = sorted(
            dentro_del_presupuesto,
            key=lambda h: (-(h.calificacion or 0), h.precio_noche)
        )[:5]

        lista_resumida = []
        for hospedaje in mejores:
            lista_resumida.append({
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
                1. Identifica el MEJOR hospedaje de la lista (todos cumplen con el presupuesto).
                2. Muestra el nombre del hospedaje seleccionado y su enlace de reserva en formato Markdown, usando únicamente la propiedad 'url_reserva' correspondiente a ese hospedaje en el JSON (ejemplo: [Ver o Reservar en Google Hotels](URL)). Queda estrictamente prohibido inventar o modificar enlaces.
                3. Explica brevemente por qué es la mejor opción.
                4. Menciona un aspecto positivo y un caso límite o desventaja si aplica.
                """

        try:
            response = self.client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt
            )
            return response.text
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
        "Busco algo bien ubicado, limpio y con buena calificacion y que este cerca de la playa"
    )

    print("\n--- Resultado del Análisis de Gemini ---")
    print(analisis)
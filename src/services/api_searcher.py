import os, requests, json
from urllib.parse import quote
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pathlib import Path
from src.services.db_service import obtener_o_crear_destino
from src.models.destino import Destino
from src.models.hospedaje import Hospedaje

load_dotenv()

RUTA_RESPUESTA_PRUEBA = Path(__file__).resolve().parents[2] / "respuesta_prueba.json"


def construir_link_google_hotels(property_token, fecha_inicio, fecha_fin, query):
    return (
        f"https://www.google.com/travel/hotels/entity/{property_token}"
        f"?check_in={fecha_inicio}&check_out={fecha_fin}"
        f"&q={quote(query)}&hl=es&gl=us"
    )


def buscar_hospedajes_raw(ciudad, pais, presupuesto_maximo=None):

    api_key = os.getenv("SERPAPI_KEY")
    if api_key is None:
        print("No se encontro la clave de la API")
        return None

    fecha_inicio = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    fecha_fin = (datetime.now() + timedelta(days=9)).strftime("%Y-%m-%d")

    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_hotels",
        "q": f"hoteles en {ciudad} {pais}",
        "check_in_date": fecha_inicio,
        "check_out_date": fecha_fin,
        "currency": "USD",
        "hl": "es",
        "api_key": api_key,
    }

    if presupuesto_maximo is not None:
        params["max_price"] = presupuesto_maximo

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        resultado = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error al buscar hospedajes: {e}")
        return None

    if "error" in resultado:
        print(f"Error de la API: {resultado['error']}")
        return None

    return resultado


def buscar_hospedajes(ciudad, pais, presupuesto_maximo=None):
    resultado = buscar_hospedajes_raw(ciudad, pais, presupuesto_maximo)

    if not resultado or "properties" not in resultado:
        return []

    destino = Destino(ciudad=ciudad, pais=pais)

    id_destino = obtener_o_crear_destino(destino)

    if id_destino is None:
        print("No se pudo obtener o crear el destino")
        return []

    if resultado:

        resultado['city'] = ciudad
        resultado['country'] = pais

        with open(RUTA_RESPUESTA_PRUEBA, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=4)
        print("Respuesta guardad en respuesta_prueba.json")

    hospedajes = []

    parametros_busqueda = resultado.get("search_parameters", {})
    fecha_inicio = parametros_busqueda.get("check_in_date")
    fecha_fin = parametros_busqueda.get("check_out_date")

    for lugar in resultado["properties"]:
        rate_info = lugar.get("rate_per_night", {})
        precio = rate_info.get("extracted_lowest", 0.0)

        if presupuesto_maximo is not None and precio > presupuesto_maximo:
            continue

        property_token = lugar.get("property_token")
        if property_token and fecha_inicio and fecha_fin:
            url_reserva = construir_link_google_hotels(
                property_token,
                fecha_inicio,
                fecha_fin,
                f"hoteles en {ciudad} {pais}"
            )
        else:
            url_reserva = lugar.get("link", "")

        hospedaje = Hospedaje(
            destino_id=id_destino,
            nombre=lugar.get("name", "Sin nombre"),
            tipo="hotel",
            precio_noche=precio,
            calificacion=lugar.get("overall_rating", 0.0),
            direccion=lugar.get("description", "Sin dirección disponible"),
            url_reserva=url_reserva
        )
        hospedajes.append(hospedaje)

    return hospedajes


if __name__ == "__main__":
    archivo_mock = RUTA_RESPUESTA_PRUEBA

    # Si ya tenemos la respuesta guardada, la leemos para no consumir créditos
    if os.path.exists(archivo_mock):
        with open(archivo_mock, "r", encoding="utf-8") as f:
            datos = json.load(f)

        hotel_ejemplo = datos["properties"][0]
        print("Objeto rate_per_night completo:")
        print(hotel_ejemplo.get("rate_per_night"))
    else:
        # Si no existe, ejecutamos la búsqueda para generar el archivo por primera vez
        print("No se encontró archivo local. Realizando petición a SerpAPI...")
        lista_hospedajes = buscar_hospedajes("Cartagena", "Colombia")
        print(f"Se mapearon {len(lista_hospedajes)} hospedajes.")
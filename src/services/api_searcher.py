from asyncio import timeout

import requests, os
from dotenv import load_dotenv

load_dotenv()

def buscar_hospedajes_raw(ciudad, pais, presupuesto_maximo=None):

    API_KEY = os.getenv("SERPAPI_KEY")
    if API_KEY is None:
        print("No se encontro la clave de la API")
        return None

    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_hotels",
        "q": f"hoteles {ciudad} {pais}",
        "currency": "USD",
        "hl":"es",
        "api_key": API_KEY,
    }

    if presupuesto_maximo is not None:
        params["max_price"] = presupuesto_maximo

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error al buscar hospedajes: {e}")
        return None

if __name__ == "__main__":
    resultado = buscar_hospedajes_raw("Cartagena", "Colombia")
    if resultado and "properties" in resultado:
        print(f"Se encontraron {len(resultado['properties'])} hospedajes.")
        print(resultado['properties'][0])
    else:
        print("No se obtuvieron resultados o hubo un error.")
import os, requests, json
from dotenv import load_dotenv
from datetime import datetime, timedelta

from src.models.hospedaje import Hospedaje

load_dotenv()


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

    hospedajes = []

    for lugar in resultado["properties"]:
        rate_info = lugar.get("rate_per_night", {})
        precio = rate_info.get("lowest_extracted", 0.0)

        if presupuesto_maximo is not None and precio > presupuesto_maximo:
            continue

        hospedaje = Hospedaje(
            destino_id=None,
            nombre=lugar.get("name", "Sin nombre"),
            tipo="hotel",
            precio_noche=precio,
            calificacion=lugar.get("overall_rating", 0.0),
            direccion=lugar.get("description", "Sin dirección disponible"),
            url_reserva=lugar.get("link", "")
        )
        hospedajes.append(hospedaje)

    return hospedajes


if __name__ == "__main__":
    lista_hospedajes = buscar_hospedajes("Cartagena", "Colombia")
    print(f"Se mapearon {len(lista_hospedajes)} objetos Hospedaje.")

    if lista_hospedajes:
        primer_hotel = lista_hospedajes[0]
        print(f"Nombre: {primer_hotel.nombre}")
        print(f"Precio/Noche: {primer_hotel.precio_noche}")
        print(f"Calificación: {primer_hotel.calificacion}")

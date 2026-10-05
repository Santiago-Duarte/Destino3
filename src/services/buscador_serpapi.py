import os, requests, json
from urllib.parse import quote
from datetime import datetime, timedelta
from pathlib import Path
# env se carga centralizado en src/config/__init__.py (importado transitivamente via repositories)
from src.repositories.destino_repository import DestinoRepository
from src.models.destino import Destino
from src.models.hospedaje import Hospedaje

RUTA_RESPUESTA_PRUEBA = Path(__file__).resolve().parents[2] / "respuesta_prueba.json"


def construir_link_google_hotels(property_token: str, fecha_inicio: str, fecha_fin: str, query: str) -> str:
    return (
        f"https://www.google.com/travel/hotels/entity/{property_token}"
        f"?check_in={fecha_inicio}&check_out={fecha_fin}"
        f"&q={quote(query)}&hl=es&gl=us"
    )


def buscar_hospedajes_raw(ciudad: str, pais: str, presupuesto_maximo: float | None = None) -> dict | None:
    """Consulta la API de Google Hotels vía SerpAPI y devuelve la respuesta sin procesar.

    Fija de forma automática una estancia de dos noches a partir de una semana
    y, si se indica presupuesto, lo traduce al parámetro ``max_price`` de la API.

    Args:
        ciudad: Nombre de la ciudad a buscar.
        pais: País de la ciudad.
        presupuesto_maximo: Precio por noche máximo en USD; si es ``None``
            no se aplica filtro de precio.

    Returns:
        El JSON de la respuesta de SerpAPI, o ``None`` si falta la clave
        ``SERPAPI_KEY``, la petición falla o la API devuelve un error.
    """

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


def buscar_hospedajes(ciudad: str, pais: str, presupuesto_maximo: float | None = None) -> list[Hospedaje]:
    """Busca hospedajes en SerpAPI, los persiste y los convierte en modelos.

    Garantiza que el destino exista en base de datos antes de mapear los
    resultados, por lo que necesita conexión a la base.

    Args:
        ciudad: Nombre de la ciudad a buscar.
        pais: País de la ciudad.
        presupuesto_maximo: Precio por noche máximo en USD; si es ``None``
            no se aplica filtro de precio.

    Returns:
        La lista de hospedajes mapeados; vacía si la API falla, no hay
        resultados o no se puede obtener o crear el destino.
    """
    resultado = buscar_hospedajes_raw(ciudad, pais, presupuesto_maximo)

    if not resultado or "properties" not in resultado:
        return []

    destino = Destino(ciudad=ciudad, pais=pais)

    destino_repo = DestinoRepository()
    id_destino = destino_repo.obtener_o_crear(destino)

    if id_destino is None:
        print("No se pudo obtener o crear el destino")
        return []

    escribir_ciudad_pais(resultado, ciudad, pais)

    hospedajes = []

    parametros_busqueda = resultado.get("search_parameters", {})
    fecha_inicio = parametros_busqueda.get("check_in_date")
    fecha_fin = parametros_busqueda.get("check_out_date")

    lista_hospedajes = crear_lista_hospedajes(
        resultado,
        id_destino,
        fecha_inicio,
        fecha_fin,
        presupuesto_maximo,
        ciudad,
        pais,
        hospedajes
    )

    return lista_hospedajes

def escribir_ciudad_pais(resultado: dict, ciudad: str, pais: str) -> None:
    datos = resultado.copy()
    datos['city'] = ciudad
    datos['country'] = pais

    with open(RUTA_RESPUESTA_PRUEBA, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)
    print("Respuesta guardad en respuesta_prueba.json")


def crear_lista_hospedajes(
        resultado: dict,
        id_destino: int,
        fecha_inicio: str,
        fecha_fin: str,
        presupuesto_maximo: float | None,
        ciudad: str,
        pais: str,
        hospedajes: list[Hospedaje]
) -> list[Hospedaje]:
    """Convierte las ``properties`` de la respuesta de SerpAPI en objetos ``Hospedaje``.

    Descarta los lugares sin precio o por encima del presupuesto y construye la
    URL de reserva a partir del ``property_token`` cuando hay fechas de estancia;
    si no, usa el enlace genérico reportado por la API.

    Args:
        resultado: Respuesta cruda de SerpAPI con la clave ``properties``.
        id_destino: Identificador del destino ya persistido en base de datos.
        fecha_inicio: Fecha de check-in en formato ``YYYY-MM-DD``.
        fecha_fin: Fecha de check-out en formato ``YYYY-MM-DD``.
        presupuesto_maximo: Precio por noche máximo en USD; si es ``None``
            no se filtra por precio.
        ciudad: Ciudad usada para armar el enlace de reserva.
        pais: País usado para armar el enlace de reserva.
        hospedajes: Lista que se incrementa en sitio con cada hospedaje válido.

    Returns:
        La misma lista ``hospedajes`` recibida, con los hospedajes añadidos.
    """
    for lugar in resultado["properties"]:
        rate_info = lugar.get("rate_per_night", {})
        precio = rate_info.get("extracted_lowest")

        if presupuesto_maximo is not None and (precio is None or precio > presupuesto_maximo):
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
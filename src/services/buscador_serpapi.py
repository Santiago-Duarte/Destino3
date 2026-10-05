import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import requests

from src.config import settings
from src.models.destino import Destino
from src.models.hospedaje import Hospedaje
from src.repositories.destino_repository import DestinoRepository

logger = logging.getLogger(__name__)

URL_SERPAPI = "https://serpapi.com/search.json"
RUTA_RESPUESTA_PRUEBA = Path(__file__).resolve().parents[2] / "respuesta_prueba.json"


def _texto_de_busqueda(ciudad: str, pais: str) -> str:
    return f"hoteles en {ciudad} {pais}"


def construir_link_google_hotels(property_token: str, fecha_inicio: str, fecha_fin: str, query: str) -> str:
    return (
        f"https://www.google.com/travel/hotels/entity/{property_token}"
        f"?check_in={fecha_inicio}&check_out={fecha_fin}"
        f"&q={quote(query)}&hl=es&gl=us"
    )


def consultar_serpapi(ciudad: str, pais: str, presupuesto_maximo: float | None = None) -> dict | None:
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
    if not settings.SERPAPI_KEY:
        logger.error("Falta la clave de la API (SERPAPI_KEY)")
        return None

    check_in = datetime.now() + timedelta(days=7)
    check_out = check_in + timedelta(days=2)

    params = {
        "engine": "google_hotels",
        "q": _texto_de_busqueda(ciudad, pais),
        "check_in_date": check_in.strftime("%Y-%m-%d"),
        "check_out_date": check_out.strftime("%Y-%m-%d"),
        "currency": "USD",
        "hl": "es",
        "api_key": settings.SERPAPI_KEY,
    }

    if presupuesto_maximo is not None:
        params["max_price"] = presupuesto_maximo

    try:
        response = requests.get(URL_SERPAPI, params=params, timeout=settings.SERPAPI_TIMEOUT)
        response.raise_for_status()
        resultado = response.json()
    except requests.exceptions.RequestException as e:
        logger.error("Error al buscar hospedajes: %s", e)
        return None

    if "error" in resultado:
        logger.error("Error de la API: %s", resultado["error"])
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
    resultado = consultar_serpapi(ciudad, pais, presupuesto_maximo)

    if not resultado or "properties" not in resultado:
        return []

    try:
        id_destino = DestinoRepository().obtener_o_crear(Destino(ciudad=ciudad, pais=pais))
    except Exception as error:
        logger.error("No se pudo obtener o crear el destino: %s", error)
        return []

    guardar_respuesta_prueba(resultado, ciudad, pais)

    return mapear_propiedades_en_hospedajes(resultado, id_destino, presupuesto_maximo, ciudad, pais)


def guardar_respuesta_prueba(resultado: dict, ciudad: str, pais: str) -> None:
    datos = resultado.copy()
    datos['city'] = ciudad
    datos['country'] = pais

    with open(RUTA_RESPUESTA_PRUEBA, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)
    logger.info("Respuesta guardada en respuesta_prueba.json")


def mapear_propiedades_en_hospedajes(
        resultado: dict,
        id_destino: int,
        presupuesto_maximo: float | None,
        ciudad: str,
        pais: str,
) -> list[Hospedaje]:
    """Convierte las ``properties`` de la respuesta de SerpAPI en objetos ``Hospedaje``.

    Si se indica presupuesto, descarta los lugares sin precio o por encima del
    límite; sin presupuesto, conserva también los que no traen precio. Construye
    la URL de reserva a partir del ``property_token`` cuando la respuesta trae
    fechas de estancia; si no, usa el enlace genérico reportado por la API.

    Args:
        resultado: Respuesta cruda de SerpAPI con las claves ``properties`` y
            ``search_parameters`` (de ahí toma las fechas de la estancia).
        id_destino: Identificador del destino ya persistido en base de datos.
        presupuesto_maximo: Precio por noche máximo en USD; si es ``None``
            no se filtra por precio.
        ciudad: Ciudad usada para armar el enlace de reserva.
        pais: País usado para armar el enlace de reserva.

    Returns:
        Los hospedajes mapeados, en el mismo orden que la respuesta.
    """
    parametros_busqueda = resultado.get("search_parameters", {})
    fecha_inicio = parametros_busqueda.get("check_in_date")
    fecha_fin = parametros_busqueda.get("check_out_date")
    texto_busqueda = _texto_de_busqueda(ciudad, pais)

    hospedajes = []
    for lugar in resultado["properties"]:
        rate_info = lugar.get("rate_per_night", {})
        precio = rate_info.get("extracted_lowest")

        if presupuesto_maximo is not None and (precio is None or precio > presupuesto_maximo):
            continue

        property_token = lugar.get("property_token")
        if property_token and fecha_inicio and fecha_fin:
            url_reserva = construir_link_google_hotels(property_token, fecha_inicio, fecha_fin, texto_busqueda)
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

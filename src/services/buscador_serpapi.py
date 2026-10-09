import logging
import threading
import time
from datetime import datetime, timedelta
from urllib.parse import quote

import requests

from src.config import settings
from src.exceptions import SerpApiError
from src.models.destino import Destino
from src.models.hospedaje import Hospedaje
from src.repositories.destino_repository import DestinoRepository

logger = logging.getLogger(__name__)

_rate_limit_lock = threading.Lock()
_ultima_llamada_serpapi = 0.0

URL_SERPAPI = "https://serpapi.com/search.json"


def _texto_de_busqueda(ciudad: str, pais: str) -> str:
    return f"hoteles en {ciudad} {pais}"


def construir_link_google_hotels(property_token: str, fecha_inicio: str, fecha_fin: str, query: str) -> str:
    return (
        f"https://www.google.com/travel/hotels/entity/{property_token}"
        f"?check_in={fecha_inicio}&check_out={fecha_fin}"
        f"&q={quote(query)}&hl=es&gl=us"
    )


def _esperar_rate_limit() -> None:
    """Serializa las llamadas al proveedor respetando el RPS configurado."""
    global _ultima_llamada_serpapi

    rate_limit_rps = settings.SERPAPI_RATE_LIMIT_RPS
    if rate_limit_rps <= 0:
        return

    intervalo = 1.0 / rate_limit_rps
    with _rate_limit_lock:
        ahora = time.monotonic()
        espera = intervalo - (ahora - _ultima_llamada_serpapi)
        if espera > 0:
            time.sleep(espera)
        _ultima_llamada_serpapi = time.monotonic()


def _retry_after(response: requests.Response) -> float | None:
    """Obtiene ``Retry-After`` en segundos si el header es válido."""
    valor = response.headers.get("Retry-After")
    if valor is None:
        return None
    try:
        return max(0.0, float(valor))
    except (TypeError, ValueError):
        return None


def _crear_parametros_busqueda(
        ciudad: str,
        pais: str,
        presupuesto_maximo: float | None,
        fecha_inicio: datetime,
        fecha_fin: datetime,
) -> dict:
    parametros_busqueda = {
        "engine": "google_hotels",
        "q": _texto_de_busqueda(ciudad, pais),
        "check_in_date": fecha_inicio.strftime("%Y-%m-%d"),
        "check_out_date": fecha_fin.strftime("%Y-%m-%d"),
        "currency": "USD",
        "hl": "es",
        "api_key": settings.SERPAPI_KEY,
    }

    if presupuesto_maximo is not None:
        parametros_busqueda["max_price"] = presupuesto_maximo

    return parametros_busqueda


def _consultar_pagina_con_reintentos(parametros: dict) -> dict | None:
    for numero_intento in range(settings.SERPAPI_MAX_REINTENTOS + 1):
        _esperar_rate_limit()
        try:
            respuesta_http = requests.get(
                URL_SERPAPI,
                params=parametros,
                timeout=settings.SERPAPI_TIMEOUT,
            )
            respuesta_http.raise_for_status()
            return respuesta_http.json()
        except requests.exceptions.HTTPError as error:
            respuesta_error = error.response
            es_error_de_limite = (
                respuesta_error is not None
                and respuesta_error.status_code == 429
            )
            if not es_error_de_limite:
                logger.error("Error al buscar hospedajes: %s", error)
                raise SerpApiError("SerpAPI", "consulta", str(error)) from error

            if numero_intento >= settings.SERPAPI_MAX_REINTENTOS:
                logger.error("SerpAPI agotó los reintentos por límite de tasa")
                break

            espera_por_backoff = settings.SERPAPI_BACKOFF_BASE * (2 ** numero_intento)
            espera_indicada_por_serpapi = _retry_after(respuesta_error)
            espera_reintento = max(
                espera_por_backoff,
                espera_indicada_por_serpapi or 0.0,
            )
            logger.warning(
                "SerpAPI respondió 429; reintento %s de %s en %.2f segundos",
                numero_intento + 1,
                settings.SERPAPI_MAX_REINTENTOS,
                espera_reintento,
            )
            if espera_reintento > 0:
                time.sleep(espera_reintento)
        except requests.exceptions.RequestException as error:
            logger.error("Error al buscar hospedajes: %s", error)
            raise SerpApiError("SerpAPI", "consulta", str(error)) from error

    return None


def _obtener_propiedades_paginadas(
        parametros_base: dict,
        max_paginas: int,
        max_resultados: int,
) -> tuple[dict | None, list[dict]]:

    propiedades_acumuladas: list[dict] = []
    primera_respuesta: dict | None = None
    siguiente_token: str | None = None
    paginas_consultadas = 0

    while paginas_consultadas < max_paginas and len(propiedades_acumuladas) < max_resultados:
        parametros_pagina = dict(parametros_base)
        if siguiente_token is not None:
            parametros_pagina["next_page_token"] = siguiente_token

        respuesta_pagina = _consultar_pagina_con_reintentos(parametros_pagina)
        if respuesta_pagina is None:
            break

        if "error" in respuesta_pagina:
            logger.error("Error de la API: %s", respuesta_pagina["error"])
            raise SerpApiError("SerpAPI", "consulta", str(respuesta_pagina["error"]))

        if primera_respuesta is None:
            primera_respuesta = respuesta_pagina

        propiedades_acumuladas.extend(respuesta_pagina.get("properties", []))
        paginas_consultadas += 1

        if len(propiedades_acumuladas) >= max_resultados:
            propiedades_acumuladas = propiedades_acumuladas[:max_resultados]
            break

        paginacion = respuesta_pagina.get("serpapi_pagination") or {}
        siguiente_token = paginacion.get("next_page_token")
        if not siguiente_token:
            break

    return primera_respuesta, propiedades_acumuladas


def _consolidar_respuesta(
        primera_respuesta: dict | None,
        propiedades_acumuladas: list[dict],
        parametros_base: dict,
) -> dict:
    if primera_respuesta is None:
        return {"search_parameters": parametros_base, "properties": []}

    respuesta_consolidada = {}
    for clave, valor in primera_respuesta.items():
        if clave not in ("properties", "serpapi_pagination"):
            respuesta_consolidada[clave] = valor
    respuesta_consolidada["properties"] = propiedades_acumuladas
    return respuesta_consolidada


def consultar_serpapi(ciudad: str, pais: str, presupuesto_maximo: float | None = None) -> dict | None:
    """Consulta la API de Google Hotels vía SerpAPI y devuelve una respuesta consolidada.

    Fija de forma automática una estancia de dos noches a partir de una semana
    y, si se indica presupuesto, lo traduce al parámetro ``max_price`` de la API.

    Recorre las páginas que devuelva SerpAPI (``serpapi_pagination.next_page_token``)
    respetando los límites operativos de ``SERPAPI_MAX_PAGES`` y
    ``SERPAPI_MAX_RESULTS``: al alcanzar cualquiera de ellos detiene la
    obtención de nuevas páginas y conserva los resultados acumulados hasta ese
    momento (RF-3, RF-9, RF-10). La respuesta consolidada expone las
    ``search_parameters`` de la primera página y las ``properties`` acumuladas
    en orden; no expone ``serpapi_pagination``.

    Args:
        ciudad: Nombre de la ciudad a buscar.
        pais: País de la ciudad.
        presupuesto_maximo: Precio por noche máximo en USD; si es ``None``
            no se aplica filtro de precio.

    Raises:
        SerpApiError: si falta la clave ``SERPAPI_KEY``, la petición de red
            falla o la API devuelve un error en su JSON. La capa superior
            decide cómo responder (constitución #6).
    """
    if not settings.SERPAPI_KEY:
        logger.error("Falta la clave de la API (SERPAPI_KEY)")
        raise SerpApiError(
            "SerpAPI",
            "configuracion",
            "Falta la clave de la API (SERPAPI_KEY)",
        )

    fecha_inicio = datetime.now() + timedelta(days=7)
    fecha_fin = fecha_inicio + timedelta(days=2)
    parametros_base = _crear_parametros_busqueda(
        ciudad,
        pais,
        presupuesto_maximo,
        fecha_inicio,
        fecha_fin,
    )
    primera_respuesta, propiedades_acumuladas = _obtener_propiedades_paginadas(
        parametros_base,
        settings.SERPAPI_MAX_PAGES,
        settings.SERPAPI_MAX_RESULTS,
    )
    return _consolidar_respuesta(
        primera_respuesta,
        propiedades_acumuladas,
        parametros_base,
    )


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
    try:
        resultado = consultar_serpapi(ciudad, pais, presupuesto_maximo)
    except SerpApiError as error:
        logger.error("La búsqueda de hospedajes falló: %s", error)
        return []

    if not resultado or "properties" not in resultado:
        return []

    try:
        id_destino = DestinoRepository().obtener_o_crear(Destino(ciudad=ciudad, pais=pais))
    except Exception as error:
        logger.error("No se pudo obtener o crear el destino: %s", error)
        return []

    return mapear_propiedades_en_hospedajes(resultado, id_destino, presupuesto_maximo, ciudad, pais)


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

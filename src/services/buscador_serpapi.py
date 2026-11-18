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

URL_SERPAPI = "https://serpapi.com/search.json"

_candado_rate_limit = threading.Lock()
_ultima_llamada = 0.0


def _consulta_hoteles(ciudad: str, pais: str) -> str:
    return f"hoteles en {ciudad} {pais}"


def construir_url_reserva(
        token_propiedad: str,
        fecha_entrada: str,
        fecha_salida: str,
        consulta: str,
) -> str:
    return (
        f"https://www.google.com/travel/hotels/entity/{token_propiedad}"
        f"?check_in={fecha_entrada}&check_out={fecha_salida}"
        f"&q={quote(consulta)}&hl=es&gl=us"
    )


def _esperar_turno() -> None:
    global _ultima_llamada

    llamadas_por_segundo = settings.SERPAPI_RATE_LIMIT_RPS
    if llamadas_por_segundo <= 0:
        return

    intervalo = 1.0 / llamadas_por_segundo
    with _candado_rate_limit:
        ahora = time.monotonic()
        espera = intervalo - (ahora - _ultima_llamada)
        if espera > 0:
            time.sleep(espera)
        _ultima_llamada = time.monotonic()


def _segundos_retry_after(respuesta: requests.Response) -> float | None:
    encabezado = respuesta.headers.get("Retry-After")
    if encabezado is None:
        return None
    try:
        return max(0.0, float(encabezado))
    except (TypeError, ValueError):
        return None


def _parametros_de_busqueda(
        ciudad: str,
        pais: str,
        precio_maximo_noche: float | None,
        fecha_entrada: datetime,
        fecha_salida: datetime,
) -> dict:
    parametros = {
        "engine": "google_hotels",
        "q": _consulta_hoteles(ciudad, pais),
        "check_in_date": fecha_entrada.strftime("%Y-%m-%d"),
        "check_out_date": fecha_salida.strftime("%Y-%m-%d"),
        "currency": "USD",
        "hl": "es",
        "api_key": settings.SERPAPI_KEY,
    }

    if precio_maximo_noche is not None:
        parametros["max_price"] = int(precio_maximo_noche)

    return parametros


def _pedir_pagina(parametros: dict) -> dict | None:
    for intento in range(settings.SERPAPI_MAX_REINTENTOS + 1):
        _esperar_turno()
        try:
            respuesta = requests.get(
                URL_SERPAPI,
                params=parametros,
                timeout=settings.SERPAPI_TIMEOUT,
            )
            respuesta.raise_for_status()
            return respuesta.json()
        except requests.exceptions.HTTPError as error:
            respuesta_fallida = error.response
            es_limite_de_tasa = (
                respuesta_fallida is not None
                and respuesta_fallida.status_code == 429
            )
            if not es_limite_de_tasa:
                logger.error("Error al consultar SerpAPI: tipo=%s", type(error).__name__)
                raise SerpApiError("consulta", type(error).__name__) from error

            if intento >= settings.SERPAPI_MAX_REINTENTOS:
                logger.error("SerpAPI agotó los reintentos por límite de tasa")
                break

            espera_backoff = settings.SERPAPI_BACKOFF_BASE * (2 ** intento)
            espera_retry_after = _segundos_retry_after(respuesta_fallida)
            espera = max(espera_backoff, espera_retry_after or 0.0)
            logger.warning(
                "SerpAPI respondió 429; reintento %s de %s en %.2f segundos",
                intento + 1,
                settings.SERPAPI_MAX_REINTENTOS,
                espera,
            )
            if espera > 0:
                time.sleep(espera)
        except requests.exceptions.RequestException as error:
            logger.error("Error al consultar SerpAPI: tipo=%s", type(error).__name__)
            raise SerpApiError("consulta", type(error).__name__) from error

    return None


def _recolectar_propiedades(
        parametros_base: dict,
        max_paginas: int,
        max_resultados: int,
) -> tuple[dict | None, list[dict]]:
    propiedades: list[dict] = []
    respuesta_inicial: dict | None = None
    token_siguiente_pagina: str | None = None
    paginas_leidas = 0

    while paginas_leidas < max_paginas and len(propiedades) < max_resultados:
        parametros_pagina = dict(parametros_base)
        if token_siguiente_pagina is not None:
            parametros_pagina["next_page_token"] = token_siguiente_pagina

        respuesta_pagina = _pedir_pagina(parametros_pagina)
        if respuesta_pagina is None:
            break

        if "error" in respuesta_pagina:
            logger.error("Error reportado por la API de SerpAPI")
            raise SerpApiError("consulta", "Error reportado por la API")

        if respuesta_inicial is None:
            respuesta_inicial = respuesta_pagina

        propiedades.extend(respuesta_pagina.get("properties", []))
        paginas_leidas += 1

        if len(propiedades) >= max_resultados:
            propiedades = propiedades[:max_resultados]
            break

        paginacion = respuesta_pagina.get("serpapi_pagination") or {}
        token_siguiente_pagina = paginacion.get("next_page_token")
        if not token_siguiente_pagina:
            break

    return respuesta_inicial, propiedades


def _unir_paginas(
        respuesta_inicial: dict | None,
        propiedades: list[dict],
        parametros_base: dict,
) -> dict:
    if respuesta_inicial is None:
        return {"search_parameters": parametros_base, "properties": []}

    respuesta_unida = {
        clave: valor
        for clave, valor in respuesta_inicial.items()
        if clave not in ("properties", "serpapi_pagination")
    }
    respuesta_unida["properties"] = propiedades
    return respuesta_unida


def consultar_serpapi(
        ciudad: str,
        pais: str,
        precio_maximo_noche: float | None = None,
) -> dict | None:
    if not settings.SERPAPI_KEY:
        logger.error("Falta la credencial requerida del proveedor")
        raise SerpApiError("configuracion", "Falta la credencial del proveedor")

    # Estancia provisoria: el flujo con fechas reales llega con RF-3.
    fecha_entrada = datetime.now() + timedelta(days=7)
    fecha_salida = fecha_entrada + timedelta(days=2)
    parametros_base = _parametros_de_busqueda(
        ciudad,
        pais,
        precio_maximo_noche,
        fecha_entrada,
        fecha_salida,
    )
    respuesta_inicial, propiedades = _recolectar_propiedades(
        parametros_base,
        settings.SERPAPI_MAX_PAGES,
        settings.SERPAPI_MAX_RESULTS,
    )
    return _unir_paginas(respuesta_inicial, propiedades, parametros_base)


def buscar_hospedajes(
        ciudad: str,
        pais: str,
        precio_maximo_noche: float | None = None,
) -> list[Hospedaje]:
    try:
        respuesta = consultar_serpapi(ciudad, pais, precio_maximo_noche)
    except SerpApiError as error:
        logger.error("La búsqueda de hospedajes falló: tipo=%s", type(error).__name__)
        return []

    if not respuesta or "properties" not in respuesta:
        return []

    try:
        id_destino = DestinoRepository().obtener_o_crear(Destino(ciudad=ciudad, pais=pais))
    except Exception as error:
        logger.error("No se pudo obtener o crear el destino: tipo=%s", type(error).__name__)
        return []

    return mapear_hospedajes(respuesta, id_destino, precio_maximo_noche, ciudad, pais)


def mapear_hospedajes(
        respuesta: dict,
        id_destino: int,
        precio_maximo_noche: float | None,
        ciudad: str,
        pais: str,
) -> list[Hospedaje]:
    parametros = respuesta.get("search_parameters", {})
    fecha_entrada = parametros.get("check_in_date")
    fecha_salida = parametros.get("check_out_date")
    consulta = _consulta_hoteles(ciudad, pais)

    hospedajes = []
    for propiedad in respuesta["properties"]:
        tarifa_noche = propiedad.get("rate_per_night", {})
        precio_noche = tarifa_noche.get("extracted_lowest")

        if precio_maximo_noche is not None and (
                precio_noche is None or precio_noche > precio_maximo_noche
        ):
            continue

        token_propiedad = propiedad.get("property_token")
        if token_propiedad and fecha_entrada and fecha_salida:
            url_reserva = construir_url_reserva(
                token_propiedad, fecha_entrada, fecha_salida, consulta
            )
        else:
            url_reserva = propiedad.get("link", "")

        hospedajes.append(Hospedaje(
            destino_id=id_destino,
            nombre=propiedad.get("name", "Sin nombre"),
            tipo="hotel",
            precio_noche=precio_noche,
            calificacion=propiedad.get("overall_rating", 0.0),
            direccion=propiedad.get("description", "Sin dirección disponible"),
            url_reserva=url_reserva,
        ))

    return hospedajes

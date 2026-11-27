import logging
import math
import threading
import time
from urllib.parse import quote

import requests

from src.config import settings
from src.exceptions import SerpApiError
from src.models.busqueda import EspecificacionBusqueda
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
        f"&q={quote(consulta, safe='')}&hl=es&gl=us"
    )


def _normalizar_url(url: str | None) -> str:
    """SerpAPI puede devolver ``link`` sin esquema (ej. ``hotel.com``)."""
    if not url:
        return ""
    url = url.strip()
    if url.startswith(("http://", "https://")):
        return url
    if url.startswith("//"):
        return f"https:{url}"
    return f"https://{url}"


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


def _segundos_retry_after(respuesta: requests.Response | None) -> float | None:
    if respuesta is None:
        return None
    encabezado = respuesta.headers.get("Retry-After")
    if encabezado is None:
        return None
    try:
        return max(0.0, float(encabezado))
    except (TypeError, ValueError):
        return None


def _es_reintentable(status_code: int | None) -> bool:
    return status_code == 429 or (
        status_code is not None and 500 <= status_code < 600
    )


def _parametros_de_busqueda(espec: EspecificacionBusqueda) -> dict[str, str | int]:
    if espec.fecha_entrada is None or espec.fecha_salida is None:
        raise ValueError("La búsqueda requiere fecha de entrada y salida.")

    parametros: dict[str, str | int] = {
        "engine": "google_hotels",
        "q": _consulta_hoteles(espec.ciudad, espec.pais),
        "check_in_date": espec.fecha_entrada.isoformat(),
        "check_out_date": espec.fecha_salida.isoformat(),
        "adults": espec.adultos if espec.adultos is not None else 2,
        "children": espec.ninos if espec.ninos is not None else 0,
        "currency": "USD",
        "hl": "es",
        "api_key": settings.SERPAPI_KEY,
    }

    if espec.mascotas:
        # 19 = "Pet-friendly" en el catálogo de amenities de Google Hotels.
        parametros["amenities"] = "19"

    if espec.presupuesto_max_noche is not None and math.isfinite(espec.presupuesto_max_noche):
        # La API espera un entero; ceil evita perder hoteles que sí caben
        # en el presupuesto y el filtro local hace el corte exacto.
        parametros["max_price"] = math.ceil(espec.presupuesto_max_noche)

    return parametros


def _pedir_pagina(parametros: dict[str, str | int]) -> dict:
    """Solicita una página y reintenta solo fallos transitorios.

    Los 4xx distintos de 429 no se reintentan. Si se agotan los reintentos,
    se propaga ``SerpApiError`` para que el llamador decida si conserva
    resultados parciales.
    """
    ultimo_error: Exception | None = None

    for intento in range(settings.SERPAPI_MAX_REINTENTOS + 1):
        _esperar_turno()
        try:
            respuesta = requests.get(
                URL_SERPAPI,
                params=parametros,
                timeout=settings.SERPAPI_TIMEOUT,
            )
            respuesta.raise_for_status()
            datos = respuesta.json()
            if "error" in datos:
                raise SerpApiError(
                    "consulta",
                    f"Error reportado por la API: {datos['error']}",
                )
            return datos
        except requests.exceptions.HTTPError as error:
            respuesta_fallida = error.response
            status_code = (
                respuesta_fallida.status_code
                if respuesta_fallida is not None
                else None
            )
            if not _es_reintentable(status_code):
                logger.error("SerpAPI respondió HTTP %s", status_code)
                raise SerpApiError("consulta", f"HTTP {status_code}") from error

            ultimo_error = error
            if intento >= settings.SERPAPI_MAX_REINTENTOS:
                break

            espera = max(
                settings.SERPAPI_BACKOFF_BASE * (2 ** intento),
                _segundos_retry_after(respuesta_fallida) or 0.0,
            )
            logger.warning(
                "SerpAPI respondió HTTP %s; reintento %s de %s en %.2f segundos",
                status_code,
                intento + 1,
                settings.SERPAPI_MAX_REINTENTOS,
                espera,
            )
            if espera > 0:
                time.sleep(espera)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as error:
            ultimo_error = error
            if intento >= settings.SERPAPI_MAX_REINTENTOS:
                break

            espera = settings.SERPAPI_BACKOFF_BASE * (2 ** intento)
            logger.warning(
                "Error de red con SerpAPI (%s); reintento %s de %s en %.2f segundos",
                type(error).__name__,
                intento + 1,
                settings.SERPAPI_MAX_REINTENTOS,
                espera,
            )
            if espera > 0:
                time.sleep(espera)
        except requests.exceptions.RequestException as error:
            logger.error("Error al consultar SerpAPI: tipo=%s", type(error).__name__)
            raise SerpApiError("consulta", type(error).__name__) from error

    logger.error(
        "SerpAPI agotó los reintentos: %s",
        type(ultimo_error).__name__ if ultimo_error is not None else "sin detalle",
    )
    raise SerpApiError("consulta", "Se agotaron los reintentos") from ultimo_error


def _recolectar_propiedades(
        parametros_base: dict[str, str | int],
        max_paginas: int,
        max_resultados: int,
) -> tuple[dict, list[dict]]:
    """Lee páginas hasta el tope de páginas o de resultados.

    La configuración debe pedir al menos una página y un resultado: el bucle
    corre una sola vez como mínimo, así que siempre hay una respuesta inicial.
    """
    if max_paginas < 1 or max_resultados < 1:
        raise ValueError("SerpAPI debe pedir al menos una página y un resultado.")

    propiedades: list[dict] = []
    respuesta_inicial: dict | None = None
    token_siguiente_pagina: str | None = None
    paginas_leidas = 0

    while paginas_leidas < max_paginas and len(propiedades) < max_resultados:
        parametros_pagina = dict(parametros_base)
        if token_siguiente_pagina is not None:
            parametros_pagina["next_page_token"] = token_siguiente_pagina

        try:
            respuesta_pagina = _pedir_pagina(parametros_pagina)
        except SerpApiError as error:
            if propiedades:
                logger.warning(
                    "Se conservan %s propiedades ya obtenidas: %s",
                    len(propiedades),
                    error,
                )
                break
            raise

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

    return respuesta_inicial or {}, propiedades


def _unir_paginas(respuesta_inicial: dict, propiedades: list[dict]) -> dict:
    """Consolida la primera respuesta con las propiedades de todas las páginas."""
    respuesta_unida = {
        clave: valor
        for clave, valor in respuesta_inicial.items()
        if clave not in ("properties", "serpapi_pagination")
    }
    respuesta_unida["properties"] = propiedades
    return respuesta_unida


def consultar_serpapi(espec: EspecificacionBusqueda) -> dict:
    if not settings.SERPAPI_KEY:
        logger.error("Falta la credencial requerida del proveedor")
        raise SerpApiError("configuracion", "Falta la credencial del proveedor")

    parametros_base = _parametros_de_busqueda(espec)
    respuesta_inicial, propiedades = _recolectar_propiedades(
        parametros_base,
        settings.SERPAPI_MAX_PAGES,
        settings.SERPAPI_MAX_RESULTS,
    )
    return _unir_paginas(respuesta_inicial, propiedades)


def buscar_hospedajes(espec: EspecificacionBusqueda) -> list[Hospedaje]:
    """Busca hoteles y resuelve su destino.

    Los fallos de SerpAPI o de PostgreSQL se propagan: el CLI debe poder
    distinguir entre “no hay resultados” y “no se pudo buscar”.
    """
    respuesta = consultar_serpapi(espec)
    if not respuesta.get("properties"):
        return []

    id_destino = DestinoRepository().obtener_o_crear(
        Destino(ciudad=espec.ciudad, pais=espec.pais)
    )
    return mapear_hospedajes(respuesta, id_destino, espec)


def _numero(valor) -> float | None:
    if valor is None:
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if math.isfinite(numero) else None


def _tipo_hospedaje(propiedad: dict) -> str:
    tipo = (propiedad.get("type") or "").strip().lower()
    if tipo in ("", "hotel"):
        return "hotel"
    return "otro"


def mapear_hospedajes(
        respuesta: dict,
        id_destino: int,
        espec: EspecificacionBusqueda,
) -> list[Hospedaje]:
    # Las fechas salen de la especificación: la URL de reserva debe coincidir
    # con la búsqueda aunque la respuesta no repita los parámetros.
    fecha_entrada = espec.fecha_entrada.isoformat() if espec.fecha_entrada else None
    fecha_salida = espec.fecha_salida.isoformat() if espec.fecha_salida else None
    consulta = _consulta_hoteles(espec.ciudad, espec.pais)

    hospedajes = []
    for propiedad in respuesta.get("properties", []):
        tarifa_noche = propiedad.get("rate_per_night") or {}
        precio_noche = _numero(tarifa_noche.get("extracted_lowest"))

        if espec.presupuesto_max_noche is not None and (
                precio_noche is None or precio_noche > espec.presupuesto_max_noche
        ):
            continue

        token_propiedad = propiedad.get("property_token")
        if token_propiedad and fecha_entrada and fecha_salida:
            url_reserva = construir_url_reserva(
                token_propiedad, fecha_entrada, fecha_salida, consulta
            )
        else:
            url_reserva = _normalizar_url(propiedad.get("link"))

        nombre = str(propiedad.get("name") or "Sin nombre")[:200]
        descripcion = str(
            propiedad.get("description") or "Sin descripción disponible"
        )[:4000]
        direccion = str(propiedad.get("address") or "").strip() or None
        gps = propiedad.get("gps_coordinates") or {}
        latitud = _numero(gps.get("latitude"))
        longitud = _numero(gps.get("longitude"))

        hospedajes.append(Hospedaje(
            destino_id=id_destino,
            nombre=nombre,
            tipo=_tipo_hospedaje(propiedad),
            precio_noche=precio_noche,
            calificacion=_numero(propiedad.get("overall_rating")),
            descripcion=descripcion,
            direccion=direccion,
            url_reserva=url_reserva,
            google_place_id=token_propiedad or None,
            latitud=latitud,
            longitud=longitud,
        ))

    return hospedajes

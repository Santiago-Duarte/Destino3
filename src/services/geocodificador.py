"""Geocodificación del centro de un destino con Nominatim (OpenStreetMap).

Nominatim es gratuito y no requiere clave, pero su política de uso exige un
``User-Agent`` identificable y como máximo una petición por segundo. Las
coordenadas se cachean solo cuando la consulta tiene éxito: un fallo de red no
debe envenenar la caché y bloquear búsquedas posteriores.
"""

import logging
import threading
import time

import requests

from src.config import settings

logger = logging.getLogger(__name__)

_candado_rate_limit = threading.Lock()
_ultima_llamada = 0.0
_cache: dict[tuple[str, str], tuple[float, float]] = {}
_cache_puntos: dict[tuple[str, str, str], tuple[float, float]] = {}


def _clave(ciudad: str, pais: str) -> tuple[str, str]:
    return (ciudad.strip().lower(), pais.strip().lower())


def _clave_punto(punto: str, ciudad: str, pais: str) -> tuple[str, str, str]:
    return (punto.strip().lower(), ciudad.strip().lower(), pais.strip().lower())


def limpiar_cache() -> None:
    """Vacía la caché de geocodificación (útil en pruebas y diagnósticos)."""
    global _ultima_llamada
    _cache.clear()
    _cache_puntos.clear()
    _ultima_llamada = 0.0


def _esperar_turno() -> None:
    global _ultima_llamada

    peticiones_por_segundo = settings.NOMINATIM_RATE_LIMIT_RPS
    if peticiones_por_segundo <= 0:
        return

    intervalo = 1.0 / peticiones_por_segundo
    with _candado_rate_limit:
        ahora = time.monotonic()
        espera = intervalo - (ahora - _ultima_llamada)
        if espera > 0:
            time.sleep(espera)
        _ultima_llamada = time.monotonic()


def _coordenadas_validas(latitud: float, longitud: float) -> bool:
    return -90.0 <= latitud <= 90.0 and -180.0 <= longitud <= 180.0


def geocodificar(ciudad: str, pais: str) -> tuple[float, float] | None:
    """Devuelve ``(latitud, longitud)`` del centro de ``ciudad, pais``.

    Devuelve ``None`` si la consulta no tiene resultados, la respuesta es
    inválida o la red falla. Un fallo de geocodificación no debe interrumpir la
    búsqueda de hoteles: las distancias simplemente quedan sin calcular.
    """
    ciudad = (ciudad or "").strip()
    pais = (pais or "").strip()
    if not ciudad or not pais:
        return None

    clave = _clave(ciudad, pais)
    if clave in _cache:
        return _cache[clave]

    _esperar_turno()
    parametros: dict[str, str | int] = {
        "q": f"{ciudad}, {pais}",
        "format": "jsonv2",
        "limit": 1,
        "addressdetails": 0,
        "accept-language": "es",
    }
    try:
        respuesta = requests.get(
            settings.NOMINATIM_URL,
            params=parametros,
            headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
            timeout=settings.NOMINATIM_TIMEOUT,
        )
        respuesta.raise_for_status()
        datos = respuesta.json()
    except (requests.RequestException, ValueError) as error:
        logger.warning(
            "No se pudo geocodificar %s, %s: %s",
            ciudad,
            pais,
            type(error).__name__,
        )
        return None

    if not isinstance(datos, list) or not datos:
        logger.warning("Nominatim no encontró coordenadas para %s, %s", ciudad, pais)
        return None

    primer_resultado = datos[0]
    if not isinstance(primer_resultado, dict):
        return None

    try:
        latitud = float(primer_resultado["lat"])
        longitud = float(primer_resultado["lon"])
    except (KeyError, TypeError, ValueError):
        logger.warning("Nominatim devolvió coordenadas inválidas para %s, %s", ciudad, pais)
        return None

    if not _coordenadas_validas(latitud, longitud):
        logger.warning("Nominatim devolvió coordenadas fuera de rango para %s, %s", ciudad, pais)
        return None

    _cache[clave] = (latitud, longitud)
    return _cache[clave]


def geocodificar_punto(
        punto: str,
        ciudad: str,
        pais: str,
) -> tuple[float, float] | None:
    """Devuelve ``(latitud, longitud)`` de ``punto, ciudad, pais``.

    Ejemplos de ``punto``: "estación metro Poblado", "aeropuerto JMC",
    "playa El Rodadero", "centro comercial Santafé".

    Devuelve ``None`` si la consulta no tiene resultados, la respuesta es
    inválida o la red falla. Un fallo no debe interrumpir la búsqueda.
    """
    punto = (punto or "").strip()
    ciudad = (ciudad or "").strip()
    pais = (pais or "").strip()
    if not punto or not ciudad or not pais:
        return None

    clave = _clave_punto(punto, ciudad, pais)
    if clave in _cache_puntos:
        return _cache_puntos[clave]

    _esperar_turno()
    parametros: dict[str, str | int] = {
        "q": f"{punto}, {ciudad}, {pais}",
        "format": "jsonv2",
        "limit": 1,
        "addressdetails": 0,
        "accept-language": "es",
    }
    try:
        respuesta = requests.get(
            settings.NOMINATIM_URL,
            params=parametros,
            headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
            timeout=settings.NOMINATIM_TIMEOUT,
        )
        respuesta.raise_for_status()
        datos = respuesta.json()
    except (requests.RequestException, ValueError) as error:
        logger.warning(
            "No se pudo geocodificar punto %s en %s, %s: %s",
            punto,
            ciudad,
            pais,
            type(error).__name__,
        )
        return None

    if not isinstance(datos, list) or not datos:
        logger.warning("Nominatim no encontró coordenadas para punto %s en %s, %s", punto, ciudad, pais)
        return None

    primer_resultado = datos[0]
    if not isinstance(primer_resultado, dict):
        return None

    try:
        latitud = float(primer_resultado["lat"])
        longitud = float(primer_resultado["lon"])
    except (KeyError, TypeError, ValueError):
        logger.warning("Nominatim devolvió coordenadas inválidas para punto %s en %s, %s", punto, ciudad, pais)
        return None

    if not _coordenadas_validas(latitud, longitud):
        logger.warning("Nominatim devolvió coordenadas fuera de rango para punto %s en %s, %s", punto, ciudad, pais)
        return None

    _cache_puntos[clave] = (latitud, longitud)
    return _cache_puntos[clave]

"""Cálculo de distancias y estimación de tiempos de viaje.

La distancia es la línea recta (haversine) entre el centro del destino y el
hotel. Los tiempos son estimaciones por velocidad media urbana, no rutas
reales: sirven para comparar y ordenar, no para prometer un trayecto exacto.
"""

from math import atan2, cos, radians, sin, sqrt

RADIO_TIERRA_KM = 6371.0

VELOCIDAD_AUTO_KMH = 30.0
VELOCIDAD_TRANSIT_KMH = 20.0
VELOCIDAD_CAMINANDO_KMH = 5.0


def distancia_haversine(
        origen: tuple[float, float],
        destino: tuple[float, float],
) -> float:
    """Distancia en línea recta, en kilómetros, entre dos puntos (lat, lon)."""
    lat1, lon1 = (radians(valor) for valor in origen)
    lat2, lon2 = (radians(valor) for valor in destino)

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    )
    return RADIO_TIERRA_KM * 2 * atan2(sqrt(a), sqrt(1 - a))


def _minutos(distancia_km: float, velocidad_kmh: float) -> int:
    if distancia_km <= 0:
        return 0
    return max(1, round(distancia_km / velocidad_kmh * 60))


def estimar_tiempo_minutos(distancia_km: float, modo: str = "auto") -> int:
    """Minutos estimados para recorrer ``distancia_km`` en el modo indicado.

    Modos admitidos: ``auto`` (30 km/h), ``transit`` (20 km/h) y ``walking``
    (5 km/h). Cualquier otro valor usa ``auto``.
    """
    velocidades = {
        "auto": VELOCIDAD_AUTO_KMH,
        "transit": VELOCIDAD_TRANSIT_KMH,
        "walking": VELOCIDAD_CAMINANDO_KMH,
    }
    return _minutos(distancia_km, velocidades.get(modo, VELOCIDAD_AUTO_KMH))


def aplicar_distancias(
        hospedajes: list,
        origen: tuple[float, float],
) -> None:
    """Completa ``distancia_km`` y los tiempos de cada hospedaje con coordenadas.

    Los hospedajes sin coordenadas se dejan intactos (sus campos quedan en
    ``None``). La función muta los objetos en lugar de crear copias para no
    romper las referencias que ya usa el orquestador.
    """
    for hospedaje in hospedajes:
        coordenadas = hospedaje.coordenadas()
        if coordenadas is None:
            continue

        distancia = distancia_haversine(origen, coordenadas)
        hospedaje.distancia_km = round(distancia, 2)
        hospedaje.tiempo_auto_min = estimar_tiempo_minutos(distancia, "auto")
        hospedaje.tiempo_transit_min = estimar_tiempo_minutos(distancia, "transit")
        hospedaje.tiempo_walking_min = estimar_tiempo_minutos(distancia, "walking")

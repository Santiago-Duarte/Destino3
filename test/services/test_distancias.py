import unittest

from src.models.hospedaje import Hospedaje
from src.services.distancias import (
    aplicar_distancias,
    distancia_haversine,
    estimar_tiempo_minutos,
)

MEDELLIN = (6.2442, -75.5812)
BOGOTA = (4.7110, -74.0721)


def crear_hospedaje(latitud=None, longitud=None) -> Hospedaje:
    return Hospedaje(
        nombre="Hotel",
        tipo="hotel",
        precio_noche=100,
        calificacion=4.5,
        direccion="Calle 1",
        url_reserva="https://hotel.example",
        destino_id=1,
        latitud=latitud,
        longitud=longitud,
    )


class TestDistanciaHaversine(unittest.TestCase):

    def test_mismo_punto_es_cero(self):
        self.assertEqual(distancia_haversine(MEDELLIN, MEDELLIN), 0.0)

    def test_distancia_conocida_entre_ciudades(self):
        # Medellín-Bogotá en línea recta ronda los 240 km.
        self.assertAlmostEqual(
            distancia_haversine(MEDELLIN, BOGOTA),
            240,
            delta=10,
        )

    def test_es_simetrica(self):
        self.assertAlmostEqual(
            distancia_haversine(MEDELLIN, BOGOTA),
            distancia_haversine(BOGOTA, MEDELLIN),
        )


class TestEstimarTiempo(unittest.TestCase):

    def test_auto_usa_treinta_kmh(self):
        self.assertEqual(estimar_tiempo_minutos(30, "auto"), 60)

    def test_transit_usa_veinte_kmh(self):
        self.assertEqual(estimar_tiempo_minutos(20, "transit"), 60)

    def test_walking_usa_cinco_kmh(self):
        self.assertEqual(estimar_tiempo_minutos(5, "walking"), 60)

    def test_modo_desconocido_usa_auto(self):
        self.assertEqual(
            estimar_tiempo_minutos(30, "desconocido"),
            estimar_tiempo_minutos(30, "auto"),
        )

    def test_distancia_cero_da_cero_minutos(self):
        self.assertEqual(estimar_tiempo_minutos(0), 0)

    def test_distancias_muy_cortas_dan_al_menos_un_minuto(self):
        self.assertEqual(estimar_tiempo_minutos(0.01), 1)


class TestAplicarDistancias(unittest.TestCase):

    def test_completa_distancia_y_tiempos(self):
        cerca = crear_hospedaje(*MEDELLIN)
        lejos = crear_hospedaje(*BOGOTA)

        aplicar_distancias([cerca, lejos], MEDELLIN)

        self.assertEqual(cerca.distancia_km, 0.0)
        self.assertEqual(cerca.tiempo_auto_min, 0)
        self.assertEqual(cerca.tiempo_transit_min, 0)
        self.assertEqual(cerca.tiempo_walking_min, 0)

        self.assertAlmostEqual(lejos.distancia_km, 240, delta=10)
        self.assertGreater(lejos.tiempo_walking_min, lejos.tiempo_transit_min)
        self.assertGreater(lejos.tiempo_transit_min, lejos.tiempo_auto_min)

    def test_hospedaje_sin_coordenadas_queda_intacto(self):
        sin_gps = crear_hospedaje()

        aplicar_distancias([sin_gps], MEDELLIN)

        self.assertIsNone(sin_gps.distancia_km)
        self.assertIsNone(sin_gps.tiempo_auto_min)
        self.assertIsNone(sin_gps.tiempo_transit_min)
        self.assertIsNone(sin_gps.tiempo_walking_min)

    def test_lista_vacia_no_falla(self):
        aplicar_distancias([], MEDELLIN)

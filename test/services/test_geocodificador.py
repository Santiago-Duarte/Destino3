import unittest
from unittest.mock import Mock, patch

from src.services import geocodificador


class TestGeocodificar(unittest.TestCase):

    def setUp(self):
        geocodificador.limpiar_cache()

    def tearDown(self):
        geocodificador.limpiar_cache()

    @staticmethod
    def _respuesta(datos, status=200):
        respuesta = Mock()
        respuesta.json.return_value = datos
        respuesta.raise_for_status.return_value = None
        respuesta.status_code = status
        return respuesta

    @patch("src.services.geocodificador.requests.get")
    def test_devuelve_coordenadas_del_primer_resultado(self, get_mock):
        get_mock.return_value = self._respuesta([
            {"lat": "6.2442", "lon": "-75.5812"},
        ])

        coordenadas = geocodificador.geocodificar("Medellin", "Colombia")

        self.assertEqual(coordenadas, (6.2442, -75.5812))
        get_mock.assert_called_once()
        argumentos = get_mock.call_args.kwargs
        self.assertEqual(argumentos["params"]["q"], "Medellin, Colombia")
        self.assertIn("User-Agent", argumentos["headers"])

    @patch("src.services.geocodificador.requests.get")
    def test_usa_la_cache_en_consultas_repetidas(self, get_mock):
        get_mock.return_value = self._respuesta([{"lat": "6.2442", "lon": "-75.5812"}])

        primera = geocodificador.geocodificar("Medellin", "Colombia")
        segunda = geocodificador.geocodificar("  medellin ", " COLOMBIA ")

        self.assertEqual(primera, segunda)
        get_mock.assert_called_once()

    @patch("src.services.geocodificador.requests.get")
    def test_sin_resultados_devuelve_none(self, get_mock):
        get_mock.return_value = self._respuesta([])

        self.assertIsNone(geocodificador.geocodificar("Nada", "Ninguno"))

    @patch("src.services.geocodificador.requests.get")
    def test_respuesta_no_lista_devuelve_none(self, get_mock):
        get_mock.return_value = self._respuesta({"error": "raro"})

        self.assertIsNone(geocodificador.geocodificar("Medellin", "Colombia"))

    @patch("src.services.geocodificador.requests.get")
    def test_coordenadas_invalidas_devuelven_none(self, get_mock):
        get_mock.return_value = self._respuesta([{"lat": "N/A", "lon": None}])

        self.assertIsNone(geocodificador.geocodificar("Medellin", "Colombia"))

    @patch("src.services.geocodificador.requests.get")
    def test_coordenadas_fuera_de_rango_devuelven_none(self, get_mock):
        get_mock.return_value = self._respuesta([{"lat": "999", "lon": "-75.5"}])

        self.assertIsNone(geocodificador.geocodificar("Medellin", "Colombia"))

    @patch("src.services.geocodificador.requests.get")
    def test_error_de_red_devuelve_none_y_no_llena_la_cache(self, get_mock):
        get_mock.side_effect = geocodificador.requests.RequestException("sin red")

        self.assertIsNone(geocodificador.geocodificar("Medellin", "Colombia"))

        get_mock.side_effect = None
        get_mock.return_value = self._respuesta([{"lat": "6.2442", "lon": "-75.5812"}])
        self.assertEqual(
            geocodificador.geocodificar("Medellin", "Colombia"),
            (6.2442, -75.5812),
        )
        self.assertEqual(get_mock.call_count, 2)

    @patch("src.services.geocodificador.requests.get")
    def test_ciudad_o_pais_vacio_no_consulta_la_api(self, get_mock):
        self.assertIsNone(geocodificador.geocodificar("", "Colombia"))
        self.assertIsNone(geocodificador.geocodificar("Medellin", "   "))
        get_mock.assert_not_called()

    @patch("src.services.geocodificador.requests.get")
    def test_json_invalido_devuelve_none(self, get_mock):
        respuesta = Mock()
        respuesta.raise_for_status.return_value = None
        respuesta.json.side_effect = ValueError("no es json")
        get_mock.return_value = respuesta

        self.assertIsNone(geocodificador.geocodificar("Medellin", "Colombia"))

    @patch("src.services.geocodificador.time.sleep")
    @patch("src.services.geocodificador.time.monotonic")
    @patch("src.services.geocodificador.requests.get")
    def test_respeta_el_rate_limit_entre_llamadas(self, get_mock, monotonic_mock, sleep_mock):
        monotonic_mock.side_effect = [100.0, 100.0, 100.5, 101.0]
        get_mock.return_value = self._respuesta([{"lat": "6.2442", "lon": "-75.5812"}])

        geocodificador.geocodificar("Medellin", "Colombia")
        geocodificador.geocodificar("Cali", "Colombia")

        sleep_mock.assert_called_once()
        self.assertAlmostEqual(sleep_mock.call_args.args[0], 0.5)

import os
os.environ['ENVIRONMENT'] = 'testing'

import tempfile
import unittest
from unittest.mock import patch

from src.services.api_searcher import (
    buscar_hospedajes,
    buscar_hospedajes_raw,
    construir_link_google_hotels,
)


def respuesta_mock():
    return {
        "search_parameters": {
            "engine": "google_hotels",
            "q": "hoteles en Medellin Colombia",
            "check_in_date": "2026-08-14",
            "check_out_date": "2026-08-16",
        },
        "properties": [
            {
                "name": "Hotel A",
                "property_token": "ChoTOKENA",
                "rate_per_night": {"lowest": "$64", "extracted_lowest": 64},
                "overall_rating": 4.5,
                "description": "Centro",
                "link": "https://hotela.com",
            },
            {
                "name": "Hotel B",
                "rate_per_night": {"lowest": "$83", "extracted_lowest": 83},
                "overall_rating": 4.0,
                "description": "Bocagrande",
                "link": "https://hotelb.com",
            },
        ],
    }


class TestConstruirLinkGoogleHotels(unittest.TestCase):

    def test_genera_url_de_entidad_con_fechas_y_query_codificado(self):
        url = construir_link_google_hotels(
            "ChoTOKENA", "2026-08-14", "2026-08-16", "hoteles en Medellin Colombia"
        )

        self.assertTrue(url.startswith("https://www.google.com/travel/hotels/entity/ChoTOKENA"))
        self.assertIn("check_in=2026-08-14", url)
        self.assertIn("check_out=2026-08-16", url)
        self.assertIn("q=hoteles%20en%20Medellin%20Colombia", url)
        self.assertIn("hl=es", url)


class TestBuscarHospedajes(unittest.TestCase):

    def setUp(self):
        self.archivo_temporal = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.archivo_temporal.close()
        patcher_ruta = patch("src.services.api_searcher.RUTA_RESPUESTA_PRUEBA",
                             self.archivo_temporal.name)
        patcher_ruta.start()
        self.addCleanup(patcher_ruta.stop)
        self.addCleanup(os.unlink, self.archivo_temporal.name)

    @patch("src.services.api_searcher.buscar_hospedajes_raw")
    def test_usar_link_de_entidad_con_fechas_de_search_parameters(self, raw_mock):
        raw_mock.return_value = respuesta_mock()

        hospedajes = buscar_hospedajes("Medellin", "Colombia")

        self.assertEqual(len(hospedajes), 2)
        self.assertTrue(hospedajes[0].url_reserva.startswith(
            "https://www.google.com/travel/hotels/entity/ChoTOKENA"))
        self.assertIn("check_in=2026-08-14", hospedajes[0].url_reserva)
        self.assertIn("check_out=2026-08-16", hospedajes[0].url_reserva)

    @patch("src.services.api_searcher.buscar_hospedajes_raw")
    def test_fallback_al_sitio_del_hotel_sin_property_token(self, raw_mock):
        raw_mock.return_value = respuesta_mock()

        hospedajes = buscar_hospedajes("Medellin", "Colombia")

        self.assertEqual(hospedajes[1].url_reserva, "https://hotelb.com")

    @patch("src.services.api_searcher.buscar_hospedajes_raw")
    def test_filtra_por_presupuesto(self, raw_mock):
        raw_mock.return_value = respuesta_mock()

        hospedajes = buscar_hospedajes("Medellin", "Colombia", presupuesto_maximo=70)

        self.assertEqual(len(hospedajes), 1)
        self.assertEqual(hospedajes[0].nombre, "Hotel A")

    @patch("src.services.api_searcher.buscar_hospedajes_raw")
    def test_sin_properties_devuelve_lista_vacia(self, raw_mock):
        raw_mock.return_value = {"search_parameters": {}}

        self.assertEqual(buscar_hospedajes("Medellin", "Colombia"), [])


class TestBuscarHospedajesRaw(unittest.TestCase):

    @patch("src.services.api_searcher.requests.get")
    def test_error_de_red_devuelve_none(self, get_mock):
        from requests.exceptions import ConnectionError

        get_mock.side_effect = ConnectionError("sin red")

        self.assertIsNone(buscar_hospedajes_raw("Medellin", "Colombia"))

    @patch("src.services.api_searcher.requests.get")
    def test_error_de_api_en_json_devuelve_none(self, get_mock):
        respuesta = unittest.mock.Mock()
        respuesta.raise_for_status.return_value = None
        respuesta.json.return_value = {"error": "Invalid hl value"}
        get_mock.return_value = respuesta

        self.assertIsNone(buscar_hospedajes_raw("Medellin", "Colombia"))

    @patch("src.services.api_searcher.requests.get")
    def test_respuesta_ok_pasa_presupuesto_como_max_price(self, get_mock):
        respuesta = unittest.mock.Mock()
        respuesta.raise_for_status.return_value = None
        respuesta.json.return_value = {"properties": []}
        get_mock.return_value = respuesta

        resultado = buscar_hospedajes_raw("Medellin", "Colombia", presupuesto_maximo=80)

        self.assertEqual(resultado, {"properties": []})
        llamada_params = get_mock.call_args.kwargs["params"]
        self.assertEqual(llamada_params["max_price"], 80)
        self.assertIn("check_in_date", llamada_params)
        self.assertIn("check_out_date", llamada_params)


if __name__ == '__main__':
    unittest.main()

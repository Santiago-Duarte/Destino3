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

from test.db_test_case import BaseDBTestCase

from src.services.db_service import (
    obtener_hospedajes_por_destino,
    guardar_hospedaje,
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

        patcher_destino = patch("src.services.api_searcher.obtener_o_crear_destino",
                                return_value=42)
        patcher_destino.start()
        self.addCleanup(patcher_destino.stop)

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
        from src.services import api_searcher

        resultado = buscar_hospedajes("Medellin", "Colombia")

        self.assertEqual(resultado, [])
        # Early return api_searcher.py:65 -> sin "properties" no debe resolver destino
        api_searcher.obtener_o_crear_destino.assert_not_called()
        # Tampoco debe escribir archivo ni mapear hospedajes
        raw_mock.assert_called_once_with("Medellin", "Colombia", None)

    @patch("src.services.api_searcher.buscar_hospedajes_raw")
    def test_todos_los_hospedajes_llevan_el_destino_resuelto(self, raw_mock):
        raw_mock.return_value = respuesta_mock()

        hospedajes = buscar_hospedajes("Medellin", "Colombia")

        self.assertEqual(len(hospedajes), 2)
        for hospedaje in hospedajes:
            self.assertEqual(hospedaje.destino_id, 42)

    @patch("src.services.api_searcher.buscar_hospedajes_raw")
    def test_destino_se_resuelve_una_sola_vez_con_el_destino_correcto(self, raw_mock):
        raw_mock.return_value = respuesta_mock()

        buscar_hospedajes("Medellin", "Colombia")

        from src.services import api_searcher
        api_searcher.obtener_o_crear_destino.assert_called_once()
        destino = api_searcher.obtener_o_crear_destino.call_args.args[0]
        self.assertEqual(destino.ciudad, "Medellin")
        self.assertEqual(destino.pais, "Colombia")

    @patch("src.services.api_searcher.buscar_hospedajes_raw")
    def test_sin_destino_valido_devuelve_lista_vacia(self, raw_mock):
        raw_mock.return_value = respuesta_mock()
        from src.services import api_searcher
        api_searcher.obtener_o_crear_destino.return_value = None

        hospedajes = buscar_hospedajes("Medellin", "Colombia")

        self.assertEqual(hospedajes, [])

    @patch("src.services.api_searcher.buscar_hospedajes_raw")
    def test_archivo_guardado_incluye_ciudad_y_pais(self, raw_mock):
        import json

        raw_mock.return_value = respuesta_mock()

        buscar_hospedajes("Medellin", "Colombia")

        with open(self.archivo_temporal.name, "r", encoding="utf-8") as f:
            datos = json.load(f)

        self.assertEqual(datos["city"], "Medellin")
        self.assertEqual(datos["country"], "Colombia")


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


class TestIntegracionBuscarYGuardar(BaseDBTestCase):

    def setUp(self):
        super().setUp()  # BaseDBTestCase: DELETE FROM hospedajes; DELETE FROM destinos;
        self.archivo_temporal = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.archivo_temporal.close()
        patcher_ruta = patch("src.services.api_searcher.RUTA_RESPUESTA_PRUEBA",
                             self.archivo_temporal.name)
        patcher_ruta.start()
        self.addCleanup(patcher_ruta.stop)
        self.addCleanup(os.unlink, self.archivo_temporal.name)

    @patch("src.services.api_searcher.buscar_hospedajes_raw")
    def test_integracion_buscar_y_guardar_persiste(self, mock_raw):
        mock_raw.return_value = respuesta_mock()  # 2 hoteles
        hospedajes = buscar_hospedajes("Medellin", "Colombia")  # genera destino_id real via obtener_o_crear_destino
        self.assertEqual(len(hospedajes), 2)
        ids = [guardar_hospedaje(h) for h in hospedajes]
        self.assertTrue(all(isinstance(i, int) for i in ids))
        persistidos = obtener_hospedajes_por_destino(hospedajes[0].destino_id)
        self.assertEqual(len(persistidos), 2)
        self.assertEqual({p.nombre for p in persistidos}, {"Hotel A", "Hotel B"})


if __name__ == '__main__':
    unittest.main()
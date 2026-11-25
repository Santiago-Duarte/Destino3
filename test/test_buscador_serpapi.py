import threading
import time
import unittest
from unittest.mock import patch

import requests

from src.config import settings
from src.exceptions import SerpApiError
from src.repositories.hospedaje_repository import HospedajeRepository
from src.services.buscador_serpapi import (
    buscar_hospedajes,
    construir_url_reserva,
    consultar_serpapi,
)
from test.db_test_case import BaseDBTestCase


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


class TestConstruirUrlReserva(unittest.TestCase):

    def test_genera_url_de_entidad_con_fechas_y_query_codificado(self):
        url = construir_url_reserva(
            "ChoTOKENA", "2026-08-14", "2026-08-16", "hoteles en Medellin Colombia"
        )

        self.assertTrue(url.startswith("https://www.google.com/travel/hotels/entity/ChoTOKENA"))
        self.assertIn("check_in=2026-08-14", url)
        self.assertIn("check_out=2026-08-16", url)
        self.assertIn("q=hoteles%20en%20Medellin%20Colombia", url)
        self.assertIn("hl=es", url)


class TestBuscarHospedajes(unittest.TestCase):

    def setUp(self):
        patcher_destino = patch("src.services.buscador_serpapi.DestinoRepository.obtener_o_crear",
                                return_value=42)
        patcher_destino.start()
        self.addCleanup(patcher_destino.stop)

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_usar_link_de_entidad_con_fechas_de_search_parameters(self, raw_mock):
        raw_mock.return_value = respuesta_mock()

        hospedajes = buscar_hospedajes("Medellin", "Colombia")

        self.assertEqual(len(hospedajes), 2)
        self.assertTrue(hospedajes[0].url_reserva.startswith(
            "https://www.google.com/travel/hotels/entity/ChoTOKENA"))
        self.assertIn("check_in=2026-08-14", hospedajes[0].url_reserva)
        self.assertIn("check_out=2026-08-16", hospedajes[0].url_reserva)

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_fallback_al_sitio_del_hotel_sin_property_token(self, raw_mock):
        raw_mock.return_value = respuesta_mock()

        hospedajes = buscar_hospedajes("Medellin", "Colombia")

        self.assertEqual(hospedajes[1].url_reserva, "https://hotelb.com")

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_filtra_por_presupuesto(self, raw_mock):
        raw_mock.return_value = respuesta_mock()

        hospedajes = buscar_hospedajes("Medellin", "Colombia", precio_maximo_noche=70)

        self.assertEqual(len(hospedajes), 1)
        self.assertEqual(hospedajes[0].nombre, "Hotel A")

    @patch("src.services.buscador_serpapi.DestinoRepository.obtener_o_crear")
    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_sin_properties_devuelve_lista_vacia_sin_crear_destino(self, raw_mock, destino_mock):
        for respuesta in ({"search_parameters": {}}, {"properties": []}):
            with self.subTest(respuesta=respuesta):
                raw_mock.return_value = respuesta

                resultado = buscar_hospedajes("Medellin", "Colombia")

                self.assertEqual(resultado, [])
        destino_mock.assert_not_called()

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_todos_los_hospedajes_llevan_el_destino_resuelto(self, raw_mock):
        raw_mock.return_value = respuesta_mock()

        hospedajes = buscar_hospedajes("Medellin", "Colombia")

        self.assertEqual(len(hospedajes), 2)
        for hospedaje in hospedajes:
            self.assertEqual(hospedaje.destino_id, 42)

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_link_sin_esquema_se_normaliza(self, raw_mock):
        respuesta = respuesta_mock()
        respuesta["properties"][1]["link"] = "hotelb.com/reservas"
        raw_mock.return_value = respuesta

        hospedajes = buscar_hospedajes("Medellin", "Colombia")

        self.assertEqual(hospedajes[1].url_reserva, "https://hotelb.com/reservas")

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_calificacion_ausente_queda_none_y_tipo_desconocido_es_otro(self, raw_mock):
        respuesta = respuesta_mock()
        respuesta["properties"][0].pop("overall_rating")
        respuesta["properties"][0]["type"] = "vacation_rental"
        raw_mock.return_value = respuesta

        hospedajes = buscar_hospedajes("Medellin", "Colombia")

        self.assertIsNone(hospedajes[0].calificacion)
        self.assertEqual(hospedajes[0].tipo, "otro")
        self.assertEqual(hospedajes[1].tipo, "hotel")

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_descripcion_larga_no_se_recorta_a_doscientos(self, raw_mock):
        respuesta = respuesta_mock()
        respuesta["properties"][0]["description"] = "x" * 250
        raw_mock.return_value = respuesta

        hospedajes = buscar_hospedajes("Medellin", "Colombia")

        self.assertEqual(len(hospedajes[0].descripcion), 250)
        self.assertIsNone(hospedajes[0].direccion)

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_direccion_y_descripcion_se_mapean_por_separado(self, raw_mock):
        respuesta = respuesta_mock()
        respuesta["properties"][0]["description"] = "Hotel con piscina"
        respuesta["properties"][0]["address"] = "Calle 10 #20-30"
        raw_mock.return_value = respuesta

        hospedajes = buscar_hospedajes("Medellin", "Colombia")

        self.assertEqual(hospedajes[0].descripcion, "Hotel con piscina")
        self.assertEqual(hospedajes[0].direccion, "Calle 10 #20-30")

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_sin_presupuesto_conserva_hotel_sin_tarifa(self, raw_mock):
        respuesta = respuesta_mock()
        respuesta["properties"][0].pop("rate_per_night")
        raw_mock.return_value = respuesta

        hospedajes = buscar_hospedajes("Medellin", "Colombia")

        self.assertEqual(len(hospedajes), 2)
        self.assertIsNone(hospedajes[0].precio_noche)

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_destino_se_resuelve_una_sola_vez_con_el_destino_correcto(self, raw_mock):
        raw_mock.return_value = respuesta_mock()

        buscar_hospedajes("Medellin", "Colombia")

        from src.services import buscador_serpapi
        buscador_serpapi.DestinoRepository.obtener_o_crear.assert_called_once()

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_si_no_se_puede_guardar_el_destino_propaga_el_error(self, raw_mock):
        raw_mock.return_value = respuesta_mock()
        from src.services import buscador_serpapi
        buscador_serpapi.DestinoRepository.obtener_o_crear.side_effect = ValueError("ciudad vacía")

        with self.assertRaises(ValueError):
            buscar_hospedajes("Medellin", "Colombia")

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_si_consultar_serpapi_falla_propaga_el_error(self, raw_mock):
        raw_mock.side_effect = SerpApiError("consulta", "error de red")

        with self.assertRaises(SerpApiError):
            buscar_hospedajes("Medellin", "Colombia")
        raw_mock.assert_called_once_with("Medellin", "Colombia", None)


class TestConsultarSerpapi(unittest.TestCase):

    @patch("src.services.buscador_serpapi.time.sleep")
    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_REINTENTOS", 0)
    @patch("src.services.buscador_serpapi.requests.get")
    def test_error_de_red_lanza_serpapi_error(self, get_mock, _sleep):
        get_mock.side_effect = requests.exceptions.ConnectionError("sin red")

        with self.assertRaises(SerpApiError):
            consultar_serpapi("Medellin", "Colombia")

    @patch("src.services.buscador_serpapi.requests.get")
    def test_error_de_api_en_json_lanza_serpapi_error(self, get_mock):
        respuesta = unittest.mock.Mock()
        respuesta.raise_for_status.return_value = None
        respuesta.json.return_value = {"error": "Invalid hl value"}
        get_mock.return_value = respuesta

        with self.assertRaises(SerpApiError):
            consultar_serpapi("Medellin", "Colombia")

    @patch("src.services.buscador_serpapi.settings.SERPAPI_KEY", "")
    def test_falta_serpapi_key_lanza_serpapi_error(self):
        with self.assertRaises(SerpApiError):
            consultar_serpapi("Medellin", "Colombia")

    @patch("src.services.buscador_serpapi.settings.SERPAPI_KEY", "clave-prueba")
    @patch("src.services.buscador_serpapi.requests.get")
    def test_respuesta_ok_pasa_presupuesto_y_timeout_a_serpapi(self, get_mock):
        respuesta = unittest.mock.Mock()
        respuesta.raise_for_status.return_value = None
        respuesta.json.return_value = {"properties": []}
        get_mock.return_value = respuesta

        resultado = consultar_serpapi("Medellin", "Colombia", precio_maximo_noche=80)

        parametros = get_mock.call_args.kwargs["params"]
        self.assertEqual(parametros["max_price"], 80)
        self.assertIn("check_in_date", parametros)
        self.assertIn("check_out_date", parametros)
        self.assertEqual(resultado, {"properties": []})
        self.assertEqual(get_mock.call_args.kwargs["timeout"], settings.SERPAPI_TIMEOUT)


class TestIntegracionBuscarYGuardar(BaseDBTestCase):

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_integracion_buscar_y_guardar_persiste(self, mock_raw):
        mock_raw.return_value = respuesta_mock()
        hospedajes = buscar_hospedajes("Medellin", "Colombia")
        self.assertEqual(len(hospedajes), 2)
        hospedaje_repo = HospedajeRepository()
        ids = hospedaje_repo.guardar_lote(hospedajes)
        self.assertTrue(all(isinstance(i, int) for i in ids))
        persistidos = hospedaje_repo.obtener_por_destino(hospedajes[0].destino_id)
        self.assertEqual(len(persistidos), 2)
        self.assertEqual({p.nombre for p in persistidos}, {"Hotel A", "Hotel B"})


def _pagina(properties, next_page_token=None, search_parameters=None):
    """Construye una respuesta de SerpAPI de una sola página para los tests."""
    resultado = {
        "search_parameters": search_parameters or {
            "engine": "google_hotels",
            "q": "hoteles en Medellin Colombia",
            "check_in_date": "2026-08-14",
            "check_out_date": "2026-08-16",
        },
        "properties": properties,
    }
    if next_page_token is not None:
        resultado["serpapi_pagination"] = {"next_page_token": next_page_token}
    return resultado


class TestConsultarSerpapiPaginacion(unittest.TestCase):
    """Paginación con corte por max_pages/max_results y acumulación."""

    def _mock_get_por_pagina(self, paginas):
        """Devuelve un side_effect que selecciona la página según next_page_token.

        ``paginas`` es una lista de dicts (página 1, 2, 3, ...). La primera
        llamada (sin token) devuelve paginas[0], la siguiente el siguiente, etc.
        """
        iterador = iter(paginas)

        def side_effect(url, params=None, timeout=None):
            respuesta = unittest.mock.Mock()
            respuesta.raise_for_status.return_value = None
            respuesta.json.return_value = next(iterador)
            return respuesta

        return side_effect

    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_PAGES", 2)
    @patch("src.services.buscador_serpapi.requests.get")
    def test_max_pages_corta_tras_dos_llamadas_y_conserva_acumulados(self, get_mock):
        paginas = [
            _pagina([{"name": "A"}, {"name": "B"}], next_page_token="tok1"),
            _pagina([{"name": "C"}, {"name": "D"}], next_page_token="tok2"),
            _pagina([{"name": "E"}, {"name": "F"}]),
        ]
        get_mock.side_effect = self._mock_get_por_pagina(paginas)

        resultado = consultar_serpapi("Medellin", "Colombia")

        self.assertEqual(get_mock.call_count, 2)
        nombres = [p["name"] for p in resultado["properties"]]
        self.assertEqual(nombres, ["A", "B", "C", "D"])

    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_RESULTS", 3)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_PAGES", 5)
    @patch("src.services.buscador_serpapi.requests.get")
    def test_max_results_trunca_acumulados_y_detiene_paginacion(self, get_mock):
        paginas = [
            _pagina([{"name": "A"}, {"name": "B"}], next_page_token="tok1"),
            _pagina([{"name": "C"}, {"name": "D"}], next_page_token="tok2"),
            _pagina([{"name": "E"}]),
        ]
        get_mock.side_effect = self._mock_get_por_pagina(paginas)

        resultado = consultar_serpapi("Medellin", "Colombia")

        # Página 1 aporta 2 (total 2), página 2 aporta 2 (total 4) → trunca a 3 y detiene.
        self.assertEqual(get_mock.call_count, 2)
        nombres = [p["name"] for p in resultado["properties"]]
        self.assertEqual(nombres, ["A", "B", "C"])

    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_PAGES", 5)
    @patch("src.services.buscador_serpapi.requests.get")
    def test_fin_natural_sin_token_detiene_iteracion(self, get_mock):
        paginas = [
            _pagina([{"name": "A"}], next_page_token="tok1"),
            _pagina([{"name": "B"}]),  # sin next_page_token → fin natural
            _pagina([{"name": "C"}]),
        ]
        get_mock.side_effect = self._mock_get_por_pagina(paginas)

        resultado = consultar_serpapi("Medellin", "Colombia")

        self.assertEqual(get_mock.call_count, 2)
        self.assertEqual([p["name"] for p in resultado["properties"]], ["A", "B"])

    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_PAGES", 5)
    @patch("src.services.buscador_serpapi.requests.get")
    def test_next_page_token_se_reenvia_como_parametro(self, get_mock):
        paginas = [
            _pagina([{"name": "A"}], next_page_token="tok1"),
            _pagina([{"name": "B"}]),
        ]
        get_mock.side_effect = self._mock_get_por_pagina(paginas)

        consultar_serpapi("Medellin", "Colombia")

        # Primera llamada sin next_page_token
        primera_params = get_mock.call_args_list[0].kwargs["params"]
        self.assertNotIn("next_page_token", primera_params)
        # Segunda llamada con el token de la primera respuesta
        segunda_params = get_mock.call_args_list[1].kwargs["params"]
        self.assertEqual(segunda_params["next_page_token"], "tok1")

    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_PAGES", 5)
    @patch("src.services.buscador_serpapi.requests.get")
    def test_search_parameters_se_conservan_de_la_primera_pagina(self, get_mock):
        paginas = [
            _pagina(
                [{"name": "A"}],
                next_page_token="tok1",
                search_parameters={"check_in_date": "2026-08-14", "check_out_date": "2026-08-16"},
            ),
            _pagina([{"name": "B"}]),
        ]
        get_mock.side_effect = self._mock_get_por_pagina(paginas)

        resultado = consultar_serpapi("Medellin", "Colombia")

        self.assertEqual(resultado["search_parameters"]["check_in_date"], "2026-08-14")
        self.assertEqual(resultado["search_parameters"]["check_out_date"], "2026-08-16")

    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_PAGES", 5)
    @patch("src.services.buscador_serpapi.requests.get")
    def test_respuesta_consolidada_no_expone_serpapi_pagination(self, get_mock):
        paginas = [
            _pagina([{"name": "A"}], next_page_token="tok1"),
            _pagina([{"name": "B"}]),
        ]
        get_mock.side_effect = self._mock_get_por_pagina(paginas)

        resultado = consultar_serpapi("Medellin", "Colombia")

        self.assertNotIn("serpapi_pagination", resultado)


class TestConsultarSerpapiRateLimit(unittest.TestCase):
    """Recuperación ante 429 y límite global de llamadas."""

    def _respuesta_ok(self, properties=None, next_page_token=None):
        respuesta = unittest.mock.Mock()
        respuesta.status_code = 200
        respuesta.headers = {}
        respuesta.raise_for_status.return_value = None
        respuesta.json.return_value = _pagina(properties or [], next_page_token)
        return respuesta

    def _respuesta_429(self, retry_after=None):
        respuesta = unittest.mock.Mock()
        respuesta.status_code = 429
        respuesta.headers = {}
        if retry_after is not None:
            respuesta.headers["Retry-After"] = str(retry_after)
        error = requests.exceptions.HTTPError("too many requests", response=respuesta)
        respuesta.raise_for_status.side_effect = error
        return respuesta

    @patch("src.services.buscador_serpapi.time.sleep")
    @patch("src.services.buscador_serpapi.settings.SERPAPI_BACKOFF_BASE", 0.25)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_REINTENTOS", 2)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_RATE_LIMIT_RPS", 0)
    @patch("src.services.buscador_serpapi.requests.get")
    def test_429_se_recupera_con_reintento_y_backoff(self, get_mock, sleep_mock):
        get_mock.side_effect = [self._respuesta_429(), self._respuesta_ok([{"name": "A"}])]

        resultado = consultar_serpapi("Medellin", "Colombia")

        self.assertEqual(get_mock.call_count, 2)
        self.assertEqual([p["name"] for p in resultado["properties"]], ["A"])
        sleep_mock.assert_called_once_with(0.25)

    @patch("src.services.buscador_serpapi.time.sleep")
    @patch("src.services.buscador_serpapi.settings.SERPAPI_BACKOFF_BASE", 0.5)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_REINTENTOS", 1)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_RATE_LIMIT_RPS", 0)
    @patch("src.services.buscador_serpapi.requests.get")
    def test_retry_after_usa_el_maximo_entre_header_y_backoff(self, get_mock, sleep_mock):
        get_mock.side_effect = [self._respuesta_429(retry_after=2), self._respuesta_ok([{"name": "A"}])]

        consultar_serpapi("Medellin", "Colombia")

        sleep_mock.assert_called_once_with(2.0)

    @patch("src.services.buscador_serpapi.time.sleep")
    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_REINTENTOS", 1)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_RATE_LIMIT_RPS", 0)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_PAGES", 5)
    @patch("src.services.buscador_serpapi.requests.get")
    def test_429_agotado_devuelve_resultados_acumulados(self, get_mock, sleep_mock):
        get_mock.side_effect = [
            self._respuesta_ok([{"name": "A"}], next_page_token="tok1"),
            self._respuesta_429(),
            self._respuesta_429(),
        ]

        resultado = consultar_serpapi("Medellin", "Colombia")

        self.assertEqual(get_mock.call_count, 3)
        self.assertEqual([p["name"] for p in resultado["properties"]], ["A"])

    @patch("src.services.buscador_serpapi.settings.SERPAPI_RATE_LIMIT_RPS", 20)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_PAGES", 1)
    @patch("src.services.buscador_serpapi.requests.get")
    def test_rate_limit_global_no_excede_llamadas_por_segundo_en_dos_hilos(self, get_mock):
        tiempos = []
        lock = threading.Lock()

        def respuesta_con_tiempo(*args, **kwargs):
            with lock:
                tiempos.append(time.monotonic())
            return self._respuesta_ok()

        get_mock.side_effect = respuesta_con_tiempo
        barrera = threading.Barrier(2)

        def ejecutar():
            barrera.wait()
            consultar_serpapi("Medellin", "Colombia")

        hilos = [threading.Thread(target=ejecutar) for _ in range(2)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        self.assertEqual(len(tiempos), 2)
        self.assertGreaterEqual(tiempos[1] - tiempos[0], 0.04)

    @patch("src.services.buscador_serpapi.time.sleep")
    @patch("src.services.buscador_serpapi.settings.SERPAPI_BACKOFF_BASE", 0.25)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_REINTENTOS", 2)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_RATE_LIMIT_RPS", 0)
    @patch("src.services.buscador_serpapi.requests.get")
    def test_5xx_se_reintenta_y_recupera(self, get_mock, sleep_mock):
        respuesta_503 = unittest.mock.Mock()
        respuesta_503.status_code = 503
        respuesta_503.headers = {}
        respuesta_503.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "servicio no disponible", response=respuesta_503
        )
        get_mock.side_effect = [respuesta_503, self._respuesta_ok([{"name": "A"}])]

        resultado = consultar_serpapi("Medellin", "Colombia")

        self.assertEqual(get_mock.call_count, 2)
        self.assertEqual([p["name"] for p in resultado["properties"]], ["A"])
        self.assertEqual(sleep_mock.call_args_list[0].args, (0.25,))

    @patch("src.services.buscador_serpapi.time.sleep")
    @patch("src.services.buscador_serpapi.settings.SERPAPI_BACKOFF_BASE", 0.25)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_REINTENTOS", 2)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_RATE_LIMIT_RPS", 0)
    @patch("src.services.buscador_serpapi.requests.get")
    def test_timeout_se_reintenta_y_recupera(self, get_mock, sleep_mock):
        get_mock.side_effect = [
            requests.exceptions.Timeout("timeout"),
            self._respuesta_ok([{"name": "A"}]),
        ]

        resultado = consultar_serpapi("Medellin", "Colombia")

        self.assertEqual(get_mock.call_count, 2)
        self.assertEqual([p["name"] for p in resultado["properties"]], ["A"])
        self.assertEqual(sleep_mock.call_args_list[0].args, (0.25,))

    @patch("src.services.buscador_serpapi.time.sleep")
    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_REINTENTOS", 0)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_RATE_LIMIT_RPS", 0)
    @patch("src.services.buscador_serpapi.requests.get")
    def test_429_en_la_primera_pagina_lanza_error(self, get_mock, _sleep):
        get_mock.return_value = self._respuesta_429()

        with self.assertRaises(SerpApiError):
            consultar_serpapi("Medellin", "Colombia")


if __name__ == '__main__':
    unittest.main()

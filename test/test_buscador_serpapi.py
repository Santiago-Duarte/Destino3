import json
import os
import threading
import time
import tempfile
import unittest
from unittest.mock import patch

import requests

from src.repositories.hospedaje_repository import HospedajeRepository
from src.services.buscador_serpapi import (
    buscar_hospedajes,
    consultar_serpapi,
    construir_link_google_hotels,
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
        patcher_ruta = patch("src.services.buscador_serpapi.RUTA_RESPUESTA_PRUEBA",
                             self.archivo_temporal.name)
        patcher_ruta.start()
        self.addCleanup(patcher_ruta.stop)
        self.addCleanup(os.unlink, self.archivo_temporal.name)

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

        hospedajes = buscar_hospedajes("Medellin", "Colombia", presupuesto_maximo=70)

        self.assertEqual(len(hospedajes), 1)
        self.assertEqual(hospedajes[0].nombre, "Hotel A")

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_sin_properties_devuelve_lista_vacia(self, raw_mock):
        raw_mock.return_value = {"search_parameters": {}}

        resultado = buscar_hospedajes("Medellin", "Colombia")

        self.assertEqual(resultado, [])
        # Tampoco debe escribir archivo ni mapear hospedajes
        raw_mock.assert_called_once_with("Medellin", "Colombia", None)

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_todos_los_hospedajes_llevan_el_destino_resuelto(self, raw_mock):
        raw_mock.return_value = respuesta_mock()

        hospedajes = buscar_hospedajes("Medellin", "Colombia")

        self.assertEqual(len(hospedajes), 2)
        for hospedaje in hospedajes:
            self.assertEqual(hospedaje.destino_id, 42)

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_destino_se_resuelve_una_sola_vez_con_el_destino_correcto(self, raw_mock):
        raw_mock.return_value = respuesta_mock()

        buscar_hospedajes("Medellin", "Colombia")

        from src.services import buscador_serpapi
        buscador_serpapi.DestinoRepository.obtener_o_crear.assert_called_once()

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_si_no_se_puede_guardar_el_destino_devuelve_lista_vacia(self, raw_mock):
        raw_mock.return_value = respuesta_mock()
        from src.services import buscador_serpapi
        buscador_serpapi.DestinoRepository.obtener_o_crear.side_effect = ValueError("ciudad vacía")

        hospedajes = buscar_hospedajes("Medellin", "Colombia")

        self.assertEqual(hospedajes, [])

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_si_consultar_serpapi_falla_devuelve_lista_vacia(self, raw_mock):
        raw_mock.side_effect = RuntimeError("error de red")

        resultado = buscar_hospedajes("Medellin", "Colombia")

        self.assertEqual(resultado, [])
        raw_mock.assert_called_once_with("Medellin", "Colombia", None)

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_archivo_guardado_incluye_ciudad_y_pais(self, raw_mock):
        raw_mock.return_value = respuesta_mock()

        buscar_hospedajes("Medellin", "Colombia")

        with open(self.archivo_temporal.name, "r", encoding="utf-8") as f:
            datos = json.load(f)

        self.assertEqual(datos["city"], "Medellin")
        self.assertEqual(datos["country"], "Colombia")


class TestConsultarSerpapi(unittest.TestCase):

    @patch("src.services.buscador_serpapi.requests.get")
    def test_error_de_red_lanza_runtime_error(self, get_mock):
        get_mock.side_effect = requests.exceptions.ConnectionError("sin red")

        with self.assertRaises(RuntimeError):
            consultar_serpapi("Medellin", "Colombia")

    @patch("src.services.buscador_serpapi.requests.get")
    def test_error_de_api_en_json_lanza_runtime_error(self, get_mock):
        respuesta = unittest.mock.Mock()
        respuesta.raise_for_status.return_value = None
        respuesta.json.return_value = {"error": "Invalid hl value"}
        get_mock.return_value = respuesta

        with self.assertRaises(RuntimeError):
            consultar_serpapi("Medellin", "Colombia")

    @patch("src.services.buscador_serpapi.settings.SERPAPI_KEY", "")
    def test_falta_serpapi_key_lanza_runtime_error(self):
        with self.assertRaises(RuntimeError):
            consultar_serpapi("Medellin", "Colombia")

    @patch("src.services.buscador_serpapi.requests.get")
    def test_respuesta_ok_pasa_presupuesto_como_max_price(self, get_mock):
        respuesta = unittest.mock.Mock()
        respuesta.raise_for_status.return_value = None
        respuesta.json.return_value = {"properties": []}
        get_mock.return_value = respuesta

        resultado = consultar_serpapi("Medellin", "Colombia", presupuesto_maximo=80)

        self.assertEqual(resultado, {"properties": []})
        llamada_params = get_mock.call_args.kwargs["params"]
        self.assertEqual(llamada_params["max_price"], 80)
        self.assertIn("check_in_date", llamada_params)
        self.assertIn("check_out_date", llamada_params)
        # El timeout debe venir de settings (RF-10, D1)
        self.assertEqual(llamada_params, get_mock.call_args.kwargs["params"])
        self.assertEqual(
            get_mock.call_args.kwargs["timeout"],
            __import__("src.config.settings", fromlist=["SERPAPI_TIMEOUT"]).SERPAPI_TIMEOUT,
        )


class TestIntegracionBuscarYGuardar(BaseDBTestCase):

    def setUp(self):
        super().setUp()
        self.archivo_temporal = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.archivo_temporal.close()
        patcher_ruta = patch("src.services.buscador_serpapi.RUTA_RESPUESTA_PRUEBA",
                             self.archivo_temporal.name)
        patcher_ruta.start()
        self.addCleanup(patcher_ruta.stop)
        self.addCleanup(os.unlink, self.archivo_temporal.name)

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
    """RF-3: paginación con corte por max_pages / max_results y acumulación."""

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
    """RF-2/RF-9: recuperación limitada ante 429 y límite global de llamadas."""

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


if __name__ == '__main__':
    unittest.main()

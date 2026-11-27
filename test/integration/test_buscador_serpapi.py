import threading
import time
import unittest
from datetime import date
from unittest.mock import patch

import requests

from src.config import settings
from src.exceptions import SerpApiError
from src.models.busqueda import EspecificacionBusqueda
from src.repositories.hospedaje_repository import HospedajeRepository
from src.services.buscador_serpapi import (
    buscar_hospedajes,
    construir_url_reserva,
    consultar_serpapi,
)
from test.caso_prueba_bd import BaseDBTestCase

ESPEC = EspecificacionBusqueda(
    ciudad="Medellin",
    pais="Colombia",
    fecha_entrada=date(2026, 8, 14),
    fecha_salida=date(2026, 8, 16),
    adultos=2,
    ninos=0,
    mascotas=False,
)


def espec_con(**cambios) -> EspecificacionBusqueda:
    return ESPEC.model_copy(update=cambios)


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
                "gps_coordinates": {"latitude": 6.2442, "longitude": -75.5812},
            },
            {
                "name": "Hotel B",
                "rate_per_night": {"lowest": "$83", "extracted_lowest": 83},
                "overall_rating": 4.0,
                "description": "Bocagrande",
                "link": "https://hotelb.com",
                "gps_coordinates": {"latitude": 6.2088, "longitude": -75.5671},
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

        hospedajes = buscar_hospedajes(ESPEC)

        self.assertEqual(len(hospedajes), 2)
        self.assertTrue(hospedajes[0].url_reserva.startswith(
            "https://www.google.com/travel/hotels/entity/ChoTOKENA"))
        self.assertIn("check_in=2026-08-14", hospedajes[0].url_reserva)
        self.assertIn("check_out=2026-08-16", hospedajes[0].url_reserva)

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_fallback_al_sitio_del_hotel_sin_property_token(self, raw_mock):
        raw_mock.return_value = respuesta_mock()

        hospedajes = buscar_hospedajes(ESPEC)

        self.assertEqual(hospedajes[1].url_reserva, "https://hotelb.com")

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_url_de_reserva_usa_las_fechas_de_la_especificacion(self, raw_mock):
        respuesta = respuesta_mock()
        respuesta.pop("search_parameters")
        raw_mock.return_value = respuesta

        hospedajes = buscar_hospedajes(ESPEC)

        self.assertIn("check_in=2026-08-14", hospedajes[0].url_reserva)
        self.assertIn("check_out=2026-08-16", hospedajes[0].url_reserva)

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_filtra_por_presupuesto(self, raw_mock):
        raw_mock.return_value = respuesta_mock()

        hospedajes = buscar_hospedajes(espec_con(presupuesto_max_noche=70))

        self.assertEqual(len(hospedajes), 1)
        self.assertEqual(hospedajes[0].nombre, "Hotel A")

    @patch("src.services.buscador_serpapi.DestinoRepository.obtener_o_crear")
    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_sin_properties_devuelve_lista_vacia_sin_crear_destino(self, raw_mock, destino_mock):
        for respuesta in ({"search_parameters": {}}, {"properties": []}):
            with self.subTest(respuesta=respuesta):
                raw_mock.return_value = respuesta

                resultado = buscar_hospedajes(ESPEC)

                self.assertEqual(resultado, [])
        destino_mock.assert_not_called()

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_todos_los_hospedajes_llevan_el_destino_resuelto(self, raw_mock):
        raw_mock.return_value = respuesta_mock()

        hospedajes = buscar_hospedajes(ESPEC)

        self.assertEqual(len(hospedajes), 2)
        for hospedaje in hospedajes:
            self.assertEqual(hospedaje.destino_id, 42)

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_link_sin_esquema_se_normaliza(self, raw_mock):
        respuesta = respuesta_mock()
        respuesta["properties"][1]["link"] = "hotelb.com/reservas"
        raw_mock.return_value = respuesta

        hospedajes = buscar_hospedajes(ESPEC)

        self.assertEqual(hospedajes[1].url_reserva, "https://hotelb.com/reservas")

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_link_con_protocolo_relativo_se_prefija_https(self, raw_mock):
        respuesta = respuesta_mock()
        respuesta["properties"][1]["link"] = "//hotelb.com/reservas"
        raw_mock.return_value = respuesta

        hospedajes = buscar_hospedajes(ESPEC)

        self.assertEqual(hospedajes[1].url_reserva, "https://hotelb.com/reservas")

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_link_ausente_queda_como_url_vacia(self, raw_mock):
        respuesta = respuesta_mock()
        respuesta["properties"][1].pop("link")
        raw_mock.return_value = respuesta

        hospedajes = buscar_hospedajes(ESPEC)

        self.assertEqual(hospedajes[1].url_reserva, "")

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_tarifa_no_numerica_queda_sin_precio(self, raw_mock):
        respuesta = respuesta_mock()
        respuesta["properties"][0]["rate_per_night"] = {
            "lowest": "N/A",
            "extracted_lowest": "N/A",
        }
        raw_mock.return_value = respuesta

        hospedajes = buscar_hospedajes(ESPEC)

        self.assertIsNone(hospedajes[0].precio_noche)

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_sin_precio_y_con_presupuesto_se_excluye(self, raw_mock):
        respuesta = respuesta_mock()
        respuesta["properties"][0].pop("rate_per_night")
        raw_mock.return_value = respuesta

        hospedajes = buscar_hospedajes(espec_con(presupuesto_max_noche=70))

        # Sin tarifa no se puede comparar y Hotel B cuesta 83: no cabe ninguno.
        self.assertEqual(hospedajes, [])

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_calificacion_ausente_queda_none_y_tipo_desconocido_es_otro(self, raw_mock):
        respuesta = respuesta_mock()
        respuesta["properties"][0].pop("overall_rating")
        respuesta["properties"][0]["type"] = "vacation_rental"
        raw_mock.return_value = respuesta

        hospedajes = buscar_hospedajes(ESPEC)

        self.assertIsNone(hospedajes[0].calificacion)
        self.assertEqual(hospedajes[0].tipo, "otro")
        self.assertEqual(hospedajes[1].tipo, "hotel")

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_descripcion_larga_no_se_recorta_a_doscientos(self, raw_mock):
        respuesta = respuesta_mock()
        respuesta["properties"][0]["description"] = "x" * 250
        raw_mock.return_value = respuesta

        hospedajes = buscar_hospedajes(ESPEC)

        self.assertEqual(len(hospedajes[0].descripcion), 250)
        self.assertIsNone(hospedajes[0].direccion)

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_direccion_y_descripcion_se_mapean_por_separado(self, raw_mock):
        respuesta = respuesta_mock()
        respuesta["properties"][0]["description"] = "Hotel con piscina"
        respuesta["properties"][0]["address"] = "Calle 10 #20-30"
        raw_mock.return_value = respuesta

        hospedajes = buscar_hospedajes(ESPEC)

        self.assertEqual(hospedajes[0].descripcion, "Hotel con piscina")
        self.assertEqual(hospedajes[0].direccion, "Calle 10 #20-30")

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_extrae_coordenadas_gps_de_cada_propiedad(self, raw_mock):
        raw_mock.return_value = respuesta_mock()

        hospedajes = buscar_hospedajes(ESPEC)

        self.assertEqual(hospedajes[0].coordenadas(), (6.2442, -75.5812))
        self.assertEqual(hospedajes[1].coordenadas(), (6.2088, -75.5671))

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_sin_gps_las_coordenadas_quedan_en_none(self, raw_mock):
        respuesta = respuesta_mock()
        respuesta["properties"][0].pop("gps_coordinates")
        raw_mock.return_value = respuesta

        hospedajes = buscar_hospedajes(ESPEC)

        self.assertIsNone(hospedajes[0].coordenadas())

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_gps_invalido_queda_en_none(self, raw_mock):
        respuesta = respuesta_mock()
        respuesta["properties"][0]["gps_coordinates"] = {
            "latitude": "N/A",
            "longitude": None,
        }
        raw_mock.return_value = respuesta

        hospedajes = buscar_hospedajes(ESPEC)

        self.assertIsNone(hospedajes[0].coordenadas())

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_sin_presupuesto_conserva_hotel_sin_tarifa(self, raw_mock):
        respuesta = respuesta_mock()
        respuesta["properties"][0].pop("rate_per_night")
        raw_mock.return_value = respuesta

        hospedajes = buscar_hospedajes(ESPEC)

        self.assertEqual(len(hospedajes), 2)
        self.assertIsNone(hospedajes[0].precio_noche)

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_destino_se_resuelve_una_sola_vez_con_el_destino_correcto(self, raw_mock):
        raw_mock.return_value = respuesta_mock()

        buscar_hospedajes(ESPEC)

        from src.services import buscador_serpapi
        llamada = buscador_serpapi.DestinoRepository.obtener_o_crear.call_args
        buscador_serpapi.DestinoRepository.obtener_o_crear.assert_called_once()
        destino_llamado = llamada.args[0]
        self.assertEqual(destino_llamado.ciudad, "Medellin")
        self.assertEqual(destino_llamado.pais, "Colombia")

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_si_no_se_puede_guardar_el_destino_propaga_el_error(self, raw_mock):
        raw_mock.return_value = respuesta_mock()
        from src.services import buscador_serpapi
        buscador_serpapi.DestinoRepository.obtener_o_crear.side_effect = ValueError("ciudad vacía")

        with self.assertRaises(ValueError):
            buscar_hospedajes(ESPEC)

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_si_consultar_serpapi_falla_propaga_el_error(self, raw_mock):
        raw_mock.side_effect = SerpApiError("consulta", "error de red")

        with self.assertRaises(SerpApiError):
            buscar_hospedajes(ESPEC)
        raw_mock.assert_called_once_with(ESPEC)


class TestConsultarSerpapi(unittest.TestCase):

    @patch("src.services.buscador_serpapi.time.sleep")
    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_REINTENTOS", 0)
    @patch("src.services.buscador_serpapi.requests.get")
    def test_error_de_red_lanza_serpapi_error(self, get_mock, _sleep):
        get_mock.side_effect = requests.exceptions.ConnectionError("sin red")

        with self.assertRaises(SerpApiError):
            consultar_serpapi(ESPEC)

    @patch("src.services.buscador_serpapi.requests.get")
    def test_error_de_api_en_json_lanza_serpapi_error(self, get_mock):
        respuesta = unittest.mock.Mock()
        respuesta.raise_for_status.return_value = None
        respuesta.json.return_value = {"error": "Invalid hl value"}
        get_mock.return_value = respuesta

        with self.assertRaises(SerpApiError):
            consultar_serpapi(ESPEC)

    @patch("src.services.buscador_serpapi.settings.SERPAPI_KEY", "")
    def test_falta_serpapi_key_lanza_serpapi_error(self):
        with self.assertRaises(SerpApiError):
            consultar_serpapi(ESPEC)

    @patch("src.services.buscador_serpapi.settings.SERPAPI_KEY", "clave-prueba")
    @patch("src.services.buscador_serpapi.requests.get")
    def test_respuesta_ok_pasa_presupuesto_y_timeout_a_serpapi(self, get_mock):
        respuesta = unittest.mock.Mock()
        respuesta.raise_for_status.return_value = None
        respuesta.json.return_value = {"properties": []}
        get_mock.return_value = respuesta

        resultado = consultar_serpapi(espec_con(presupuesto_max_noche=80))

        parametros = get_mock.call_args.kwargs["params"]
        self.assertEqual(parametros["max_price"], 80)
        self.assertEqual(parametros["check_in_date"], "2026-08-14")
        self.assertEqual(parametros["check_out_date"], "2026-08-16")
        self.assertEqual(parametros["adults"], 2)
        self.assertEqual(parametros["children"], 0)
        self.assertEqual(parametros["currency"], "USD")
        self.assertEqual(resultado, {"properties": []})
        self.assertEqual(get_mock.call_args.kwargs["timeout"], settings.SERPAPI_TIMEOUT)

    @patch("src.services.buscador_serpapi.settings.SERPAPI_KEY", "clave-prueba")
    @patch("src.services.buscador_serpapi.requests.get")
    def test_mascotas_filtra_por_amenity_pet_friendly(self, get_mock):
        respuesta = unittest.mock.Mock()
        respuesta.raise_for_status.return_value = None
        respuesta.json.return_value = {"properties": []}
        get_mock.return_value = respuesta

        consultar_serpapi(espec_con(mascotas=True))

        parametros = get_mock.call_args.kwargs["params"]
        self.assertEqual(parametros["amenities"], "19")

    @patch("src.services.buscador_serpapi.time.sleep")
    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_REINTENTOS", 2)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_RATE_LIMIT_RPS", 0)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_KEY", "clave-prueba")
    @patch("src.services.buscador_serpapi.requests.get")
    def test_http_401_no_se_reintenta_y_lanza_error(self, get_mock, _sleep):
        respuesta = unittest.mock.Mock()
        respuesta.status_code = 401
        respuesta.headers = {}
        respuesta.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "no autorizado", response=respuesta
        )
        get_mock.return_value = respuesta

        with self.assertRaises(SerpApiError) as contexto:
            consultar_serpapi(ESPEC)

        self.assertIn("HTTP 401", str(contexto.exception))
        self.assertEqual(get_mock.call_count, 1)

    @patch("src.services.buscador_serpapi.time.sleep")
    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_REINTENTOS", 2)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_RATE_LIMIT_RPS", 0)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_KEY", "clave-prueba")
    @patch("src.services.buscador_serpapi.requests.get")
    def test_otro_error_de_requests_no_se_reintenta(self, get_mock, _sleep):
        get_mock.side_effect = requests.exceptions.RequestException("algo raro")

        with self.assertRaises(SerpApiError) as contexto:
            consultar_serpapi(ESPEC)

        self.assertIn("RequestException", str(contexto.exception))
        self.assertEqual(get_mock.call_count, 1)

    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_PAGES", 0)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_KEY", "clave-prueba")
    def test_max_pages_en_cero_es_configuracion_invalida(self):
        with self.assertRaises(ValueError):
            consultar_serpapi(ESPEC)

    @patch("src.services.buscador_serpapi.settings.SERPAPI_KEY", "clave-prueba")
    def test_sin_fechas_falla_antes_de_llamar_a_serpapi(self):
        with self.assertRaises(ValueError):
            consultar_serpapi(espec_con(fecha_entrada=None))


class TestIntegracionBuscarYGuardar(BaseDBTestCase):

    @patch("src.services.buscador_serpapi.consultar_serpapi")
    def test_integracion_buscar_y_guardar_persiste(self, mock_raw):
        mock_raw.return_value = respuesta_mock()
        hospedajes = buscar_hospedajes(ESPEC)
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

        resultado = consultar_serpapi(ESPEC)

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

        resultado = consultar_serpapi(ESPEC)

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

        resultado = consultar_serpapi(ESPEC)

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

        consultar_serpapi(ESPEC)

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

        resultado = consultar_serpapi(ESPEC)

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

        resultado = consultar_serpapi(ESPEC)

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

        resultado = consultar_serpapi(ESPEC)

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

        consultar_serpapi(ESPEC)

        sleep_mock.assert_called_once_with(2.0)

    @patch("src.services.buscador_serpapi.time.sleep")
    @patch("src.services.buscador_serpapi.settings.SERPAPI_BACKOFF_BASE", 0.25)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_REINTENTOS", 1)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_RATE_LIMIT_RPS", 0)
    @patch("src.services.buscador_serpapi.requests.get")
    def test_retry_after_no_numerico_usa_el_backoff(self, get_mock, sleep_mock):
        get_mock.side_effect = [
            self._respuesta_429(retry_after="ahora"),
            self._respuesta_ok([{"name": "A"}]),
        ]

        consultar_serpapi(ESPEC)

        sleep_mock.assert_called_once_with(0.25)

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

        resultado = consultar_serpapi(ESPEC)

        self.assertEqual(get_mock.call_count, 3)
        self.assertEqual([p["name"] for p in resultado["properties"]], ["A"])

    @patch("src.services.buscador_serpapi.settings.SERPAPI_RATE_LIMIT_RPS", 20)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_PAGES", 1)
    @patch("src.services.buscador_serpapi.requests.get")
    def test_rate_limit_global_no_excede_llamadas_por_segundo_en_dos_hilos(self, get_mock):
        from src.services import buscador_serpapi

        # El estado global del módulo no debe arrastrarse de otras pruebas.
        buscador_serpapi._ultima_llamada = 0.0
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
            consultar_serpapi(ESPEC)

        hilos = [threading.Thread(target=ejecutar) for _ in range(2)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        self.assertEqual(len(tiempos), 2)
        # El intervalo es 1/20 s = 0.05 s; se exige casi todo el intervalo.
        self.assertGreaterEqual(tiempos[1] - tiempos[0], 0.03)

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

        resultado = consultar_serpapi(ESPEC)

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

        resultado = consultar_serpapi(ESPEC)

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
            consultar_serpapi(ESPEC)



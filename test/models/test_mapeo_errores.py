import unittest
from datetime import date
from unittest.mock import MagicMock, patch

import requests

from src.exceptions import PersistenciaError, SerpApiError
from src.models.busqueda import EspecificacionBusqueda
from src.models.destino import Destino
from src.repositories.destino_repository import DestinoRepository
from src.services.buscador_serpapi import consultar_serpapi

ESPEC = EspecificacionBusqueda(
    ciudad="Medellin",
    pais="Colombia",
    fecha_entrada=date(2026, 8, 14),
    fecha_salida=date(2026, 8, 16),
)


class TestMapeoErroresServicios(unittest.TestCase):

    @patch("src.services.buscador_serpapi.time.sleep")
    @patch("src.services.buscador_serpapi.settings.SERPAPI_MAX_REINTENTOS", 0)
    @patch("src.services.buscador_serpapi.settings.SERPAPI_RATE_LIMIT_RPS", 0)
    @patch("src.services.buscador_serpapi.requests.get")
    def test_serpapi_conserva_causa_y_contexto_en_error_de_red(
            self, get_mock, _sleep
    ):
        causa = requests.exceptions.ConnectionError("sin red")
        get_mock.side_effect = causa

        with self.assertRaises(SerpApiError) as contexto:
            consultar_serpapi(ESPEC)

        self.assertIs(contexto.exception.__cause__, causa)
        self.assertEqual(contexto.exception.proveedor, "SerpAPI")
        self.assertEqual(contexto.exception.operacion, "consulta")

    def test_destino_repository_expone_error_de_persistencia_contextualizado(self):
        repo = DestinoRepository()
        cursor = MagicMock()
        cursor.fetchone.side_effect = [None, None, None]
        transaccion = MagicMock()
        transaccion.__enter__.return_value = cursor
        transaccion.__exit__.return_value = None

        with patch("src.repositories.base_repository.BaseRepository._transaccion", return_value=transaccion):
            with self.assertRaises(PersistenciaError) as contexto:
                repo.obtener_o_crear(Destino(ciudad="Medellin", pais="Colombia"))

        self.assertEqual(contexto.exception.proveedor, "PostgreSQL")
        self.assertEqual(contexto.exception.operacion, "obtener_o_crear_destino")
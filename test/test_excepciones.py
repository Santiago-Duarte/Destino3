import unittest
from unittest.mock import MagicMock, patch

import requests

from src.exceptions import (
    Destino3Error,
    EvaluacionIALoteError,
    GeminiError,
    PersistenciaError,
    SerpApiError,
)
from src.models.destino import Destino
from src.repositories.destino_repository import DestinoRepository
from src.services.buscador_serpapi import consultar_serpapi


class TestExcepcionesPersonalizadas(unittest.TestCase):

    def test_jerarquia_y_contexto_de_excepciones(self):
        error = SerpApiError(
            proveedor="SerpAPI",
            operacion="consulta",
            detalle="sin conexión",
        )

        self.assertIsInstance(error, Destino3Error)
        self.assertEqual(error.proveedor, "SerpAPI")
        self.assertEqual(error.operacion, "consulta")
        self.assertEqual(error.detalle, "sin conexión")
        self.assertIn("SerpAPI", str(error))
        self.assertIn("consulta", str(error))
        self.assertIsInstance(EvaluacionIALoteError("Gemini", "evaluar_lote", "falló"), GeminiError)
        self.assertIsInstance(PersistenciaError("PostgreSQL", "guardar", "falló"), Destino3Error)

    @patch("src.services.buscador_serpapi.settings.SERPAPI_RATE_LIMIT_RPS", 0)
    @patch("src.services.buscador_serpapi.requests.get")
    def test_serpapi_conserva_causa_y_contexto_en_error_de_red(self, get_mock):
        causa = requests.exceptions.ConnectionError("sin red")
        get_mock.side_effect = causa

        with self.assertRaises(SerpApiError) as contexto:
            consultar_serpapi("Medellin", "Colombia")

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


if __name__ == "__main__":
    unittest.main()

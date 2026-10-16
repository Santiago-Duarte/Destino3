import os
import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

from src import demo_integracion
from src.config import database, settings


class TestDemoIntegracion(unittest.TestCase):
    def _argumentos(self):
        return Namespace(
            ciudad="Medellin",
            pais="Colombia",
            presupuesto_max=100.0,
            preferencias="",
        )

    def test_entorno_invalido_no_consulta_dependencias(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "testing"}, clear=True):
            with patch("src.config.database.obtener_conexion") as obtener_conexion:
                with patch("src.services.buscador_serpapi.buscar_hospedajes") as buscar_hospedajes:
                    with patch("src.services.evaluador_ia.EvaluadorIA") as evaluador:
                        with patch(
                            "src.orchestrator.orquestador_integracion.OrquestadorIntegracion"
                        ) as orquestador:
                            resultado = demo_integracion.ejecutar_demo(self._argumentos())

        self.assertEqual(resultado, 1)
        obtener_conexion.assert_not_called()
        buscar_hospedajes.assert_not_called()
        evaluador.assert_not_called()
        orquestador.assert_not_called()

    def test_entorno_demo_conecta_a_demo_db_despues_de_validar(self):
        variables = {
            "ENVIRONMENT": "demo",
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
            "DB_DEMO_NAME": "demo_db",
            "DB_DEMO_USER": "destino3_demo",
            "DB_DEMO_PASSWORD": "password-demo",
        }
        conexion = MagicMock()
        orquestador = MagicMock()
        orquestador.ejecutar.return_value = []

        def construir_orquestador():
            conexion_configurada = database.obtener_conexion()
            conexion_configurada.close()
            return orquestador

        with patch.dict(os.environ, variables, clear=True):
            with patch.object(settings, "SERPAPI_KEY", "clave-serpapi"):
                with patch.object(settings, "GEMINI_API_KEY", "clave-gemini"):
                    with patch.object(database.psycopg2, "connect", return_value=conexion) as conectar:
                        with patch(
                            "src.orchestrator.orquestador_integracion.OrquestadorIntegracion",
                            side_effect=construir_orquestador,
                        ):
                            resultado = demo_integracion.ejecutar_demo(self._argumentos())

        self.assertEqual(resultado, 0)
        conectar.assert_called_once_with(
            host="localhost",
            port="5432",
            database="demo_db",
            user="destino3_demo",
            password="password-demo",
        )
        orquestador.ejecutar.assert_called_once()


if __name__ == "__main__":
    unittest.main()

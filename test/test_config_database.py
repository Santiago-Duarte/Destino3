import os
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.config import database


class TestObtenerConexion(unittest.TestCase):
    def _variables_entorno(self, entorno):
        return {
            "ENVIRONMENT": entorno,
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
            "DB_TEST_NAME": "destino3_test_db",
            "DB_TEST_USER": "destino3_testing",
            "DB_TEST_PASSWORD": "password-testing",
            "DB_DEMO_NAME": "demo_db",
            "DB_DEMO_USER": "destino3_demo",
            "DB_DEMO_PASSWORD": "password-demo",
            "DB_PRODUCTION_NAME": "destino3_db",
            "DB_PRODUCTION_USER": "destino3_production",
            "DB_PRODUCTION_PASSWORD": "password-production",
        }

    def test_selecciona_el_triplete_de_cada_entorno(self):
        conexion = MagicMock()
        esperados = {
            "testing": ("destino3_test_db", "destino3_testing", "password-testing"),
            "demo": ("demo_db", "destino3_demo", "password-demo"),
            "production": ("destino3_db", "destino3_production", "password-production"),
        }

        for entorno, parametros_esperados in esperados.items():
            with self.subTest(entorno=entorno):
                variables = self._variables_entorno(entorno)
                with patch.dict(os.environ, variables, clear=True):
                    with patch.object(database.psycopg2, "connect", return_value=conexion) as conectar:
                        self.assertIs(database.obtener_conexion(), conexion)

                conectar.assert_called_once_with(
                    host="localhost",
                    port="5432",
                    database=parametros_esperados[0],
                    user=parametros_esperados[1],
                    password=parametros_esperados[2],
                )

    def test_entorno_desconocido_falla_antes_de_conectar(self):
        variables = self._variables_entorno("development")

        with patch.dict(os.environ, variables, clear=True):
            with patch.object(database.psycopg2, "connect") as conectar:
                with self.assertRaises(ValueError):
                    database.obtener_conexion()

        conectar.assert_not_called()

    def test_variable_de_base_ausente_no_hace_fallback_ni_conecta(self):
        variables = self._variables_entorno("testing")
        variables.pop("DB_TEST_NAME")
        variables["DB_NAME"] = "destino3_db"

        with patch.dict(os.environ, variables, clear=True):
            with patch.object(database.psycopg2, "connect") as conectar:
                with self.assertRaises(ValueError):
                    database.obtener_conexion()

        conectar.assert_not_called()

    def test_harness_fuerza_testing_y_no_selecciona_demo_ni_production(self):
        raiz = Path(__file__).parents[1]
        codigo = textwrap.dedent("""
            import os
            from unittest.mock import patch
            
            __import__("test")
            from src.config import database
            
            with patch.object(database.psycopg2, "connect") as conectar:
                database.obtener_conexion()
            
            if os.getenv("ENVIRONMENT") != "testing":
                raise AssertionError("El paquete de tests no fijó ENVIRONMENT=testing")
            conectar.assert_called_once_with(
                host="localhost",
                port="5432",
                database="destino3_test_db",
                user="destino3_testing",
                password="password-testing",
            )
            print("testing")
        """)

        for entorno_inicial in ("testing", "demo", "production"):
            with self.subTest(entorno_inicial=entorno_inicial):
                variables = {
                    "PATH": os.environ.get("PATH", ""),
                    "HOME": os.environ.get("HOME", ""),
                    "PYTHONPATH": str(raiz),
                    **self._variables_entorno(entorno_inicial),
                }
                resultado = subprocess.run(
                    [sys.executable, "-c", codigo],
                    cwd=raiz,
                    env=variables,
                    capture_output=True,
                    text=True,
                    check=False,
                )

                self.assertEqual(resultado.returncode, 0, msg=resultado.stderr)
                self.assertEqual(resultado.stdout.strip(), "testing")


if __name__ == "__main__":
    unittest.main()

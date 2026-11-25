import unittest
from unittest.mock import patch

from src.config import settings
from src.services.gemini import crear_cliente


class TestCrearCliente(unittest.TestCase):

    @patch("src.services.gemini.settings.GEMINI_API_KEY", "")
    def test_sin_credencial_lanza_value_error(self):
        with self.assertRaises(ValueError):
            crear_cliente()

    @patch("src.services.gemini.settings.GEMINI_API_KEY", "clave-prueba")
    @patch("src.services.gemini.genai.Client")
    def test_aplica_el_timeout_configurado_en_milisegundos(self, cliente_mock):
        crear_cliente()

        opciones = cliente_mock.call_args.kwargs["http_options"]
        self.assertEqual(opciones.timeout, int(settings.GEMINI_TIMEOUT * 1000))



import json
import unittest
from unittest.mock import Mock, patch

from src.models.busqueda import EspecificacionBusqueda
from src.services.interpretador_ia import InterpretadorIA

FRASE = "quiero hoteles en Medellin, Colombia hasta 100 USD cerca del metro"


def respuesta_con(**campos) -> Mock:
    datos = {
        "ciudad": "Medellin",
        "pais": "Colombia",
        "presupuesto_max_noche": 100,
        "preferencias": "cerca del metro",
    }
    datos.update(campos)
    return Mock(text=json.dumps(datos))


@patch("time.sleep")
@patch("src.services.gemini.settings.GEMINI_API_KEY", "clave-prueba")
@patch("src.services.gemini.genai.Client")
class TestInterpretadorIA(unittest.TestCase):

    def _interpretar(self, cliente_mock, respuesta: Mock) -> EspecificacionBusqueda:
        cliente_mock.return_value.models.generate_content.return_value = respuesta
        return InterpretadorIA().interpretar(FRASE)

    def test_extrae_normaliza_y_manda_la_frase_al_prompt(self, cliente_mock, _sleep):
        espec = self._interpretar(cliente_mock, respuesta_con(
            ciudad="  Medellin ",
            pais=" Colombia",
            preferencias="  cerca del metro  ",
        ))

        self.assertEqual(espec.ciudad, "Medellin")
        self.assertEqual(espec.pais, "Colombia")
        self.assertEqual(espec.presupuesto_max_noche, 100.0)
        self.assertEqual(espec.preferencias, "cerca del metro")

        llamada = cliente_mock.return_value.models.generate_content.call_args
        self.assertIn(FRASE, llamada.kwargs["contents"])
        self.assertIs(llamada.kwargs["config"].response_schema, EspecificacionBusqueda)

    def test_sin_ciudad_falla(self, cliente_mock, _sleep):
        with self.assertRaises(ValueError):
            self._interpretar(cliente_mock, respuesta_con(ciudad="   "))

    def test_sin_pais_falla(self, cliente_mock, _sleep):
        with self.assertRaises(ValueError):
            self._interpretar(cliente_mock, respuesta_con(pais=""))

    def test_presupuesto_cero_o_negativo_queda_en_none(self, cliente_mock, _sleep):
        self.assertIsNone(
            self._interpretar(cliente_mock, respuesta_con(presupuesto_max_noche=0)
                              ).presupuesto_max_noche
        )
        self.assertIsNone(
            self._interpretar(cliente_mock, respuesta_con(presupuesto_max_noche=-10)
                              ).presupuesto_max_noche
        )

    def test_sin_presupuesto_ni_preferencias_queda_sin_requisitos(self, cliente_mock, _sleep):
        espec = self._interpretar(cliente_mock, respuesta_con(
            presupuesto_max_noche=None,
            preferencias="   ",
        ))

        self.assertIsNone(espec.presupuesto_max_noche)
        self.assertEqual(espec.preferencias, "")
        self.assertFalse(espec.tiene_requisitos())


if __name__ == "__main__":
    unittest.main()

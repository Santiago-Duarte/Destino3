import json
import unittest
from datetime import date
from unittest.mock import Mock, patch

from src.models.busqueda import EspecificacionBusqueda
from src.models.interpretacion import InterpretacionFrase
from src.services.interpretador_ia import InterpretadorIA

FRASE = "quiero hoteles en Medellin, Colombia hasta 100 USD cerca del metro"


def respuesta_con(**campos) -> Mock:
    datos = {
        "ciudad": "Medellin",
        "pais": "Colombia",
        "fecha_entrada": "2026-12-04",
        "fecha_salida": "2026-12-06",
        "adultos": 2,
        "ninos": 1,
        "mascotas": True,
        "presupuesto_max_noche": 100,
        "preferencias": "cerca del metro",
        "max_distancia_km": None,
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
        self.assertIs(llamada.kwargs["config"].response_schema, InterpretacionFrase)

    def test_extrae_fechas_y_ocupacion(self, cliente_mock, _sleep):
        espec = self._interpretar(cliente_mock, respuesta_con())

        self.assertEqual(espec.fecha_entrada, date(2026, 12, 4))
        self.assertEqual(espec.fecha_salida, date(2026, 12, 6))
        self.assertEqual(espec.adultos, 2)
        self.assertEqual(espec.ninos, 1)
        self.assertTrue(espec.mascotas)
        self.assertEqual(espec.noches(), 2)

    def test_el_prompt_incluye_la_fecha_de_hoy_para_inferir_el_ano(self, cliente_mock, _sleep):
        self._interpretar(cliente_mock, respuesta_con())

        llamada = cliente_mock.return_value.models.generate_content.call_args
        self.assertIn(date.today().isoformat(), llamada.kwargs["contents"])

    def test_mascotas_false_se_conserva(self, cliente_mock, _sleep):
        espec = self._interpretar(cliente_mock, respuesta_con(mascotas=False))

        self.assertFalse(espec.mascotas)

    def test_datos_ausentes_quedan_en_none(self, cliente_mock, _sleep):
        espec = self._interpretar(cliente_mock, respuesta_con(
            fecha_entrada=None,
            fecha_salida=None,
            adultos=None,
            ninos=None,
            mascotas=None,
        ))

        self.assertIsNone(espec.fecha_entrada)
        self.assertIsNone(espec.fecha_salida)
        self.assertIsNone(espec.adultos)
        self.assertIsNone(espec.ninos)
        self.assertIsNone(espec.mascotas)

    def test_fecha_invalida_queda_en_none(self, cliente_mock, _sleep):
        espec = self._interpretar(cliente_mock, respuesta_con(
            fecha_entrada="04/12/2026",
        ))

        self.assertIsNone(espec.fecha_entrada)
        self.assertEqual(espec.fecha_salida, date(2026, 12, 6))

    def test_ocupacion_invalida_queda_en_none(self, cliente_mock, _sleep):
        espec = self._interpretar(cliente_mock, respuesta_con(adultos=0, ninos=-1))

        self.assertIsNone(espec.adultos)
        self.assertIsNone(espec.ninos)

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

    def test_extrae_la_distancia_maxima(self, cliente_mock, _sleep):
        espec = self._interpretar(cliente_mock, respuesta_con(max_distancia_km=1.5))

        self.assertEqual(espec.max_distancia_km, 1.5)
        self.assertTrue(espec.tiene_requisitos())

    def test_distancia_maxima_cero_o_negativa_queda_en_none(self, cliente_mock, _sleep):
        self.assertIsNone(
            self._interpretar(cliente_mock, respuesta_con(max_distancia_km=0)
                              ).max_distancia_km
        )
        self.assertIsNone(
            self._interpretar(cliente_mock, respuesta_con(max_distancia_km=-2)
                              ).max_distancia_km
        )



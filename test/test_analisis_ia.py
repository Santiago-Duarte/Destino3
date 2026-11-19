import unittest

from pydantic import ValidationError

from src.models.analisis_ia import (
    AnalisisIAOutput,
    LoteAnalisisIA,
    LotePuntuacionesIA,
    PuntuacionIAOutput,
)
from src.models.busqueda import EspecificacionBusqueda

JSON_ANALISIS_VALIDO = """
{
  "analisis": [
    {
      "hospedaje_id": 7,
      "resumen_ejecutivo": "Buena relación calidad-precio.",
      "puntos_fuertes": "Cerca del centro; desayuno incluido.",
      "puntos_debiles": "Habitaciones pequeñas."
    },
    {
      "hospedaje_id": 8,
      "resumen_ejecutivo": "Opción económica.",
      "puntos_fuertes": "Precio bajo.",
      "puntos_debiles": "Sin reseñas."
    }
  ]
}
"""

JSON_ANALISIS_SIN_CAMPO = """
{
  "analisis": [
    {
      "hospedaje_id": 7,
      "resumen_ejecutivo": "Resumen.",
      "puntos_fuertes": "Fuertes."
    }
  ]
}
"""

JSON_PUNTUACION_VALIDA = """
{
  "puntuaciones": [
    {
      "hospedaje_id": 7,
      "score_calidad": 8,
      "score_cumplimiento": 9,
      "requisitos_cumplidos": ["presupuesto hasta 100 USD"],
      "requisitos_faltantes": ["cerca del metro"]
    }
  ]
}
"""

JSON_SCORE_FUERA_DE_RANGO = """
{
  "puntuaciones": [
    {
      "hospedaje_id": 7,
      "score_calidad": 11,
      "score_cumplimiento": 9,
      "requisitos_cumplidos": [],
      "requisitos_faltantes": []
    }
  ]
}
"""

JSON_SCORE_TIPO_INCORRECTO = """
{
  "puntuaciones": [
    {
      "hospedaje_id": 7,
      "score_calidad": "8",
      "score_cumplimiento": 9,
      "requisitos_cumplidos": [],
      "requisitos_faltantes": []
    }
  ]
}
"""


class TestLoteAnalisisIA(unittest.TestCase):

    def test_parsea_el_lote_y_expone_los_ids_recibidos(self):
        lote = LoteAnalisisIA.model_validate_json(JSON_ANALISIS_VALIDO)

        self.assertEqual(len(lote), 2)
        self.assertEqual(lote.hospedaje_ids(), {7, 8})
        self.assertEqual(lote.analisis[0].resumen_ejecutivo, "Buena relación calidad-precio.")

    def test_un_analisis_sin_puntos_debiles_lanza_validation_error(self):
        with self.assertRaises(ValidationError):
            LoteAnalisisIA.model_validate_json(JSON_ANALISIS_SIN_CAMPO)

    def test_el_contrato_no_tiene_score_porque_no_se_persiste(self):
        self.assertNotIn("score_calidad_precio", AnalisisIAOutput.model_fields)


class TestLotePuntuacionesIA(unittest.TestCase):

    def test_parsea_la_puntuacion_con_sus_requisitos(self):
        lote = LotePuntuacionesIA.model_validate_json(JSON_PUNTUACION_VALIDA)

        puntuacion = lote.puntuaciones[0]
        self.assertEqual(lote.hospedaje_ids(), {7})
        self.assertEqual(puntuacion.score_calidad, 8)
        self.assertEqual(puntuacion.score_cumplimiento, 9)
        self.assertEqual(puntuacion.requisitos_cumplidos, ["presupuesto hasta 100 USD"])
        self.assertEqual(puntuacion.requisitos_faltantes, ["cerca del metro"])

    def test_score_fuera_del_rango_lanza_validation_error(self):
        with self.assertRaises(ValidationError):
            LotePuntuacionesIA.model_validate_json(JSON_SCORE_FUERA_DE_RANGO)

    def test_score_con_tipo_incorrecto_lanza_validation_error(self):
        with self.assertRaises(ValidationError):
            LotePuntuacionesIA.model_validate_json(JSON_SCORE_TIPO_INCORRECTO)

    def test_los_lotes_deben_poder_centrarse_por_id_de_hospedaje(self):
        puntuacion = PuntuacionIAOutput(
            hospedaje_id=1, score_calidad=1, score_cumplimiento=10
        )

        self.assertEqual(puntuacion.score_calidad, 1)
        self.assertEqual(puntuacion.score_cumplimiento, 10)


class TestEspecificacionBusqueda(unittest.TestCase):

    def test_sin_campos_no_tiene_requisitos(self):
        espec = EspecificacionBusqueda()

        self.assertEqual(espec.tiene_requisitos(), False)

    def test_con_presupuesto_o_preferencias_tiene_requisitos(self):
        self.assertTrue(
            EspecificacionBusqueda(presupuesto_max_noche=100).tiene_requisitos()
        )
        self.assertTrue(
            EspecificacionBusqueda(preferencias="cerca del metro").tiene_requisitos()
        )


if __name__ == "__main__":
    unittest.main()

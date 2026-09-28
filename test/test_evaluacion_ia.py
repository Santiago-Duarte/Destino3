import unittest

from pydantic import ValidationError

from src.models.evaluacion_ia import EvaluacionIAOutput, LoteEvaluacionesIA

JSON_VALIDO = """
{
  "evaluaciones": [
    {
      "id_temporal": 1,
      "resumen_ejecutivo": "Buena relación calidad-precio.",
      "puntos_fuertes": "Cerca del centro, desayuno incluido.",
      "puntos_debiles": "Habitaciones pequeñas.",
      "score_calidad_precio": 8
    },
    {
      "id_temporal": 2,
      "resumen_ejecutivo": "Opción económica.",
      "puntos_fuertes": "Precio bajo.",
      "puntos_debiles": "Sin reseñas.",
      "score_calidad_precio": 6
    }
  ]
}
"""


JSON_SCORE_FUERA_DE_RANGO = """
{
  "evaluaciones": [
    {
      "id_temporal": 1,
      "resumen_ejecutivo": "Resumen.",
      "puntos_fuertes": "Fuertes.",
      "puntos_debiles": "Debiles.",
      "score_calidad_precio": 11
    }
  ]
}
"""

JSON_SCORE_TIPO_INCORRECTO = """
{
  "evaluaciones": [
    {
      "id_temporal": 1,
      "resumen_ejecutivo": "Resumen.",
      "puntos_fuertes": "Fuertes.",
      "puntos_debiles": "Debiles.",
      "score_calidad_precio": "8"
    }
  ]
}
"""




class TestLoteEvaluacionesIA(unittest.TestCase):

    def test_respuesta_valida_parsea_todas_las_evaluaciones(self):
        lote = LoteEvaluacionesIA.model_validate_json(JSON_VALIDO)

        self.assertEqual(len(lote.evaluaciones), 2)
        primera = lote.evaluaciones[0]
        self.assertEqual(primera.id_temporal, 1)
        self.assertEqual(primera.resumen_ejecutivo, "Buena relación calidad-precio.")
        self.assertEqual(primera.puntos_fuertes, "Cerca del centro, desayuno incluido.")
        self.assertEqual(primera.puntos_debiles, "Habitaciones pequeñas.")
        self.assertEqual(primera.score_calidad_precio, 8)

    def test_score_fuera_del_rango_lanza_validation_error(self):
        with self.assertRaises(ValidationError):
            LoteEvaluacionesIA.model_validate_json(JSON_SCORE_FUERA_DE_RANGO)

    def test_score_con_tipo_incorrecto_lanza_validation_error(self):
        with self.assertRaises(ValidationError):
            LoteEvaluacionesIA.model_validate_json(JSON_SCORE_TIPO_INCORRECTO)



class TestEvaluacionIAOutput(unittest.TestCase):

    def test_puntaje_minimo_y_maximo_se_aceptan(self):
        base = {
            "id_temporal": 1,
            "resumen_ejecutivo": "Resumen.",
            "puntos_fuertes": "Fuertes.",
            "puntos_debiles": "Debiles.",
        }

        minima = EvaluacionIAOutput(score_calidad_precio=1, **base)
        maxima = EvaluacionIAOutput(score_calidad_precio=10, **base)

        self.assertEqual(minima.score_calidad_precio, 1)
        self.assertEqual(maxima.score_calidad_precio, 10)


class TestSinDuplicacion(unittest.TestCase):
    """El contrato de la IA vive una sola vez, en src/models/evaluacion_ia.py."""

    def test_el_servicio_reutiliza_el_dto_del_dominio(self):
        from src.services import ai_evaluator

        self.assertIs(ai_evaluator.EvaluacionIAOutput, EvaluacionIAOutput)

    def test_el_servicio_no_define_su_propio_contenedor_de_lote(self):
        from src.services import ai_evaluator

        self.assertFalse(hasattr(ai_evaluator, "Top3Evaluaciones"))

    def test_el_orquestador_no_importa_dtos_desde_el_servicio(self):
        from src.orchestrator import evaluacion_orchestrator

        self.assertFalse(hasattr(evaluacion_orchestrator, "Top3Evaluaciones"))

    def test_la_clave_de_la_respuesta_de_ia_es_evaluaciones(self):
        propiedades = set(LoteEvaluacionesIA.model_json_schema()["properties"])

        self.assertEqual(propiedades, {"evaluaciones"})


if __name__ == "__main__":
    unittest.main()

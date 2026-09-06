import unittest
from psycopg2 import errors
from test.db_test_case import BaseDBTestCase
from src.repositories.evaluaciones_repository import EvaluacionesRepository
from src.services.ai_evaluator import EvaluacionIAOutput


class TestEvaluacionesRepository(BaseDBTestCase):

    def setUp(self):
        super().setUp()
        self.repo = EvaluacionesRepository()

    def test_guardar_y_recuperar_evaluacion(self):
        destino_id = self.crear_destino()
        hospedaje_id = self.crear_hospedaje(destino_id)

        evaluacion = EvaluacionIAOutput(
            id_temporal=1,
            resumen_ejecutivo="Excelente opción cerca al centro",
            puntos_fuertes="Ubicación céntrica, desayuno incluido",
            puntos_debiles="Ruido nocturno",
            score_calidad_precio=8,
        )

        evaluacion_id = self.repo.guardar(evaluacion, hospedaje_id)
        self.assertIsNotNone(evaluacion_id)

        recuperada = self.repo.obtener_por_hospedaje(hospedaje_id)
        self.assertIsNotNone(recuperada)
        self.assertEqual(recuperada.resumen_ejecutivo, "Excelente opción cerca al centro")
        self.assertEqual(recuperada.puntos_fuertes, "Ubicación céntrica, desayuno incluido")
        self.assertEqual(recuperada.puntos_debiles, "Ruido nocturno")
        self.assertEqual(recuperada.score_calidad_precio, 8)

    def test_duplicar_evaluacion_mismo_hospedaje_falla(self):
        destino_id = self.crear_destino()
        hospedaje_id = self.crear_hospedaje(destino_id)

        evaluacion = EvaluacionIAOutput(
            id_temporal=1,
            resumen_ejecutivo="Primera evaluación",
            puntos_fuertes="Puntos fuertes",
            puntos_debiles="Puntos débiles",
            score_calidad_precio=7,
        )

        self.repo.guardar(evaluacion, hospedaje_id)

        evaluacion_duplicada = EvaluacionIAOutput(
            id_temporal=2,
            resumen_ejecutivo="Segunda evaluación",
            puntos_fuertes="Otros puntos fuertes",
            puntos_debiles="Otros puntos débiles",
            score_calidad_precio=9,
        )

        with self.assertRaises(errors.UniqueViolation):
            self.repo.guardar(evaluacion_duplicada, hospedaje_id)


if __name__ == "__main__":
    unittest.main()

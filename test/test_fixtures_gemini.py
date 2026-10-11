import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from src.models.evaluacion_ia import LoteEvaluacionesIA


RUTA_FIXTURES = Path(__file__).parent / "fixtures"


class TestFixturesGemini(unittest.TestCase):

    def cargar_json(self, nombre: str) -> str:
        return (RUTA_FIXTURES / nombre).read_text(encoding="utf-8")

    def test_respuesta_valida_pasa_validacion_del_lote(self):
        respuesta = LoteEvaluacionesIA.model_validate_json(
            self.cargar_json("gemini_respuesta_valida.json")
        )

        self.assertEqual(len(respuesta.evaluaciones), 3)

    def test_respuesta_invalida_lanza_validation_error(self):
        with self.assertRaises(ValidationError):
            LoteEvaluacionesIA.model_validate_json(
                self.cargar_json("gemini_respuesta_invalida.json")
            )

if __name__ == "__main__":
    unittest.main()

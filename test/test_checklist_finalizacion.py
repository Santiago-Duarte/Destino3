import unittest
from pathlib import Path


ROOT = Path(__file__).parent


class TestChecklistFinalizacion(unittest.TestCase):
    """G10: cada escenario mínimo tiene una prueba identificable."""

    CASOS = {
        "hospedaje completo": ("test_fixtures_serpapi.py", "test_fixture_hospedaje_completo"),
        "hospedaje sin reseñas": ("test_evaluador_ia.py", "test_hospedaje_sin_resenas"),
        "respuesta IA válida": ("test_fixtures_gemini.py", "test_respuesta_valida"),
        "respuesta IA inválida": ("test_fixtures_gemini.py", "test_respuesta_invalida"),
        "límite 429": ("test_buscador_serpapi.py", "test_429_se_recupera"),
        "agotamiento de reintentos": ("test_evaluador_ia.py", "test_respuesta_invalida_agota_reintentos"),
        "sin resultados": ("test_orquestador_integracion.py", "test_properties_vacias"),
        "límite de paginación": ("test_buscador_serpapi.py", "test_max_pages_corta"),
    }

    def test_cada_caso_minimo_tiene_prueba(self):
        for caso, (archivo, nombre_test) in self.CASOS.items():
            with self.subTest(caso=caso):
                fuente = (ROOT / archivo).read_text(encoding="utf-8")
                self.assertIn(nombre_test, fuente)


if __name__ == "__main__":
    unittest.main()

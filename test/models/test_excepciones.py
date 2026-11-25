import unittest

from src.exceptions import (
    Destino3Error,
    GeminiError,
    LoteIAError,
    PersistenciaError,
    SerpApiError,
)


class TestExcepcionesPersonalizadas(unittest.TestCase):

    def test_jerarquia_y_contexto_de_excepciones(self):
        error = SerpApiError("consulta", "sin conexión")

        self.assertIsInstance(error, Destino3Error)
        self.assertEqual(error.proveedor, "SerpAPI")
        self.assertEqual(error.operacion, "consulta")
        self.assertEqual(error.detalle, "sin conexión")
        self.assertIn("SerpAPI", str(error))
        self.assertIn("consulta", str(error))
        self.assertIsInstance(LoteIAError("analizar", "falló"), GeminiError)
        self.assertIsInstance(PersistenciaError("PostgreSQL", "guardar", "falló"), Destino3Error)
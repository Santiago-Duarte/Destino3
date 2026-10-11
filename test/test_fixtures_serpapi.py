import json
import unittest
from pathlib import Path


RUTA_FIXTURES = Path(__file__).parent / "fixtures"


class TestFixturesSerpapi(unittest.TestCase):

    def cargar(self, nombre: str) -> dict:
        with (RUTA_FIXTURES / nombre).open(encoding="utf-8") as archivo:
            return json.load(archivo)

    def test_las_fixtures_requeridas_cargan_como_json(self):
        nombres = (
            "hospedaje_completo.json",
            "hospedaje_sin_resenas.json",
            "serpapi_rate_limit_429.json",
            "serpapi_paginacion_multiple.json",
            "busqueda_sin_resultados.json",
        )

        for nombre in nombres:
            with self.subTest(nombre=nombre):
                self.assertIsInstance(self.cargar(nombre), dict)

    def test_fixture_hospedaje_completo_contiene_claves_consumidas(self):
        respuesta = self.cargar("hospedaje_completo.json")
        propiedad = respuesta["properties"][0]

        self.assertIn("search_parameters", respuesta)
        self.assertIn("properties", respuesta)
        self.assertIn("name", propiedad)
        self.assertIn("property_token", propiedad)
        self.assertIn("rate_per_night", propiedad)
        self.assertIn("extracted_lowest", propiedad["rate_per_night"])
        self.assertIn("overall_rating", propiedad)
        self.assertIn("description", propiedad)
        self.assertIn("link", propiedad)
        self.assertIn("reviews", propiedad)
        self.assertIn("amenities", propiedad)

    def test_fixture_sin_resenas_omite_datos_opcionales_de_resenas(self):
        respuesta = self.cargar("hospedaje_sin_resenas.json")
        propiedad = respuesta["properties"][0]

        self.assertIn("search_parameters", respuesta)
        self.assertIn("properties", respuesta)
        self.assertIn("name", propiedad)
        self.assertIn("rate_per_night", propiedad)
        self.assertNotIn("reviews", propiedad)
        self.assertNotIn("overall_rating", propiedad)

    def test_fixture_429_contiene_status_headers_y_body(self):
        respuesta = self.cargar("serpapi_rate_limit_429.json")

        self.assertEqual(respuesta["status_code"], 429)
        self.assertIn("Retry-After", respuesta["headers"])
        self.assertIsInstance(respuesta["body"], dict)

    def test_fixture_paginacion_contiene_token_de_siguiente_pagina(self):
        respuesta = self.cargar("serpapi_paginacion_multiple.json")

        self.assertIn("properties", respuesta)
        self.assertIn("serpapi_pagination", respuesta)
        self.assertTrue(respuesta["serpapi_pagination"]["next_page_token"])

    def test_fixture_sin_resultados_contiene_properties_vacias(self):
        respuesta = self.cargar("busqueda_sin_resultados.json")

        self.assertIn("search_parameters", respuesta)
        self.assertEqual(respuesta["properties"], [])


if __name__ == "__main__":
    unittest.main()

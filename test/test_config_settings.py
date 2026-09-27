import importlib
import os
import unittest

from src.config import settings

VARIABLES = [
    "SERPAPI_KEY",
    "GEMINI_API_KEY",
    "SERPAPI_TIMEOUT",
    "SERPAPI_MAX_PAGES",
    "SERPAPI_MAX_RESULTS",
    "SERPAPI_RATE_LIMIT_RPS",
    "SERPAPI_MAX_REINTENTOS",
    "SERPAPI_BACKOFF_BASE",
    "GEMINI_TIMEOUT",
    "GEMINI_MAX_REINTENTOS",
    "GEMINI_BACKOFF_BASE",
]


class TestSettings(unittest.TestCase):

    def recargar(self, **extras):
        anteriores = {nombre: os.environ.pop(nombre, None) for nombre in VARIABLES}
        os.environ.update(extras)
        importlib.reload(settings)

        def restaurar():
            for nombre, valor in anteriores.items():
                if valor is None:
                    os.environ.pop(nombre, None)
                else:
                    os.environ[nombre] = valor
            importlib.reload(settings)

        self.addCleanup(restaurar)

    def test_valores_por_defecto(self):
        self.recargar()

        self.assertEqual(settings.SERPAPI_TIMEOUT, 15.0)
        self.assertEqual(settings.SERPAPI_MAX_PAGES, 5)
        self.assertEqual(settings.SERPAPI_MAX_RESULTS, 20)
        self.assertEqual(settings.SERPAPI_RATE_LIMIT_RPS, 1.0)
        self.assertEqual(settings.SERPAPI_MAX_REINTENTOS, 3)
        self.assertEqual(settings.SERPAPI_BACKOFF_BASE, 0.5)
        self.assertEqual(settings.GEMINI_TIMEOUT, 60.0)
        self.assertEqual(settings.GEMINI_MAX_REINTENTOS, 3)
        self.assertEqual(settings.GEMINI_BACKOFF_BASE, 1.0)

    def test_lee_parametros_desde_variables_de_entorno(self):
        self.recargar(
            SERPAPI_TIMEOUT="5",
            SERPAPI_MAX_PAGES="2",
            SERPAPI_MAX_RESULTS="7",
            SERPAPI_RATE_LIMIT_RPS="0.5",
            SERPAPI_MAX_REINTENTOS="4",
            GEMINI_MAX_REINTENTOS="2",
        )

        self.assertEqual(settings.SERPAPI_TIMEOUT, 5.0)
        self.assertEqual(settings.SERPAPI_MAX_PAGES, 2)
        self.assertEqual(settings.SERPAPI_MAX_RESULTS, 7)
        self.assertEqual(settings.SERPAPI_RATE_LIMIT_RPS, 0.5)
        self.assertEqual(settings.SERPAPI_MAX_REINTENTOS, 4)
        self.assertEqual(settings.GEMINI_MAX_REINTENTOS, 2)

    def test_valor_no_numerico_usa_el_valor_por_defecto(self):
        self.recargar(SERPAPI_MAX_PAGES="abc", SERPAPI_TIMEOUT="")

        self.assertEqual(settings.SERPAPI_MAX_PAGES, 5)
        self.assertEqual(settings.SERPAPI_TIMEOUT, 15.0)

    def test_expone_las_claves_de_los_proveedores(self):
        self.recargar(SERPAPI_KEY="clave-serpapi", GEMINI_API_KEY="clave-gemini")

        self.assertEqual(settings.SERPAPI_KEY, "clave-serpapi")
        self.assertEqual(settings.GEMINI_API_KEY, "clave-gemini")

    def test_los_parametros_no_estan_hardcodeados_en_el_codigo(self):
        fuente = open(settings.__file__, encoding="utf-8").read()

        self.assertIn("os.getenv", fuente)
        self.assertNotIn("print(", fuente)


if __name__ == "__main__":
    unittest.main()

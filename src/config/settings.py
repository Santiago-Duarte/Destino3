import os

# src/config/__init__.py carga el .env antes de importar este módulo.


def _leer_variable(nombre: str, defecto: str = "") -> str:
    valor = os.getenv(nombre)
    if valor is None or valor.strip() == "":
        return defecto
    return valor


# Nunca registrar credenciales.
SERPAPI_KEY = _leer_variable("SERPAPI_KEY")
GEMINI_API_KEY = _leer_variable("GEMINI_API_KEY")

SERPAPI_TIMEOUT = 15.0
SERPAPI_MAX_PAGES = 5
SERPAPI_MAX_RESULTS = 20
SERPAPI_RATE_LIMIT_RPS = 1.0
SERPAPI_MAX_REINTENTOS = 3
SERPAPI_BACKOFF_BASE = 0.5

GEMINI_TIMEOUT = 60.0
GEMINI_MAX_REINTENTOS = 3
GEMINI_BACKOFF_BASE = 1.0

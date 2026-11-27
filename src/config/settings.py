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
# Una página de Google Hotels ronda los 20 resultados. El MVP lee una sola
# página para acotar costo y latencia; para paginar hay que subir
# SERPAPI_MAX_PAGES y SERPAPI_MAX_RESULTS de forma conjunta.
SERPAPI_MAX_PAGES = 1
SERPAPI_MAX_RESULTS = 20
SERPAPI_RATE_LIMIT_RPS = 1.0
SERPAPI_MAX_REINTENTOS = 3
SERPAPI_BACKOFF_BASE = 0.5

GEMINI_MODELO = "gemini-3.6-flash"
GEMINI_TIMEOUT = 60.0
GEMINI_MAX_REINTENTOS = 3
GEMINI_BACKOFF_BASE = 1.0
GEMINI_TEMPERATURA = 0.2

MAX_CANDIDATOS_IA = 10
TOP_RESULTADOS = 3
SCORE_CUMPLIMIENTO_MINIMO = 7
# Súbelo cuando cambie el prompt de análisis: los análisis guardados con una
# versión anterior se ignoran y se regeneran en la siguiente búsqueda.
ANALISIS_VERSION = 1

# Geocodificación del centro del destino con Nominatim (OpenStreetMap).
# La política de uso exige un User-Agent identificable y como máximo 1 req/s.
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_TIMEOUT = 10.0
NOMINATIM_RATE_LIMIT_RPS = 1.0
NOMINATIM_USER_AGENT = "Destino3/1.0 (herramienta personal de búsqueda de hoteles)"

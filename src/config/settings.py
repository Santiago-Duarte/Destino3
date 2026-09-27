import os

# src/config/__init__.py carga el .env antes de que este módulo se importe.

def _leer_texto(nombre: str, defecto: str = "") -> str:
    valor = os.getenv(nombre)
    if valor is None or valor.strip() == "":
        return defecto
    return valor


def _leer_entero(nombre: str, defecto: int) -> int:
    try:
        return int(_leer_texto(nombre, str(defecto)))
    except ValueError:
        return defecto

def _leer_decimal(nombre: str, defecto: float) -> float:
    try:
        return float(_leer_texto(nombre, str(defecto)))
    except ValueError:
        return defecto


# Proveedores externos (nunca registrar estos valores)
SERPAPI_KEY = _leer_texto("SERPAPI_KEY")
GEMINI_API_KEY = _leer_texto("GEMINI_API_KEY")

# SerpAPI: tiempos, límites operativos y política de reintentos
SERPAPI_TIMEOUT = _leer_decimal("SERPAPI_TIMEOUT", 15.0)
SERPAPI_MAX_PAGES = _leer_entero("SERPAPI_MAX_PAGES", 5)
SERPAPI_MAX_RESULTS = _leer_entero("SERPAPI_MAX_RESULTS", 20)
SERPAPI_RATE_LIMIT_RPS = _leer_decimal("SERPAPI_RATE_LIMIT_RPS", 1.0)
SERPAPI_MAX_REINTENTOS = _leer_entero("SERPAPI_MAX_REINTENTOS", 3)
SERPAPI_BACKOFF_BASE = _leer_decimal("SERPAPI_BACKOFF_BASE", 0.5)

# Gemini: tiempos y política de reintentos
GEMINI_TIMEOUT = _leer_decimal("GEMINI_TIMEOUT", 60.0)
GEMINI_MAX_REINTENTOS = _leer_entero("GEMINI_MAX_REINTENTOS", 3)
GEMINI_BACKOFF_BASE = _leer_decimal("GEMINI_BACKOFF_BASE", 1.0)

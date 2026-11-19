from google import genai

from src.config import settings
from src.models.busqueda import EspecificacionBusqueda
from src.services import gemini


def _prompt_frase(frase: str) -> str:
    return f"""
                Extrae la búsqueda de hoteles que pide esta frase: "{frase}"

                Devuelve JSON con:
                - `ciudad`: lugar exacto que se busca; cadena vacía si la frase no lo indica.
                - `pais`: país de ese lugar; infiérelo solo si estás seguro de la ciudad, si no deja la cadena vacía.
                - `presupuesto_max_noche`: presupuesto máximo en USD por noche, como número; null si no se indica.
                - `preferencias`: requisitos adicionales en texto corto; cadena vacía si no hay.

                No inventes la ciudad ni el país.
                """


class InterpretadorIA:

    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise ValueError("Falta la credencial del proveedor de IA")
        self._cliente = genai.Client(api_key=settings.GEMINI_API_KEY)

    def interpretar(self, frase: str) -> EspecificacionBusqueda:
        espec = gemini.generar(
            self._cliente,
            _prompt_frase(frase),
            EspecificacionBusqueda,
            "interpretar_frase",
        )

        if not espec.ciudad.strip() or not espec.pais.strip():
            raise ValueError("La frase no indica la ciudad o el país de la búsqueda.")

        espec.ciudad = espec.ciudad.strip()
        espec.pais = espec.pais.strip()
        espec.preferencias = espec.preferencias.strip()
        if espec.presupuesto_max_noche is not None and espec.presupuesto_max_noche <= 0:
            espec.presupuesto_max_noche = None
        return espec

import json

from google import genai

from src.config import settings
from src.models.analisis import Analisis
from src.models.analisis_ia import LoteAnalisisIA, LotePuntuacionesIA
from src.models.busqueda import EspecificacionBusqueda
from src.models.hospedaje import Hospedaje
from src.services import gemini

MAX_CANDIDATOS_IA = 10


def preseleccionar_candidatos(
        hospedajes: list[Hospedaje],
        presupuesto_maximo_noche: float,
) -> list[Hospedaje]:
    en_presupuesto = [
        hospedaje
        for hospedaje in hospedajes
        if hospedaje.precio_noche is not None
        and hospedaje.precio_noche <= presupuesto_maximo_noche
    ]

    return sorted(
        en_presupuesto,
        key=lambda hospedaje: (-(hospedaje.calificacion or 0), hospedaje.precio_noche),
    )[:MAX_CANDIDATOS_IA]


def _resumen_de(hospedaje: Hospedaje) -> dict:
    return {
        "hospedaje_id": hospedaje.id,
        "nombre": hospedaje.nombre,
        "precio_noche": hospedaje.precio_noche,
        "calificacion": hospedaje.calificacion,
        "direccion": hospedaje.direccion,
        "url_reserva": hospedaje.url_reserva,
    }


def _prompt_analisis(resumen_candidatos: list[dict]) -> str:
    return f"""
                Eres experto en alojamientos. Analiza cada hotel de este JSON:
                {json.dumps(resumen_candidatos, ensure_ascii=False, indent=4)}

                Instrucciones:
                1. Describe únicamente características objetivas del alojamiento: no evalúes si sirve o no para quien lo busca.
                2. Responde con exactamente un elemento por cada `hospedaje_id` recibido; no inventes ni omitas ids.
                3. `resumen_ejecutivo` en una sola frase; `puntos_fuertes` y `puntos_debiles` como hechos separados por punto y coma.
                """


def _prompt_puntuacion(resumen_candidatos: list[dict], espec: EspecificacionBusqueda) -> str:
    presupuesto = (
        f"USD ${espec.presupuesto_max_noche:g} por noche"
        if espec.presupuesto_max_noche is not None
        else "Sin límite declarado"
    )
    preferencias = espec.preferencias.strip() or "Ninguna especificada"
    return f"""
                Eres un asistente experto en viajes. Puntúa los hoteles de este JSON según lo que pide esta persona:
                {json.dumps(resumen_candidatos, ensure_ascii=False, indent=4)}

                Especificaciones del usuario:
                - Destino: {espec.ciudad}, {espec.pais}
                - Presupuesto máximo: {presupuesto}
                - Preferencias: {preferencias}

                Instrucciones:
                1. Responde con exactamente un elemento por cada `hospedaje_id` recibido; no inventes ni omitas ids.
                2. `score_calidad`: calidad intrínseca del alojamiento del 1 al 10, sin mirar las preferencias.
                3. `score_cumplimiento`: qué tan bien cumple las especificaciones del usuario, del 1 al 10 (1=no cumple, 10=las cumple todas).
                4. `requisitos_cumplidos` y `requisitos_faltantes`: textos cortos tomados de las especificaciones, por ejemplo "presupuesto hasta 100 USD" o "cerca del metro". Un hotel que sí cumple debe aparecer en `requisitos_cumplidos`.
                5. Cuando el hotel traiga un `analisis` previo, úsalo para responder; no uses información que no esté en los datos de entrada.
                """


class EvaluadorIA:

    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise ValueError("Falta la credencial del proveedor de IA")
        self._cliente = genai.Client(api_key=settings.GEMINI_API_KEY)

    def analizar(self, hospedajes: list[Hospedaje]) -> LoteAnalisisIA:
        """Descripción intrínseca de los candidatos; se persiste y se reutiliza."""
        return gemini.generar(
            self._cliente,
            _prompt_analisis([_resumen_de(hospedaje) for hospedaje in hospedajes]),
            LoteAnalisisIA,
            "analizar",
            hospedaje_ids={hospedaje.id for hospedaje in hospedajes},
        )

    def puntuar(
            self,
            hospedajes: list[Hospedaje],
            analisis: dict[int, Analisis],
            espec: EspecificacionBusqueda,
    ) -> LotePuntuacionesIA:
        """Doble score contra lo que pidió esta persona; no se persiste."""
        candidatos = []
        for hospedaje in hospedajes:
            resumen = _resumen_de(hospedaje)
            analisis_previo = analisis.get(hospedaje.id)
            if analisis_previo is not None:
                resumen["analisis"] = {
                    "resumen_ejecutivo": analisis_previo.resumen_ejecutivo,
                    "puntos_fuertes": analisis_previo.puntos_fuertes,
                    "puntos_debiles": analisis_previo.puntos_debiles,
                }
            candidatos.append(resumen)

        return gemini.generar(
            self._cliente,
            _prompt_puntuacion(candidatos, espec),
            LotePuntuacionesIA,
            "puntuar",
            hospedaje_ids={hospedaje.id for hospedaje in hospedajes},
        )

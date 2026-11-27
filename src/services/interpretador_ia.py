import logging
from datetime import date

from src.models.busqueda import EspecificacionBusqueda
from src.models.interpretacion import InterpretacionFrase
from src.services import gemini

logger = logging.getLogger(__name__)


def _prompt_frase(frase: str, hoy: date) -> str:
    return f"""
                Hoy es {hoy.isoformat()}.
                Extrae la búsqueda de hoteles que pide esta frase: "{frase}"

                Devuelve JSON con:
                - `ciudad`: lugar exacto que se busca; cadena vacía si la frase no lo indica.
                - `pais`: país de ese lugar; infiérelo solo si estás seguro de la ciudad, si no deja la cadena vacía.
                - `fecha_entrada`: fecha de entrada en formato YYYY-MM-DD; null si no se indica.
                - `fecha_salida`: fecha de salida en formato YYYY-MM-DD; null si no se indica.
                - `adultos`: número de adultos; null si no se indica.
                - `ninos`: número de niños; null si no se indica.
                - `mascotas`: true si viaja con mascotas, false si dice que no, null si no se menciona.
                - `presupuesto_max_noche`: presupuesto máximo en USD por noche, como número; null si no se indica.
                - `preferencias`: requisitos adicionales en texto corto; cadena vacía si no hay.
                - `max_distancia_km`: si la frase pide una distancia máxima (por ejemplo "a menos de 1 km" o "a máximo 2 km"), el número en kilómetros; null si no se indica.
                - `punto_referencia`: si la frase menciona un lugar específico al que quiere estar cerca (ej. "cerca del metro", "cerca del aeropuerto", "cerca de la playa El Rodadero", "cerca del centro comercial Santafé", "zona Poblado"), ese texto tal cual; null si no se indica.

                Reglas de fechas:
                - Si la frase da día y mes sin año, usa el año de hoy; si esa fecha ya pasó, usa el año siguiente.
                - Si la fecha es relativa ("el próximo fin de semana", "en dos semanas"), deja null: el programa la pedirá.
                - No inventes fechas que la frase no mencione.

                No inventes ciudad, país ni ocupación: si el dato no está en la frase, usa null.
                """


def _fecha(valor: str | None) -> date | None:
    if not valor:
        return None
    try:
        return date.fromisoformat(valor.strip())
    except ValueError:
        logger.warning("El interpretador devolvió una fecha inválida: %r", valor)
        return None


def _entero(valor: int | None, minimo: int) -> int | None:
    if valor is None or valor < minimo:
        return None
    return valor


class InterpretadorIA:

    def __init__(self) -> None:
        self._cliente = gemini.crear_cliente()

    def interpretar(self, frase: str, hoy: date | None = None) -> EspecificacionBusqueda:
        datos = gemini.generar(
            self._cliente,
            _prompt_frase(frase, hoy or date.today()),
            InterpretacionFrase,
            "interpretar_frase",
        )

        if not datos.ciudad.strip() or not datos.pais.strip():
            raise ValueError("La frase no indica la ciudad o el país de la búsqueda.")

        espec = EspecificacionBusqueda(
            ciudad=datos.ciudad.strip(),
            pais=datos.pais.strip(),
            fecha_entrada=_fecha(datos.fecha_entrada),
            fecha_salida=_fecha(datos.fecha_salida),
            adultos=_entero(datos.adultos, 1),
            ninos=_entero(datos.ninos, 0),
            mascotas=datos.mascotas,
            presupuesto_max_noche=datos.presupuesto_max_noche,
            preferencias=datos.preferencias.strip(),
            max_distancia_km=datos.max_distancia_km,
            punto_referencia=datos.punto_referencia.strip() if datos.punto_referencia else None,
        )
        if espec.presupuesto_max_noche is not None and espec.presupuesto_max_noche <= 0:
            espec.presupuesto_max_noche = None
        if espec.max_distancia_km is not None and espec.max_distancia_km <= 0:
            espec.max_distancia_km = None
        if espec.punto_referencia is not None and not espec.punto_referencia.strip():
            espec.punto_referencia = None
        return espec

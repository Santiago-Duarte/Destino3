import json

from src.config import settings
from src.models.analisis import Analisis
from src.models.analisis_ia import LoteAnalisisIA, LotePuntuacionesIA
from src.models.busqueda import EspecificacionBusqueda
from src.models.hospedaje import Hospedaje
from src.services import gemini


def _precio(hospedaje: Hospedaje) -> float | None:
    if hospedaje.precio_noche is None:
        return None
    return float(hospedaje.precio_noche)


def _calificacion(hospedaje: Hospedaje) -> float:
    if hospedaje.calificacion is None:
        return 0.0
    return float(hospedaje.calificacion)


def _id(hospedaje: Hospedaje) -> int:
    """Los evaluadores solo operan sobre hospedajes ya persistidos."""
    if hospedaje.id is None:
        raise ValueError("El hospedaje debe estar persistido para evaluarse")
    return hospedaje.id


def preseleccionar_candidatos(
        hospedajes: list[Hospedaje],
        presupuesto_maximo_noche: float | None,
) -> list[Hospedaje]:
    """Ordena por calidad y deja los mejores candidatos dentro del presupuesto.

    Sin presupuesto se conservan también los hoteles sin tarifa conocida;
    quedan al final porque no se pueden comparar por precio.
    """
    if presupuesto_maximo_noche is None:
        candidatos = list(hospedajes)
    else:
        candidatos = []
        for hospedaje in hospedajes:
            precio = _precio(hospedaje)
            if precio is not None and precio <= presupuesto_maximo_noche:
                candidatos.append(hospedaje)

    return sorted(
        candidatos,
        key=lambda hospedaje: (
            -_calificacion(hospedaje),
            _precio(hospedaje) is None,
            _precio(hospedaje) or 0.0,
        ),
    )[:settings.MAX_CANDIDATOS_IA]


def _json(datos: list[dict]) -> str:
    return json.dumps(
        datos,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )


def _resumen_intrinseco(hospedaje: Hospedaje) -> dict:
    """Datos que no cambian con cada búsqueda ni con la tarifa."""
    return {
        "hospedaje_id": _id(hospedaje),
        "nombre": hospedaje.nombre,
        "tipo": hospedaje.tipo,
        "descripcion": hospedaje.descripcion or "",
        "direccion": hospedaje.direccion or "",
    }


def _resumen_comercial(hospedaje: Hospedaje) -> dict:
    resumen = _resumen_intrinseco(hospedaje)
    resumen["precio_noche"] = _precio(hospedaje)
    resumen["calificacion"] = hospedaje.calificacion
    return resumen


def _prompt_analisis(resumen_candidatos: list[dict]) -> str:
    return f"""
                Eres experto en alojamientos. Analiza cada hotel de este JSON:
                {_json(resumen_candidatos)}

                Instrucciones:
                1. Describe únicamente características objetivas e intrínsecas del alojamiento: no evalúes si sirve o no para quien lo busca.
                2. No menciones precios, tarifas ni calificaciones: cambian con cada búsqueda y este análisis se reutiliza.
                3. Responde con exactamente un elemento por cada `hospedaje_id` recibido; no inventes ni omitas ids.
                4. `resumen_ejecutivo` en una sola frase; `puntos_fuertes` y `puntos_debiles` como hechos separados por punto y coma.
                """


def _prompt_puntuacion(resumen_candidatos: list[dict], espec: EspecificacionBusqueda) -> str:
    presupuesto = (
        f"USD ${espec.presupuesto_max_noche:g} por noche"
        if espec.presupuesto_max_noche is not None
        else "Sin límite declarado"
    )
    preferencias = espec.preferencias.strip() or "Ninguna especificada"
    if espec.mascotas is None:
        mascotas = "no especificado"
    else:
        mascotas = "sí" if espec.mascotas else "no"
    return f"""
                Eres un asistente experto en viajes. Puntúa los hoteles de este JSON según lo que pide esta persona:
                {_json(resumen_candidatos)}

                Especificaciones del usuario:
                - Destino: {espec.ciudad}, {espec.pais}
                - Presupuesto máximo: {presupuesto}
                - Viaja con mascotas: {mascotas}
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
        self._cliente = gemini.crear_cliente()

    def analizar(self, hospedajes: list[Hospedaje]) -> LoteAnalisisIA:
        """Descripción intrínseca de los candidatos; se persiste y se reutiliza."""
        return gemini.generar(
            self._cliente,
            _prompt_analisis([
                _resumen_intrinseco(hospedaje) for hospedaje in hospedajes
            ]),
            LoteAnalisisIA,
            "analizar",
            hospedaje_ids={_id(hospedaje) for hospedaje in hospedajes},
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
            resumen = _resumen_comercial(hospedaje)
            analisis_previo = analisis.get(_id(hospedaje))
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
            hospedaje_ids={_id(hospedaje) for hospedaje in hospedajes},
        )

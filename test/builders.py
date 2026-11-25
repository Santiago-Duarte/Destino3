"""Builders y fixtures compartidos para tests.

Centraliza la creación de objetos de dominio y mocks frecuentes
para evitar duplicación y deriva entre archivos de test.
"""

from datetime import date
from unittest.mock import MagicMock

from src.models.analisis import Analisis
from src.models.analisis_ia import AnalisisIAOutput
from src.models.busqueda import EspecificacionBusqueda
from src.models.destino import Destino
from src.models.hospedaje import Hospedaje
from src.orchestrator.orquestador_integracion import Candidato, ResultadoBusqueda


def espec_completa(
    *,
    ciudad: str = "Medellin",
    pais: str = "Colombia",
    fecha_entrada: date | None = None,
    fecha_salida: date | None = None,
    adultos: int | None = 2,
    ninos: int | None = 0,
    mascotas: bool | None = False,
    presupuesto_max_noche: float | None = None,
    preferencias: str = "",
) -> EspecificacionBusqueda:
    """Especificación con valores por defecto razonables."""
    return EspecificacionBusqueda(
        ciudad=ciudad,
        pais=pais,
        fecha_entrada=fecha_entrada,
        fecha_salida=fecha_salida,
        adultos=adultos,
        ninos=ninos,
        mascotas=mascotas,
        presupuesto_max_noche=presupuesto_max_noche,
        preferencias=preferencias,
    )


def espec_con(**kwargs) -> EspecificacionBusqueda:
    """Alias corto para espec_completa (compatibilidad)."""
    return espec_completa(**kwargs)


def crear_hospedaje(
    *,
    id: int | None = None,
    nombre: str = "Hotel Test",
    tipo: str = "hotel",
    precio_noche: float | None = 100.0,
    calificacion: float | None = 4.5,
    direccion: str = "Calle 1",
    url_reserva: str = "https://hotel.example",
    destino_id: int = 1,
) -> Hospedaje:
    """Hospedaje con valores por defecto."""
    h = Hospedaje(
        nombre=nombre,
        tipo=tipo,
        precio_noche=precio_noche,
        calificacion=calificacion,
        direccion=direccion,
        url_reserva=url_reserva,
        destino_id=destino_id,
    )
    if id is not None:
        h.id = id
    return h


def crear_destino(
    *,
    id: int | None = None,
    ciudad: str = "Medellin",
    pais: str = "Colombia",
) -> Destino:
    """Destino con valores por defecto."""
    d = Destino(ciudad=ciudad, pais=pais)
    if id is not None:
        d.id = id
    return d


def respuesta_mock(
    *,
    propiedades: list[dict] | None = None,
    search_parameters: dict | None = None,
) -> dict:
    """Respuesta cruda de SerpAPI (estructura mínima)."""
    if propiedades is None:
        propiedades = [
            {
                "name": "Hotel A",
                "type": "hotel",
                "rate_per_night": {"lowest": "100", "extracted_lowest": 100.0},
                "overall_rating": 4.5,
                "address": "Calle A",
                "link": "https://hotela.com",
            },
            {
                "name": "Hotel B",
                "type": "hotel",
                "rate_per_night": {"lowest": "120", "extracted_lowest": 120.0},
                "overall_rating": 4.2,
                "address": "Calle B",
                "link": "https://hotelb.com",
            },
        ]
    return {"properties": propiedades, "search_parameters": search_parameters or {}}


def puntuacion_de(
    hospedaje_id: int,
    *,
    calidad: int,
    cumplimiento: int,
    cumplidos: tuple[str, ...] = (),
    faltantes: tuple[str, ...] = (),
) -> AnalisisIAOutput:
    """Puntuación IA lista para LotePuntuacionesIA."""
    return AnalisisIAOutput(
        hospedaje_id=hospedaje_id,
        score_calidad=calidad,
        score_cumplimiento=cumplimiento,
        requisitos_cumplidos=list(cumplidos),
        requisitos_faltantes=list(faltantes),
    )


def analisis_para(
    hospedaje_id: int,
    *,
    resumen: str = "Resumen",
    fuertes: str = "Fuertes",
    debiles: str = "Débiles",
    id: int | None = None,
) -> Analisis:
    """Fila de tabla analisis_ia."""
    a = Analisis(
        resumen_ejecutivo=resumen,
        puntos_fuertes=fuertes,
        puntos_debiles=debiles,
        hospedaje_id=hospedaje_id,
    )
    if id is not None:
        a.id = id
    return a


def candidato_de(
    hospedaje_id: int,
    *,
    calidad: int = 5,
    cumplimiento: int = 5,
    cumplidos: tuple[str, ...] = (),
    faltantes: tuple[str, ...] = (),
    precio_noche: float | None = 100.0,
    calificacion: float | None = 4.0,
) -> Candidato:
    """Candidato completo para tests de orquestador/ranking."""
    hospedaje = crear_hospedaje(
        id=hospedaje_id,
        precio_noche=precio_noche,
        calificacion=calificacion,
    )
    analisis = analisis_para(hospedaje_id)
    return Candidato(
        hospedaje=hospedaje,
        analisis=analisis,
        score_calidad=calidad,
        score_cumplimiento=cumplimiento,
        requisitos_cumplidos=list(cumplidos),
        requisitos_faltantes=list(faltantes),
    )


def resultado_con(candidatos: list[Candidato], espec: EspecificacionBusqueda | None = None) -> ResultadoBusqueda:
    """ResultadoBusqueda listo para aserciones."""
    if espec is None:
        espec = espec_completa()
    from src.orchestrator.orquestador_integracion import rankear_candidatos
    return ResultadoBusqueda(espec, rankear_candidatos(candidatos))


def mock_transaccion(cursor: MagicMock | None = None) -> MagicMock:
    """Context manager de transacción que devuelve el cursor dado."""
    if cursor is None:
        cursor = MagicMock()
    tx = MagicMock()
    tx.__enter__.return_value = cursor
    tx.__exit__.return_value = None
    return tx


def _ciudad_unica() -> str:
    """Ciudad única por test para evitar colisiones en BD."""
    import uuid
    return f"Ciudad_{uuid.uuid4().hex[:8]}"


# Patchers frecuentes como helpers
def patch_settings_serpapi(**kwargs):
    """Genera patch.multiple para settings de SerpAPI."""
    from unittest.mock import patch
    prefijos = {
        "key": "SERPAPI_KEY",
        "max_reintentos": "SERPAPI_MAX_REINTENTOS",
        "rate_limit_rps": "SERPAPI_RATE_LIMIT_RPS",
        "max_pages": "SERPAPI_MAX_PAGES",
        "max_results": "SERPAPI_MAX_RESULTS",
        "backoff_base": "SERPAPI_BACKOFF_BASE",
    }
    mapping = {f"src.services.buscador_serpapi.settings.{prefijos[k]}": v for k, v in kwargs.items()}
    return patch.multiple("src.services.buscador_serpapi.settings", **mapping)
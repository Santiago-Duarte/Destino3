import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from src.config import settings
from src.exceptions.LoteIAError import LoteIAError
from src.models.analisis import Analisis
from src.models.busqueda import EspecificacionBusqueda
from src.models.hospedaje import Hospedaje
from src.repositories.analisis_ia_repository import AnalisisIARepository
from src.repositories.hospedaje_repository import HospedajeRepository
from src.services.buscador_serpapi import buscar_hospedajes
from src.services.evaluador_ia import EvaluadorIA, preseleccionar_candidatos
from src.services.interpretador_ia import InterpretadorIA

logger = logging.getLogger(__name__)


@dataclass
class Candidato:
    hospedaje: Hospedaje
    analisis: Analisis | None = None
    score_calidad: int | None = None
    score_cumplimiento: int | None = None
    requisitos_cumplidos: list[str] = field(default_factory=list)
    requisitos_faltantes: list[str] = field(default_factory=list)


@dataclass
class ResultadoBusqueda:
    especificacion: EspecificacionBusqueda
    candidatos: list[Candidato]  # ya rankeados

    def mejores(self, cantidad: int | None = None) -> list[Candidato]:
        """Devuelve el top de candidatos puntuados.

        Con requisitos, un candidato entra si la IA reportó al menos un
        requisito cumplido o si su score es suficientemente alto. El score
        cubre el caso de una respuesta parcial sin listas de requisitos.
        """
        cantidad = settings.TOP_RESULTADOS if cantidad is None else cantidad
        puntuados = [
            candidato for candidato in self.candidatos
            if candidato.score_cumplimiento is not None
        ]
        if self.especificacion.tiene_requisitos():
            filtrados = []
            for candidato in puntuados:
                score = candidato.score_cumplimiento
                if candidato.requisitos_cumplidos or (
                        score is not None
                        and score >= settings.SCORE_CUMPLIMIENTO_MINIMO
                ):
                    filtrados.append(candidato)
            puntuados = filtrados
        return puntuados[:cantidad]


def _id_de(candidato: Candidato) -> int:
    """Los candidatos ya persistidos deben tener id para analizarse."""
    if candidato.hospedaje.id is None:
        raise ValueError("El hospedaje del candidato no está persistido")
    return candidato.hospedaje.id


def rankear_candidatos(candidatos: list[Candidato]) -> list[Candidato]:
    """Cumplimiento primero y después calidad; sin puntaje quedan al final."""
    return sorted(
        candidatos,
        key=lambda candidato: (
            candidato.score_cumplimiento is not None,
            candidato.score_cumplimiento or 0,
            candidato.score_calidad or 0,
        ),
        reverse=True,
    )


class OrquestadorIntegracion:

    def __init__(
            self,
            buscar_hospedajes: Callable[[str, str, float | None], list[Hospedaje]] = buscar_hospedajes,
            interpretar: Callable[[str], EspecificacionBusqueda] | None = None,
            hospedajes_repo: HospedajeRepository | None = None,
            analisis_repo: AnalisisIARepository | None = None,
            evaluador: EvaluadorIA | None = None,
    ) -> None:
        self._buscar_hospedajes = buscar_hospedajes
        self._interpretar = interpretar
        self._hospedajes_repo = hospedajes_repo
        self._analisis_repo = analisis_repo
        self._evaluador = evaluador

    def buscar_desde_frase(self, frase: str) -> ResultadoBusqueda:
        interpretar = self._interpretar or InterpretadorIA().interpretar
        espec = interpretar(frase)

        hospedajes = self._buscar_hospedajes(
            espec.ciudad, espec.pais, espec.presupuesto_max_noche
        )
        if not hospedajes:
            return ResultadoBusqueda(espec, [])

        repositorio_hospedajes = self._hospedajes_repo or HospedajeRepository()
        for hospedaje, id_generado in zip(
                hospedajes,
                repositorio_hospedajes.guardar_lote(hospedajes),
                strict=True,
        ):
            hospedaje.id = id_generado

        candidatos = [
            Candidato(hospedaje=hospedaje)
            for hospedaje in preseleccionar_candidatos(
                hospedajes, espec.presupuesto_max_noche
            )
        ]
        if not candidatos:
            return ResultadoBusqueda(espec, [])

        self._completar_analisis(candidatos)
        self._puntuar(candidatos, espec)
        return ResultadoBusqueda(espec, rankear_candidatos(candidatos))

    def _completar_analisis(self, candidatos: list[Candidato]) -> None:
        repositorio = self._analisis_repo or AnalisisIARepository()
        guardados = repositorio.obtener_por_hospedajes(
            [_id_de(candidato) for candidato in candidatos]
        )
        for candidato in candidatos:
            candidato.analisis = guardados.get(_id_de(candidato))

        sin_analisis = [
            candidato for candidato in candidatos
            if candidato.analisis is None
        ]
        if not sin_analisis:
            return

        try:
            lote = self._obtener_evaluador().analizar(
                [candidato.hospedaje for candidato in sin_analisis]
            )
        except LoteIAError as error:
            # Sin análisis la búsqueda sigue: esos candidatos se puntúan con sus datos crudos.
            logger.warning("No se pudo analizar el lote de candidatos: %s", error)
            return

        esperados = {_id_de(candidato) for candidato in sin_analisis}
        por_hospedaje: dict[int, Analisis] = {}
        for item in lote.analisis:
            if item.hospedaje_id in esperados:
                # Si el modelo repite un id, gana la última respuesta válida.
                por_hospedaje[item.hospedaje_id] = Analisis.desde_ia(item)

        nuevos = list(por_hospedaje.values())
        if not nuevos:
            return

        ids_generados = repositorio.guardar_lote(nuevos)
        for analisis, id_generado in zip(nuevos, ids_generados, strict=True):
            analisis.id = id_generado

        guardados.update(por_hospedaje)
        for candidato in sin_analisis:
            candidato.analisis = guardados.get(_id_de(candidato))

    def _puntuar(self, candidatos: list[Candidato], espec: EspecificacionBusqueda) -> None:
        try:
            lote = self._obtener_evaluador().puntuar(
                [candidato.hospedaje for candidato in candidatos],
                {_id_de(candidato): candidato.analisis
                 for candidato in candidatos if candidato.analisis is not None},
                espec,
            )
        except LoteIAError as error:
            # Sin puntaje la búsqueda sigue: queda el orden local por calificación.
            logger.warning("No se pudo puntuar el lote de candidatos: %s", error)
            return

        puntuaciones = {puntuacion.hospedaje_id: puntuacion
                        for puntuacion in lote.puntuaciones}

        for candidato in candidatos:
            puntuacion = puntuaciones.get(_id_de(candidato))
            if puntuacion is None:
                logger.warning(
                    "Sin puntaje para %s; queda al final del ranking",
                    candidato.hospedaje.nombre,
                )
                continue
            candidato.score_calidad = puntuacion.score_calidad
            candidato.score_cumplimiento = puntuacion.score_cumplimiento
            candidato.requisitos_cumplidos = puntuacion.requisitos_cumplidos
            candidato.requisitos_faltantes = puntuacion.requisitos_faltantes

    def _obtener_evaluador(self) -> EvaluadorIA:
        if self._evaluador is None:
            self._evaluador = EvaluadorIA()
        return self._evaluador

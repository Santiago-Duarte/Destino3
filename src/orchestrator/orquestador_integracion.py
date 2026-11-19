import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from src.exceptions.Evaluacion_IA_error import EvaluacionIALoteError
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

    def mejores(self, cantidad: int = 3) -> list[Candidato]:
        puntuados = [candidato for candidato in self.candidatos
                     if candidato.score_cumplimiento is not None]
        if self.especificacion.tiene_requisitos():
            puntuados = [candidato for candidato in puntuados if candidato.requisitos_cumplidos]
        return puntuados[:cantidad]


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
                hospedajes, repositorio_hospedajes.guardar_lote(hospedajes)
        ):
            hospedaje.id = id_generado

        presupuesto = espec.presupuesto_max_noche or float("inf")
        candidatos = [
            Candidato(hospedaje=hospedaje)
            for hospedaje in preseleccionar_candidatos(hospedajes, presupuesto)
        ]
        if not candidatos:
            return ResultadoBusqueda(espec, [])

        self._completar_analisis(candidatos)
        self._puntuar(candidatos, espec)
        return ResultadoBusqueda(espec, rankear_candidatos(candidatos))

    def _completar_analisis(self, candidatos: list[Candidato]) -> None:
        repositorio = self._analisis_repo or AnalisisIARepository()
        guardados = repositorio.obtener_por_hospedajes(
            [candidato.hospedaje.id for candidato in candidatos]
        )
        for candidato in candidatos:
            candidato.analisis = guardados.get(candidato.hospedaje.id)

        sin_analisis = [candidato for candidato in candidatos if candidato.analisis is None]
        if not sin_analisis:
            return

        try:
            lote = self._obtener_evaluador().analizar(
                [candidato.hospedaje for candidato in sin_analisis]
            )
        except EvaluacionIALoteError as error:
            # Sin análisis la búsqueda sigue: esos candidatos se puntúan con sus datos crudos.
            logger.warning("No se pudo analizar el lote de candidatos: %s", error)
            return

        esperados = {candidato.hospedaje.id for candidato in sin_analisis}
        nuevos = [
            Analisis.desde_ia(item)
            for item in lote.analisis
            if item.hospedaje_id in esperados and item.hospedaje_id not in guardados
        ]
        repositorio.guardar_lote(nuevos)

        guardados.update({item.hospedaje_id: item for item in nuevos})
        for candidato in sin_analisis:
            candidato.analisis = guardados.get(candidato.hospedaje.id)

    def _puntuar(self, candidatos: list[Candidato], espec: EspecificacionBusqueda) -> None:
        lote = self._obtener_evaluador().puntuar(
            [candidato.hospedaje for candidato in candidatos],
            {candidato.hospedaje.id: candidato.analisis
             for candidato in candidatos if candidato.analisis is not None},
            espec,
        )
        puntuaciones = {puntuacion.hospedaje_id: puntuacion
                        for puntuacion in lote.puntuaciones}

        for candidato in candidatos:
            puntuacion = puntuaciones.get(candidato.hospedaje.id)
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

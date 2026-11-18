from dataclasses import dataclass
from typing import Callable

from src.exceptions import PersistenciaError
from src.models.evaluacion import Evaluacion
from src.models.evaluacion_ia import LoteEvaluacionesIA
from src.models.hospedaje import Hospedaje
from src.repositories.evaluacion_ia_repository import EvaluacionIARepository
from src.repositories.hospedaje_repository import HospedajeRepository
from src.services.buscador_serpapi import buscar_hospedajes
from src.services.evaluador_ia import EvaluadorIA


@dataclass
class ResultadoIntegracion:
    hospedajes: list[Hospedaje]
    resultado_ia: tuple[LoteEvaluacionesIA, dict[int, Hospedaje]] | None


class OrquestadorIntegracion:

    def __init__(
            self,
            buscar_hospedajes: Callable[[str, str, float | None], list[Hospedaje]] = buscar_hospedajes,
            hospedajes_repo: HospedajeRepository | None = None,
            evaluaciones_repo: EvaluacionIARepository | None = None,
            evaluador: EvaluadorIA | None = None,
    ) -> None:
        self._buscar_hospedajes = buscar_hospedajes
        self._hospedajes_repo = hospedajes_repo
        self._evaluaciones_repo = evaluaciones_repo
        self._evaluador = evaluador

    def buscar_persistir_y_evaluar(
            self,
            ciudad: str,
            pais: str,
            presupuesto_maximo_noche: float,
            preferencias: str,
    ) -> ResultadoIntegracion | list:
        hospedajes = self._buscar_hospedajes(ciudad, pais, presupuesto_maximo_noche)
        if not hospedajes:
            return []

        repositorio_hospedajes = self._hospedajes_repo or HospedajeRepository()
        ids_generados = repositorio_hospedajes.guardar_lote(hospedajes)
        for hospedaje, id_generado in zip(hospedajes, ids_generados):
            hospedaje.id = id_generado

        evaluador = self._evaluador or EvaluadorIA()
        resultado_ia = evaluador.evaluar_lote(
            hospedajes, presupuesto_maximo_noche, preferencias
        )
        return ResultadoIntegracion(hospedajes=hospedajes, resultado_ia=resultado_ia)

    def persistir_evaluaciones(self, resultado: ResultadoIntegracion) -> list[Evaluacion]:
        if resultado.resultado_ia is None:
            return []

        lote_ia, hospedaje_por_id_temporal = resultado.resultado_ia
        evaluaciones = []
        for evaluacion_ia in lote_ia.evaluaciones:
            hospedaje = hospedaje_por_id_temporal.get(evaluacion_ia.id_temporal)
            if hospedaje is None:
                raise PersistenciaError(
                    "PostgreSQL",
                    "persistir_evaluaciones",
                    f"No existe hospedaje para id_temporal {evaluacion_ia.id_temporal}",
                )
            evaluaciones.append(Evaluacion.desde_ia(evaluacion_ia, hospedaje.id))

        if not evaluaciones:
            return []

        repositorio_evaluaciones = self._evaluaciones_repo or EvaluacionIARepository()
        ids_generados = repositorio_evaluaciones.guardar_lote(evaluaciones)
        for evaluacion, id_generado in zip(evaluaciones, ids_generados):
            evaluacion.id = id_generado
        return evaluaciones

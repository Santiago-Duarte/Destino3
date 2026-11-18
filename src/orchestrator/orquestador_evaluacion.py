import logging

from src.models.evaluacion import Evaluacion
from src.models.evaluacion_ia import EvaluacionIAOutput, LoteEvaluacionesIA
from src.models.hospedaje import Hospedaje
from src.repositories.evaluacion_ia_repository import EvaluacionIARepository
from src.services.evaluador_ia import EvaluadorIA

logger = logging.getLogger(__name__)


class OrquestadorEvaluacion:

    def __init__(self) -> None:
        self._evaluador = EvaluadorIA()
        self._repositorio_evaluaciones = EvaluacionIARepository()

    def evaluar_y_persistir(
            self,
            hospedajes: list[Hospedaje],
            presupuesto_maximo_noche: float,
            preferencias: str,
    ) -> list[Evaluacion]:
        resultado_ia = self._evaluador.evaluar_lote(
            hospedajes, presupuesto_maximo_noche, preferencias
        )

        if resultado_ia is None:
            logger.warning("No se pudo evaluar los hospedajes")
            return []

        lote_ia, hospedaje_por_id_temporal = resultado_ia
        candidatos = self._emparejar_evaluaciones(lote_ia, hospedaje_por_id_temporal)

        evaluaciones = [
            Evaluacion.desde_ia(evaluacion_ia, hospedaje.id)
            for evaluacion_ia, hospedaje in candidatos
        ]
        ids_generados = self._repositorio_evaluaciones.guardar_lote(evaluaciones)
        for evaluacion, id_generado in zip(evaluaciones, ids_generados):
            evaluacion.id = id_generado

        return evaluaciones

    @staticmethod
    def _emparejar_evaluaciones(
            lote_ia: LoteEvaluacionesIA,
            hospedaje_por_id_temporal: dict[int, Hospedaje],
    ) -> list[tuple[EvaluacionIAOutput, Hospedaje]]:
        candidatos = []
        for evaluacion_ia in lote_ia.evaluaciones:
            hospedaje = hospedaje_por_id_temporal.get(evaluacion_ia.id_temporal)
            if hospedaje is None:
                logger.warning(
                    "id_temporal %s sin hospedaje asociado, descartando",
                    evaluacion_ia.id_temporal,
                )
                continue
            candidatos.append((evaluacion_ia, hospedaje))
        return candidatos

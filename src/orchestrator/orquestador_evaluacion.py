import logging

from src.models.evaluacion import Evaluacion
from src.models.evaluacion_ia import EvaluacionIAOutput, LoteEvaluacionesIA
from src.models.hospedaje import Hospedaje
from src.models.recomendacion import Recomendacion
from src.repositories.evaluacion_ia_repository import EvaluacionIARepository
from src.repositories.recomendacion_repository import RecomendacionRepository
from src.services.evaluador_ia import EvaluadorIA

logger = logging.getLogger(__name__)


class OrquestadorEvaluacion:

    def __init__(self) -> None:
        self.evaluador = EvaluadorIA()
        self.evaluaciones_repo = EvaluacionIARepository()
        self.recomendaciones_repo = RecomendacionRepository()

    def evaluar_y_persistir(
            self,
            hospedajes: list[Hospedaje],
            busqueda_id: int,
            presupuesto_max: float,
            preferencias: str,
    ) -> list[Evaluacion]:
        """Evalúa los candidatos con IA y persiste evaluaciones y recomendaciones.

        Descarta los ``id_temporal`` huérfanos que la IA devuelva sin hospedaje
        asociado, guarda las evaluaciones de los 3 elegidos en una única
        transacción y, después, persiste las recomendaciones ordenadas por
        posición. Si la IA no devuelve nada utilizable no se escribe nada.

        Args:
            hospedajes: Candidatos a evaluar.
            busqueda_id: Búsqueda a la que pertenecen las recomendaciones.
            presupuesto_max: Presupuesto máximo por noche en USD.
            preferencias: Criterios adicionales del usuario.

        Returns:
            Las evaluaciones guardadas en base de datos, con su id asignado.
        """
        resultado = self.evaluador.evaluar_lote(hospedajes, presupuesto_max, preferencias)

        if resultado is None:
            logger.warning("No se pudo evaluar los hospedajes")
            return []

        respuesta, hospedajes_por_id_temporal = resultado
        candidatos = self._candidatos_elegidos(respuesta, hospedajes_por_id_temporal)

        evaluaciones = [
            Evaluacion.desde_ia(evaluacion_ia, hospedaje.id)
            for evaluacion_ia, hospedaje in candidatos
        ]
        for evaluacion, id_generado in zip(evaluaciones, self.evaluaciones_repo.guardar_lote(evaluaciones)):
            evaluacion.id = id_generado

        recomendaciones = [
            Recomendacion(
                id=None,
                busqueda_id=busqueda_id,
                hospedaje_id=hospedaje.id,
                posicion=posicion,
            )
            for posicion, (_, hospedaje) in enumerate(candidatos, start=1)
        ]
        if recomendaciones:
            self.recomendaciones_repo.guardar_lote(recomendaciones)

        return evaluaciones

    @staticmethod
    def _candidatos_elegidos(
            respuesta: LoteEvaluacionesIA,
            hospedajes_por_id_temporal: dict[int, Hospedaje],
    ) -> list[tuple[EvaluacionIAOutput, Hospedaje]]:
        """Descarta los ``id_temporal`` sin hospedaje y devuelve los pares en el orden de la IA."""
        candidatos = []
        for evaluacion_ia in respuesta.evaluaciones:
            hospedaje = hospedajes_por_id_temporal.get(evaluacion_ia.id_temporal)
            if hospedaje is None:
                logger.warning("id_temporal %s sin hospedaje asociado, descartando", evaluacion_ia.id_temporal)
                continue
            candidatos.append((evaluacion_ia, hospedaje))
        return candidatos

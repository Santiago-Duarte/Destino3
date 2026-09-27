import logging
from src.services.ai_evaluator import AIEvaluator, Top3Evaluaciones, convertir_a_evaluacion
from src.repositories.evaluaciones_repository import EvaluacionesRepository
from src.repositories.recomendacion_repository import RecomendacionRepository
from src.models.evaluacion import Evaluacion
from src.models.hospedaje import Hospedaje
from src.models.recomendaciones import Recomendaciones

logger = logging.getLogger(__name__)


class EvaluacionOrchestrator:

    def __init__(self) -> None:
        self.evaluador = AIEvaluator()
        self.evaluaciones_repo = EvaluacionesRepository()
        self.recomendaciones_repo = RecomendacionRepository()

    def ejecutar(
            self,
            hospedajes: list[Hospedaje],
            busqueda_id: int,
            presupuesto_max: float,
            preferencias: str,
    ) -> list[Evaluacion]:
        """Coordina la evaluación con IA y la persistencia de resultados.

        Para cada uno de los 3 hospedajes elegidos por el modelo, descarta los
        id_temporales huérfanos, guarda la evaluación asociándola al hospedaje
        real y, al final, persiste las recomendaciones ordenadas por posición.

        Args:
            hospedajes: Candidatos a evaluar.
            busqueda_id: Búsqueda a la que pertenecen las recomendaciones.
            presupuesto_max: Presupuesto máximo por noche en USD.
            preferencias: Criterios adicionales del usuario.

        Returns:
            Las evaluaciones guardadas en base de datos; vacía si el evaluador
            no devuelve resultado o ninguna evaluación se persiste correctamente.
        """
        resultado = self.evaluador.evaluar_hospedaje(hospedajes, presupuesto_max, preferencias)

        if resultado is None:
            logger.warning("No se pudo evaluar los hospedajes")
            return []

        respuesta, mapping = resultado
        evaluaciones_guardadas = []

        for evaluacion_ia in respuesta.top_3:
            hospedaje_real = mapping.get(evaluacion_ia.id_temporal)

            if hospedaje_real is None:
                logger.warning(f"id_temporal {evaluacion_ia.id_temporal} no encontrado en mapping, descartando")
                continue

            evaluacion = convertir_a_evaluacion(evaluacion_ia, hospedaje_real.id)
            evaluacion_id = self.evaluaciones_repo.guardar(evaluacion)

            if evaluacion_id is not None:
                evaluacion.id = evaluacion_id
                evaluaciones_guardadas.append(evaluacion)

        self._guardar_recomendaciones(respuesta, busqueda_id, mapping)

        return evaluaciones_guardadas

    def _guardar_recomendaciones(
            self,
            respuesta: Top3Evaluaciones,
            busqueda_id: int,
            mapping: dict[int, Hospedaje],
    ) -> None:
        """Persiste las recomendaciones del top 3 en una sola operación atómica.

        Args:
            respuesta: Top 3 devuelto por el modelo, en orden de preferencia.
            busqueda_id: Búsqueda propietaria de las recomendaciones.
            mapping: Correspondencia entre ``id_temporal`` y hospedaje real.
        """
        recomendaciones = []

        for posicion, evaluacion_ia in enumerate(respuesta.top_3, start=1):
            hospedaje_real = mapping.get(evaluacion_ia.id_temporal)

            if hospedaje_real is None:
                continue

            recomendacion = Recomendaciones(
                id=None,
                busqueda_id=busqueda_id,
                hospedaje_id=hospedaje_real.id,
                posicion=posicion,
            )
            recomendaciones.append(recomendacion)

        if recomendaciones:
            exito = self.recomendaciones_repo.guardar_varias(recomendaciones, busqueda_id)
            if not exito:
                logger.error("Error al guardar las recomendaciones")

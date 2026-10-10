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
class IntegracionResultado:
    """Resultado del flujo F1 antes de persistir evaluaciones IA."""

    hospedajes: list[Hospedaje]
    resultado_ia: tuple[LoteEvaluacionesIA, dict[int, Hospedaje]] | None


class OrquestadorIntegracion:
    """Coordina la búsqueda, persistencia e evaluación de hospedajes."""

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

    def ejecutar(
            self,
            ciudad: str,
            pais: str,
            presupuesto_max: float,
            preferencias: str,
    ) -> IntegracionResultado | list:
        """Ejecuta búsqueda, persistencia de hospedajes y evaluación en lote.

        Args:
            ciudad: Ciudad donde se buscarán hospedajes.
            pais: País de la ciudad.
            presupuesto_max: Precio máximo por noche.
            preferencias: Criterios adicionales para la evaluación IA.

        Returns:
            ``[]`` si la búsqueda no devuelve hospedajes; en otro caso, un
            ``IntegracionResultado`` con hospedajes que ya tienen IDs reales y
            el resultado de la única llamada de evaluación IA.
        """
        hospedajes = self._buscar_hospedajes(ciudad, pais, presupuesto_max)
        if not hospedajes:
            return []

        hospedajes_repo = self._hospedajes_repo or HospedajeRepository()
        ids = hospedajes_repo.guardar_lote(hospedajes)
        for hospedaje, id_generado in zip(hospedajes, ids):
            hospedaje.id = id_generado

        evaluador = self._evaluador or EvaluadorIA()
        resultado_ia = evaluador.evaluar_lote(hospedajes, presupuesto_max, preferencias)
        return IntegracionResultado(hospedajes=hospedajes, resultado_ia=resultado_ia)

    def persistir_evaluaciones(self, resultado: IntegracionResultado) -> list[Evaluacion]:
        """Mapea y persiste el lote IA usando los IDs reales de hospedajes.

        Args:
            resultado: Resultado de F1 con hospedajes persistidos y respuesta IA.

        Returns:
            Evaluaciones persistidas con sus IDs generados por PostgreSQL, o
            una lista vacía si el lote IA no produjo resultado.

        Raises:
            PersistenciaError: si una evaluación apunta a un ``id_temporal``
                que no existe en el mapa del lote.
        """
        if resultado.resultado_ia is None:
            return []

        respuesta_ia, hospedajes_por_id_temporal = resultado.resultado_ia
        evaluaciones = []
        for evaluacion_ia in respuesta_ia.evaluaciones:
            hospedaje = hospedajes_por_id_temporal.get(evaluacion_ia.id_temporal)
            if hospedaje is None:
                raise PersistenciaError(
                    "PostgreSQL",
                    "persistir_evaluaciones",
                    f"No existe hospedaje para id_temporal {evaluacion_ia.id_temporal}",
                )
            evaluaciones.append(Evaluacion.desde_ia(evaluacion_ia, hospedaje.id))

        if not evaluaciones:
            return []

        evaluaciones_repo = self._evaluaciones_repo or EvaluacionIARepository()
        ids = evaluaciones_repo.guardar_lote(evaluaciones)
        for evaluacion, id_generado in zip(evaluaciones, ids):
            evaluacion.id = id_generado
        return evaluaciones

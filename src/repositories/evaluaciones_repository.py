import logging
from typing import Optional
from src.repositories.base_repository import BaseRepository
from src.services.ai_evaluator import EvaluacionIAOutput

logger = logging.getLogger(__name__)


class EvaluacionesRepository(BaseRepository):

    def guardar(self, evaluacion: EvaluacionIAOutput, hospedaje_id: int) -> Optional[int]:
        conexion = self._obtener_conexion()
        cursor = conexion.cursor()

        try:
            query = """
                INSERT INTO evaluaciones_ia (resumen_ejecutivo, puntos_fuertes, puntos_debiles, score_calidad_precio, hospedaje_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id;
            """
            cursor.execute(
                query,
                (
                    evaluacion.resumen_ejecutivo,
                    evaluacion.puntos_fuertes,
                    evaluacion.puntos_debiles,
                    evaluacion.score_calidad_precio,
                    hospedaje_id,
                )
            )
            evaluacion_id = cursor.fetchone()[0]
            conexion.commit()
            return evaluacion_id
        except Exception as error:
            conexion.rollback()
            logger.error(f"Error al guardar la evaluación: {error}")
            raise
        finally:
            cursor.close()
            conexion.close()

    def obtener_por_hospedaje(self, hospedaje_id: int) -> Optional[EvaluacionIAOutput]:
        conexion = self._obtener_conexion()
        cursor = conexion.cursor()

        try:
            query = """
                SELECT resumen_ejecutivo, puntos_fuertes, puntos_debiles, score_calidad_precio, hospedaje_id
                FROM evaluaciones_ia
                WHERE hospedaje_id = %s;
            """
            cursor.execute(query, (hospedaje_id,))
            fila = cursor.fetchone()

            if fila is None:
                return None

            return EvaluacionIAOutput(
                id_temporal=fila[4],
                resumen_ejecutivo=fila[0],
                puntos_fuertes=fila[1],
                puntos_debiles=fila[2],
                score_calidad_precio=fila[3],
            )
        except Exception as error:
            logger.error(f"Error al obtener la evaluación: {error}")
            return None
        finally:
            cursor.close()
            conexion.close()

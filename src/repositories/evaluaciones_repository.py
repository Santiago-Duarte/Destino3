import logging
from typing import Optional
from src.repositories.base_repository import BaseRepository
from src.models.evaluacion import Evaluacion

logger = logging.getLogger(__name__)


class EvaluacionesRepository(BaseRepository):

    def guardar(self, evaluacion: Evaluacion) -> Optional[int]:
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
                    evaluacion.hospedaje_id,
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

    def obtener_por_hospedaje(self, hospedaje_id: int) -> Optional[Evaluacion]:
        conexion = self._obtener_conexion()
        cursor = conexion.cursor()

        try:
            query = """
                SELECT id, resumen_ejecutivo, puntos_fuertes, puntos_debiles, score_calidad_precio, hospedaje_id
                FROM evaluaciones_ia
                WHERE hospedaje_id = %s;
            """
            cursor.execute(query, (hospedaje_id,))
            fila = cursor.fetchone()

            if fila is None:
                return None

            return Evaluacion(
                id=fila[0],
                resumen_ejecutivo=fila[1],
                puntos_fuertes=fila[2],
                puntos_debiles=fila[3],
                score_calidad_precio=fila[4],
                hospedaje_id=fila[5],
            )
        except Exception as error:
            logger.error(f"Error al obtener la evaluación: {error}")
            return None
        finally:
            cursor.close()
            conexion.close()

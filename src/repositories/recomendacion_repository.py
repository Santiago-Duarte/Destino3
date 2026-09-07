import logging
from typing import Optional
from src.repositories.base_repository import BaseRepository
from src.models.recomendaciones import Recomendaciones

logger = logging.getLogger(__name__)


class RecomendacionRepository(BaseRepository):

    def guardar_varias(self, recomendaciones: list[Recomendaciones], busqueda_id: int) -> bool:
        conexion = self._obtener_conexion()
        cursor = conexion.cursor()

        try:
            for recomendacion in recomendaciones:
                query = """INSERT INTO recomendaciones (busqueda_id, hospedaje_id, posicion) VALUES (%s, %s, %s);"""
                cursor.execute(query, (busqueda_id, recomendacion.hospedaje_id, recomendacion.posicion))

            conexion.commit()
            return True
        except Exception as error:
            conexion.rollback()
            logger.error(f"Error al guardar las recomendaciones: {error}")
            return False
        finally:
            cursor.close()
            conexion.close()

    def obtener_por_busqueda(self, busqueda_id: int) -> list[Recomendaciones]:
        conexion = self._obtener_conexion()
        cursor = conexion.cursor()

        try:
            query = """
                SELECT id, busqueda_id, hospedaje_id, posicion
                FROM recomendaciones
                WHERE busqueda_id = %s
                ORDER BY posicion;
            """
            cursor.execute(query, (busqueda_id,))
            filas = cursor.fetchall()

            recomendaciones = []
            for fila in filas:
                recomendacion = Recomendaciones(
                    id=fila[0],
                    busqueda_id=fila[1],
                    hospedaje_id=fila[2],
                    posicion=fila[3],
                )
                recomendaciones.append(recomendacion)

            return recomendaciones
        except Exception as error:
            logger.error(f"Error al obtener las recomendaciones: {error}")
            return []
        finally:
            cursor.close()
            conexion.close()
import logging
from src.repositories.base_repository import BaseRepository
from src.models.recomendaciones import Recomendaciones

logger = logging.getLogger(__name__)


class RecomendacionRepository(BaseRepository):

    def guardar_varias(self, recomendaciones: list[Recomendaciones], busqueda_id: int) -> bool:
        """Inserta el top de recomendaciones de una búsqueda en una sola transacción.

        Args:
            recomendaciones: Recomendaciones a persistir, ya con su posición.
            busqueda_id: Búsqueda propietaria de las recomendaciones.

        Returns:
            ``True`` si todo el lote se insertó y confirmó; ``False`` si
            cualquier inserción falla, en cuyo caso se revierte el lote completo.
        """
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

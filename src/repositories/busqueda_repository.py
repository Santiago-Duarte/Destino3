import logging
from typing import Optional
from src.repositories.base_repository import BaseRepository
from src.models.busqueda import Busqueda

logger = logging.getLogger(__name__)


class BusquedaRepository(BaseRepository):

    def guardar(self, busqueda: Busqueda) -> Optional[int]:
        conexion = self._obtener_conexion()
        cursor = conexion.cursor()

        try:
            query = """INSERT INTO busquedas (usuario_id, destino_id, zona, presupuesto, fecha_inicio, fecha_fin) 
                       VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;"""

            cursor.execute(
                query,
                (busqueda.usuario_id,
                 busqueda.destino_id,
                 busqueda.zona,
                 busqueda.presupuesto,
                 busqueda.fecha_inicio,
                 busqueda.fecha_fin)
            )

            busqueda_id = cursor.fetchone()[0]
            conexion.commit()
            return busqueda_id
        except Exception as error:
            conexion.rollback()
            logger.error(f"Error al guardar la busqueda: {error}")
            return None
        finally:
            cursor.close()
            conexion.close()
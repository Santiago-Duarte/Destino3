import logging
from typing import Optional
from src.repositories.base_repository import BaseRepository
from src.models.busqueda import Busqueda

logger = logging.getLogger(__name__)


class BusquedaRepository(BaseRepository):

    def guardar(self, busqueda: Busqueda) -> Optional[int]:
        """Inserta una búsqueda con sus criterios de zona, presupuesto y fechas.

        Returns:
            El id generado, o ``None`` si el ``INSERT`` falla (la transacción
            se revierte).
        """
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

    def obtener_por_id(self, busqueda_id: int) -> Optional[Busqueda]:
        """Recupera una búsqueda por su id.

        Returns:
            La búsqueda encontrada, o ``None`` si no existe o la consulta falla.
        """
        conexion = self._obtener_conexion()
        cursor = conexion.cursor()

        try:
            query = """
                SELECT id, usuario_id, destino_id, zona, presupuesto, fecha_inicio, fecha_fin
                FROM busquedas
                WHERE id = %s;
            """
            cursor.execute(query, (busqueda_id,))
            fila = cursor.fetchone()

            if fila is None:
                return None

            return Busqueda(
                id=fila[0],
                usuario_id=fila[1],
                destino_id=fila[2],
                zona=fila[3],
                presupuesto=fila[4],
                fecha_inicio=fila[5],
                fecha_fin=fila[6],
            )
        except Exception as error:
            logger.error(f"Error al obtener la búsqueda: {error}")
            return None
        finally:
            cursor.close()
            conexion.close()
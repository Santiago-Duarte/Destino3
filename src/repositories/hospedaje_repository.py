import logging
from src.repositories.base_repository import BaseRepository
from src.models.hospedaje import Hospedaje

logger = logging.getLogger(__name__)


class HospedajeRepository(BaseRepository):

    def guardar_varios(self, hospedajes: list[Hospedaje]) -> list[int]:
        """Inserta un lote de hospedajes en una sola transacción.

        Args:
            hospedajes: Hospedajes a persistir, en el orden de los ids devueltos.

        Returns:
            Los ids generados, uno por cada hospedaje del lote.

        Raises:
            Exception: Si cualquier inserción del lote falla; la transacción se
                revierte completa (sin filas parciales) y el error original se
                propaga a la capa superior.
        """
        conexion = self._obtener_conexion()
        cursor = conexion.cursor()

        try:
            query = """
                INSERT INTO hospedajes (nombre, tipo, precio_noche, calificacion, direccion, url_reserva, destino_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """
            ids = []

            for hospedaje in hospedajes:
                cursor.execute(
                    query,
                    (
                        hospedaje.nombre, hospedaje.tipo,
                        hospedaje.precio_noche, hospedaje.calificacion,
                        hospedaje.direccion, hospedaje.url_reserva,
                        hospedaje.destino_id
                    )
                )
                ids.append(cursor.fetchone()[0])

            conexion.commit()
            return ids
        except Exception as error:
            conexion.rollback()
            logger.error(f"Error al guardar los hospedajes: {error}")
            raise
        finally:
            cursor.close()
            conexion.close()

    def obtener_por_destino(self, destino_id: int) -> list[Hospedaje]:
        """Recupera todos los hospedajes de un destino.

        Returns:
            Los hospedajes del destino; lista vacía si no hay coincidencias o
            la consulta falla.
        """
        conexion = self._obtener_conexion()
        cursor = conexion.cursor()

        try:
            query = """
                SELECT id, nombre, tipo, precio_noche, calificacion,
                direccion, url_reserva, destino_id FROM hospedajes
                WHERE destino_id = %s;
            """
            cursor.execute(query, (destino_id,))
            filas = cursor.fetchall()

            hospedajes = []
            for fila in filas:
                hospedaje = Hospedaje(
                    id=fila[0],
                    nombre=fila[1],
                    tipo=fila[2],
                    precio_noche=fila[3],
                    calificacion=fila[4],
                    direccion=fila[5],
                    url_reserva=fila[6],
                    destino_id=fila[7]
                )
                hospedajes.append(hospedaje)

            return hospedajes
        except Exception as error:
            logger.error(f"Error al obtener los hospedajes: {error}")
            return []
        finally:
            cursor.close()
            conexion.close()
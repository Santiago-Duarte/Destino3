import logging
from typing import Optional
from src.repositories.base_repository import BaseRepository
from src.models.hospedaje import Hospedaje

logger = logging.getLogger(__name__)


class HospedajeRepository(BaseRepository):

    def guardar(self, hospedaje: Hospedaje) -> Optional[int]:
        """Inserta un hospedaje asociado a su destino.

        Returns:
            El id generado, o ``None`` si ``destino_id`` es ``None`` o el
            ``INSERT`` falla (la transacción se revierte).
        """
        if hospedaje.destino_id is None:
            logger.error("Error al guardar el hospedaje: destino_id es obligatorio")
            return None

        conexion = self._obtener_conexion()
        cursor = conexion.cursor()

        try:
            query = """
                INSERT INTO hospedajes (nombre, tipo, precio_noche, calificacion, direccion, url_reserva, destino_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """
            cursor.execute(
                query,
                (
                    hospedaje.nombre, hospedaje.tipo,
                    hospedaje.precio_noche, hospedaje.calificacion,
                    hospedaje.direccion, hospedaje.url_reserva,
                    hospedaje.destino_id
                )
            )
            hospedaje_id = cursor.fetchone()[0]
            conexion.commit()
            return hospedaje_id
        except Exception as error:
            conexion.rollback()
            logger.error(f"Error al guardar el hospedaje: {error}")
            return None
        finally:
            cursor.close()
            conexion.close()

    def obtener_por_id(self, hospedaje_id: int) -> Optional[Hospedaje]:
        """Recupera un hospedaje por su id.

        Returns:
            El hospedaje encontrado, o ``None`` si no existe o la consulta falla.
        """
        conexion = self._obtener_conexion()
        cursor = conexion.cursor()

        try:
            query = """
                SELECT id, nombre, tipo, precio_noche, calificacion,
                direccion, url_reserva, destino_id FROM hospedajes
                WHERE id = %s;
            """
            cursor.execute(query, (hospedaje_id,))
            fila = cursor.fetchone()

            if fila is None:
                return None

            return Hospedaje(
                id=fila[0],
                nombre=fila[1],
                tipo=fila[2],
                precio_noche=fila[3],
                calificacion=fila[4],
                direccion=fila[5],
                url_reserva=fila[6],
                destino_id=fila[7],
            )
        except Exception as error:
            logger.error(f"Error al obtener el hospedaje: {error}")
            return None
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
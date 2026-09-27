import logging
from typing import Optional
from src.repositories.base_repository import BaseRepository
from src.models.destino import Destino

logger = logging.getLogger(__name__)


class DestinoRepository(BaseRepository):

    def guardar(self, destino: Destino) -> Optional[int]:
        """Inserta un destino validando que ciudad y país no estén vacíos.

        Returns:
            El id generado, o ``None`` si faltan datos obligatorios o el
            ``INSERT`` falla (la transacción se revierte).
        """
        ciudad = (destino.ciudad or "").strip()
        pais = (destino.pais or "").strip()

        if not ciudad or not pais:
            logger.error("Error al guardar el destino: ciudad y pais son obligatorios")
            return None

        conexion = self._obtener_conexion()
        cursor = conexion.cursor()

        try:
            query = "INSERT INTO destinos (ciudad, pais) VALUES (%s, %s) RETURNING id;"
            cursor.execute(query, (ciudad, pais))
            destino_id = cursor.fetchone()[0]
            conexion.commit()
            return destino_id
        except Exception as error:
            conexion.rollback()
            logger.error(f"Error al guardar el destino: {error}")
            return None
        finally:
            cursor.close()
            conexion.close()

    def obtener_todos(self) -> list[Destino]:
        """Recupera la tabla completa de destinos.

        Returns:
            Todos los destinos persistidos; lista vacía si la consulta falla.
        """
        conexion = self._obtener_conexion()
        cursor = conexion.cursor()

        try:
            query = "SELECT id, ciudad, pais FROM destinos;"
            cursor.execute(query)
            filas = cursor.fetchall()

            destinos = []
            for fila in filas:
                destino = Destino(id=fila[0], ciudad=fila[1], pais=fila[2])
                destinos.append(destino)

            return destinos
        except Exception as error:
            logger.error(f"Error al obtener los destinos: {error}")
            return []
        finally:
            cursor.close()
            conexion.close()

    def obtener_o_crear(self, destino: Destino) -> Optional[int]:
        """Devuelve el id de un destino por ciudad/país o lo crea si no existe.

        La búsqueda ignora mayúsculas, espacios sobrantes (índice único
        ``LOWER(TRIM(...))``). Ante una inserción concurrente que dispare el
        conflicto del índice único, se reintenta la consulta para recuperar el
        registro ya insertado por otra transacción.

        Args:
            destino: Destino cuyo id se busca o se crea.

        Returns:
            El id del destino existente o recién creado, o ``None`` si faltan
            datos obligatorios o la operación falla.
        """
        ciudad = (destino.ciudad or "").strip()
        pais = (destino.pais or "").strip()

        if not ciudad or not pais:
            logger.error("Error al obtener o crear el destino: ciudad y pais son obligatorios")
            return None

        conexion = self._obtener_conexion()
        cursor = conexion.cursor()

        try:
            query = "SELECT id FROM destinos WHERE LOWER(TRIM(ciudad)) = LOWER(%s) AND LOWER(TRIM(pais)) = LOWER(%s);"
            cursor.execute(query, (ciudad, pais))
            resultado = cursor.fetchone()
            if resultado:
                conexion.commit()
                return resultado[0]

            cursor.execute(
                "INSERT INTO destinos (ciudad, pais) VALUES (%s, %s) ON CONFLICT DO NOTHING RETURNING id;",
                (ciudad, pais),
            )
            insertado = cursor.fetchone()
            if insertado:
                conexion.commit()
                return insertado[0]

            cursor.execute(query, (ciudad, pais))
            existente = cursor.fetchone()
            if existente:
                conexion.commit()
                return existente[0]

            return None
        except Exception as error:
            conexion.rollback()
            logger.error(f"Error al obtener o crear el destino: {error}")
            return None
        finally:
            cursor.close()
            conexion.close()
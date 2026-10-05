from collections.abc import Iterator
from contextlib import contextmanager

from psycopg2.extensions import connection as ConexionPostgres, cursor as CursorPostgres

from src.config.database import obtener_conexion


class BaseRepository:

    def _obtener_conexion(self) -> ConexionPostgres:
        conexion = obtener_conexion()
        if conexion is None:
            raise ConnectionError("No se pudo establecer conexión con la base de datos")
        return conexion

    @contextmanager
    def _transaccion(self) -> Iterator[CursorPostgres]:
        """Cursor con transacción automática.

        Confirma al salir sin errores, revierte y relanza el error si algo
        falla dentro del bloque, y siempre cierra cursor y conexión.
        """
        conexion = self._obtener_conexion()
        cursor = conexion.cursor()
        try:
            yield cursor
            conexion.commit()
        except Exception:
            conexion.rollback()
            raise
        finally:
            cursor.close()
            conexion.close()

from collections.abc import Iterator
from contextlib import contextmanager

from psycopg2.extensions import connection as ConexionPostgres
from psycopg2.extensions import cursor as CursorPostgres

from src.config.database import obtener_conexion
from src.exceptions import PersistenciaError


class BaseRepository:

    def _obtener_conexion(self) -> ConexionPostgres:
        conexion = obtener_conexion()
        if conexion is None:
            raise PersistenciaError(
                "PostgreSQL",
                "conexion",
                "No se pudo establecer conexión con la base de datos",
            )
        return conexion

    @contextmanager
    def _transaccion(self) -> Iterator[CursorPostgres]:
        conexion = self._obtener_conexion()
        try:
            cursor = conexion.cursor()
        except Exception:
            conexion.close()
            raise
        try:
            yield cursor
            conexion.commit()
        except Exception:
            conexion.rollback()
            raise
        finally:
            cursor.close()
            conexion.close()

from abc import ABC
import logging
from psycopg2.extensions import connection as ConexionPostgres
from src.config.database import obtener_conexion

logger = logging.getLogger(__name__)


class BaseRepository(ABC):

    def _obtener_conexion(self) -> ConexionPostgres:
        conexion = obtener_conexion()
        if conexion is None:
            raise ConnectionError("No se pudo establecer conexión con la base de datos")
        return conexion
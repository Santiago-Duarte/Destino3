import os
import logging
from collections.abc import Iterator
from contextlib import contextmanager
import psycopg2
from psycopg2.extensions import connection as ConexionPostgres

logger = logging.getLogger(__name__)


def obtener_conexion() -> ConexionPostgres | None:
    """Establece una conexión a PostgreSQL eligiendo la base según el entorno activo.

    Selecciona ``DB_TEST_NAME`` cuando ``ENVIRONMENT=testing``; en cualquier otro
    caso usa ``DB_NAME``. Todos los fallos (red, credenciales, variables de
    entorno ausentes) se tragan y se registran en el log.

    Returns:
        La conexión abierta, o ``None`` si la conexión falla por cualquier motivo.
    """
    entorno = os.getenv('ENVIRONMENT', 'development')

    if entorno == 'testing':
        base_de_datos = 'DB_TEST_NAME'
    else:
        base_de_datos = 'DB_NAME'

    try:
        conexion = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            database=os.getenv(base_de_datos),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )

        return conexion

    except Exception as e:
        logger.error(f"Error al conectar a la base de datos: {e}")
        return None


@contextmanager
def conexion_manager() -> Iterator[ConexionPostgres]:
    """Expone una conexión como context manager con transacción automática.

    Confirma la transacción al salir sin errores, la revierte si se propaga una
    excepción y siempre cierra la conexión en el bloque ``finally``.

    Yields:
        La conexión abierta, lista para ejecutar sentencias SQL.

    Raises:
        ConnectionError: Si ``obtener_conexion`` devuelve ``None``.
    """
    conexion = obtener_conexion()
    if conexion is None:
        raise ConnectionError("No se pudo establecer conexión con la base de datos")
    
    try:
        yield conexion
        conexion.commit()
    except Exception as e:
        conexion.rollback()
        raise e
    finally:
        conexion.close()
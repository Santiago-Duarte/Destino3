import os
import logging
from contextlib import contextmanager
import psycopg2

logger = logging.getLogger(__name__)


def obtener_conexion():
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
def conexion_manager():
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
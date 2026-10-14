import logging
import os

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
    base_de_datos = 'DB_TEST_NAME' if entorno == 'testing' else 'DB_NAME'

    try:
        return psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            database=os.getenv(base_de_datos),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
    except Exception as e:
        logger.error("Error al conectar a la base de datos: tipo=%s", type(e).__name__)
        return None

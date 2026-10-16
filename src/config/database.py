import logging
import os

import psycopg2
from psycopg2.extensions import connection as ConexionPostgres

logger = logging.getLogger(__name__)

_CONFIGURACION_BD: dict[str, tuple[str, str, str]] = {
    "testing": ("DB_TEST_NAME", "DB_TEST_USER", "DB_TEST_PASSWORD"),
    "demo": ("DB_DEMO_NAME", "DB_DEMO_USER", "DB_DEMO_PASSWORD"),
    "production": (
        "DB_PRODUCTION_NAME",
        "DB_PRODUCTION_USER",
        "DB_PRODUCTION_PASSWORD",
    ),
}


def obtener_conexion() -> ConexionPostgres | None:
    """Establece una conexión usando las credenciales del entorno activo.

    ``testing`` usa ``destino3_test_db``, ``demo`` usa ``demo_db`` y
    ``production`` usa ``destino3_db``. Un entorno no soportado se rechaza antes
    de conectar.

    Returns:
        La conexión abierta, o ``None`` si la conexión falla por cualquier motivo.
    """
    entorno = os.getenv("ENVIRONMENT")
    try:
        variable_base, variable_usuario, variable_password = _CONFIGURACION_BD[entorno]
    except KeyError as error:
        raise ValueError(f"Entorno no soportado: {entorno!r}") from error

    variables_requeridas = (
        "DB_HOST",
        "DB_PORT",
        variable_base,
        variable_usuario,
        variable_password,
    )
    faltantes = [nombre for nombre in variables_requeridas if not os.getenv(nombre)]
    if faltantes:
        raise ValueError(
            f"Faltan variables de conexión para el entorno {entorno!r}: "
            f"{', '.join(faltantes)}"
        )

    try:
        return psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv(variable_base),
            user=os.getenv(variable_usuario),
            password=os.getenv(variable_password),
        )
    except Exception as error:
        logger.error("Error al conectar a la base de datos: tipo=%s", type(error).__name__)
        return None

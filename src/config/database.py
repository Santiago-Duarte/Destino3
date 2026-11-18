import logging
import os

import psycopg2
from psycopg2.extensions import connection as ConexionPostgres

logger = logging.getLogger(__name__)

_VARIABLES_POR_ENTORNO: dict[str, tuple[str, str, str]] = {
    "testing": ("DB_TEST_NAME", "DB_TEST_USER", "DB_TEST_PASSWORD"),
    "demo": ("DB_DEMO_NAME", "DB_DEMO_USER", "DB_DEMO_PASSWORD"),
    "production": (
        "DB_PRODUCTION_NAME",
        "DB_PRODUCTION_USER",
        "DB_PRODUCTION_PASSWORD",
    ),
}


def obtener_conexion() -> ConexionPostgres | None:
    entorno = os.getenv("ENVIRONMENT")
    try:
        variable_nombre_bd, variable_usuario, variable_clave = _VARIABLES_POR_ENTORNO[entorno]
    except KeyError as error:
        raise ValueError(f"Entorno no soportado: {entorno!r}") from error

    variables_requeridas = (
        "DB_HOST",
        "DB_PORT",
        variable_nombre_bd,
        variable_usuario,
        variable_clave,
    )
    variables_faltantes = [
        nombre for nombre in variables_requeridas if not os.getenv(nombre)
    ]
    if variables_faltantes:
        raise ValueError(
            f"Faltan variables de conexión para el entorno {entorno!r}: "
            f"{', '.join(variables_faltantes)}"
        )

    try:
        return psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv(variable_nombre_bd),
            user=os.getenv(variable_usuario),
            password=os.getenv(variable_clave),
        )
    except Exception as error:
        logger.error("Error al conectar a la base de datos: tipo=%s", type(error).__name__)
        return None

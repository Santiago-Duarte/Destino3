"""Orquestador operacional del reset único de la BD real (spec 004, H4).

Artefacto operacional fuera de ``src/`` y sin interfaz pública (plan D4).
Ejecuta una sola vez (RF-9) el procedimiento transaccional de
``operacion/reset/procedimiento.py`` con dos conexiones separadas (decisión
operativa de H4):

1. Conexión de la aplicación con el rol de production
   (``destino3_production``): ``ejecutar_preflight`` valida base, rol e
   inventario de tablas antes de cualquier escritura (H1).
2. Conexión operativa con el rol dueño de las tablas (``postgres``), único
   rol capaz de ``TRUNCATE`` y de aplicar el esquema nuevo sobre las tablas
   existentes: ``ejecutar_reset_unico`` valida la base y ejecuta el vaciado,
   el esquema y la confirmación en una única transacción (RF-1, RF-2, RF-5).

Sin respaldo previo y sin confirmación humana adicional: única ejecución
autorizada por la decisión 14 de ``docs/contexto-v2-fuentes-de-verdad.md``.
"""

import logging
import os

import psycopg2

from operacion.reset.preflight import ejecutar_preflight
from operacion.reset.procedimiento import ejecutar_reset_unico
from src.config.database import obtener_conexion

logger = logging.getLogger(__name__)


def ejecutar_reset_operacional() -> str:
    """Ejecuta el reset único con preflight de production y transacción del dueño.

    Returns:
        El nombre de la base de production vaciada.

    Raises:
        Exception: cualquier fallo del preflight o de la transacción se
            propaga; el procedimiento ya revirtió y la base quedó intacta.
    """
    logger.info("Orquestador del reset único: abriendo conexión de production")
    conexion_validacion = obtener_conexion()
    if conexion_validacion is None:
        raise ConnectionError("No se pudo abrir la conexión de production")
    try:
        ejecutar_preflight(conexion_validacion)
    finally:
        conexion_validacion.close()

    logger.info("Orquestador del reset único: abriendo conexión operativa del dueño")
    conexion_operativa = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_PRODUCTION_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )
    try:
        return ejecutar_reset_unico(conexion_operativa)
    finally:
        conexion_operativa.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"Reset único completado sobre: {ejecutar_reset_operacional()}")
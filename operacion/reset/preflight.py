"""Preflight del procedimiento único de reset de la base de datos real (spec 004).

Artefacto operacional fuera de ``src/`` (plan D4): no forma parte de la
interfaz pública de la aplicación y se retira tras la única ejecución del
reset (H4). Valida, antes de iniciar la transacción (``BEGIN``), que la
conexión sea la base y el rol de production y que el inventario de tablas
públicas coincida con las siete tablas de dominio del esquema canónico; ante
cualquier desviación aborta (RF-1, RF-2, RF-5, RF-9; constitución #6).
"""

import logging
import os

from psycopg2.extensions import connection as ConexionPostgres

from src.exceptions import Destino3Error

logger = logging.getLogger(__name__)

INVENTARIO_TABLAS_DOMINIO = (
    "busquedas",
    "recomendaciones",
    "evaluaciones_ia",
    "atracciones",
    "hospedajes",
    "destinos",
    "usuarios",
)

_CONSULTA_IDENTIDAD = "SELECT current_database(), current_user"
_CONSULTA_TABLAS_PUBLICAS = "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"


class PreflightResetError(Destino3Error):
    """El preflight del reset abortó: la conexión o el inventario no son los esperados."""


def ejecutar_preflight(conexion: ConexionPostgres) -> None:
    """Ejecuta el preflight completo del reset antes de iniciar la transacción.

    Valida primero la base y el rol de production y después el inventario
    de tablas públicas; ante la primera desviación aborta sin seguir
    consultando.

    Args:
        conexion: conexión abierta sobre la que se ejecutará el reset.

    Raises:
        PreflightResetError: si la conexión no es la base y el rol de
            production o si las tablas públicas no coinciden con el
            inventario de dominio.
    """
    validar_conexion_production(conexion)
    validar_inventario_tablas_publicas(conexion)
    logger.info(
        "Preflight del reset superado: base y rol de production con el inventario esperado"
    )


def validar_conexion_production(conexion: ConexionPostgres) -> None:
    """Aborta si la conexión no es la base y el rol de production.

    Compara ``current_database()`` y ``current_user`` contra las variables
    ``DB_PRODUCTION_NAME`` y ``DB_PRODUCTION_USER``; sin fallback (plan D6).

    Args:
        conexion: conexión abierta a validar.

    Raises:
        PreflightResetError: si falta la configuración de production o si la
            conexión apunta a otra base u otro rol.
    """
    base_esperada = os.getenv("DB_PRODUCTION_NAME")
    rol_esperado = os.getenv("DB_PRODUCTION_USER")
    if not base_esperada or not rol_esperado:
        raise PreflightResetError(
            "PostgreSQL",
            "preflight_reset",
            "faltan las variables DB_PRODUCTION_NAME o DB_PRODUCTION_USER",
        )

    base_actual, rol_actual = _consultar_identidad(conexion)
    if base_actual != base_esperada or rol_actual != rol_esperado:
        raise PreflightResetError(
            "PostgreSQL",
            "preflight_reset",
            f"conexión distinta: base={base_actual!r} rol={rol_actual!r}",
        )
    logger.info("Preflight: la conexión usa la base y el rol de production")


def validar_inventario_tablas_publicas(conexion: ConexionPostgres) -> None:
    """Aborta si las tablas del esquema public no son el inventario de dominio.

    Args:
        conexion: conexión abierta ya validada como production.

    Raises:
        PreflightResetError: si hay una tabla pública inesperada o si falta
            una tabla de dominio del inventario.
    """
    tablas_actuales = {nombre for (nombre,) in _consultar_tablas_publicas(conexion)}
    tablas_esperadas = set(INVENTARIO_TABLAS_DOMINIO)
    if tablas_actuales != tablas_esperadas:
        inesperadas = sorted(tablas_actuales - tablas_esperadas)
        faltantes = sorted(tablas_esperadas - tablas_actuales)
        raise PreflightResetError(
            "PostgreSQL",
            "preflight_reset",
            f"tablas públicas distintas del inventario: inesperadas={inesperadas} "
            f"faltantes={faltantes}",
        )
    logger.info("Preflight: las tablas públicas coinciden con el inventario de dominio")


def _consultar_identidad(conexion: ConexionPostgres) -> tuple[str, str]:
    """Consulta la base y el rol actuales de la conexión.

    Args:
        conexion: conexión abierta.

    Returns:
        Par ``(base, rol)`` reportados por PostgreSQL.
    """
    cursor = conexion.cursor()
    try:
        cursor.execute(_CONSULTA_IDENTIDAD)
        base, rol = cursor.fetchone()
    finally:
        cursor.close()
    return base, rol


def _consultar_tablas_publicas(conexion: ConexionPostgres) -> list[tuple[str]]:
    """Consulta las tablas del esquema public.

    Args:
        conexion: conexión abierta.

    Returns:
        Filas con el nombre de cada tabla pública.
    """
    cursor = conexion.cursor()
    try:
        cursor.execute(_CONSULTA_TABLAS_PUBLICAS)
        return cursor.fetchall()
    finally:
        cursor.close()
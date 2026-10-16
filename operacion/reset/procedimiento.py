"""Procedimiento transaccional del reset único de la base de datos real (spec 004).

Artefacto operacional fuera de ``src/`` y sin interfaz pública (plan D4):
una sola ejecución autorizada por la spec 004, sin respaldo previo y sin
confirmación humana adicional (decisión 14 de
``docs/contexto-v2-fuentes-de-verdad.md``). En una única transacción
PostgreSQL (plan D3): preflight (H1) → vaciado de las siete tablas de dominio
conservando la estructura (RF-1) → aplicación del esquema nuevo con la
migración aditiva (RF-5) → confirmación. Cualquier fallo revierte la
transacción completa y se propaga (RF-2): la base queda exactamente como
estaba, sin segunda ejecución (RF-9).
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from psycopg2.extensions import connection as ConexionPostgres

from operacion.reset.preflight import (
    INVENTARIO_TABLAS_DOMINIO,
    PreflightResetError,
    _consultar_identidad,
    validar_inventario_tablas_publicas,
)
from src.exceptions import Destino3Error

logger = logging.getLogger(__name__)

RUTA_RAIZ = Path(__file__).resolve().parents[2]
RUTA_MIGRACION_ESQUEMA = RUTA_RAIZ / "sql" / "migrations" / "002_google_place_id.sql"
RUTA_EVIDENCIA = Path(__file__).resolve().parent / "evidencia_reset.json"

_SENTENCIA_VACIADO = (
    "TRUNCATE TABLE " + ", ".join(INVENTARIO_TABLAS_DOMINIO) + " CASCADE"
)


class ResetYaEjecutadoError(Destino3Error):
    """El reset único de la spec 004 ya fue ejecutado y no puede repetirse (RF-9)."""


def ejecutar_reset_unico(conexion: ConexionPostgres) -> str:
    """Ejecuta el reset único de la BD real en una sola transacción.

    Antes de escribir exige que no exista evidencia de una ejecución previa
    (RF-9) y valida que la conexión apunte a la base de production con el
    inventario de tablas de dominio; el rol de producción se valida con el
    preflight sobre la conexión de la aplicación (ver
    ``operacion/reset/ejecutar.py``). El vaciado de las siete tablas y la
    migración de esquema ocurren dentro de la única transacción de la
    conexión (la implícita de psycopg2): si todo termina confirma y
    registra la evidencia; ante cualquier fallo revierte y propaga la
    excepción (RF-2), sin segunda ejecución.

    Args:
        conexion: conexión operativa abierta contra la base de production.

    Returns:
        El nombre de la base vaciada.

    Raises:
        ResetYaEjecutadoError: si la evidencia de una ejecución previa existe.
        PreflightResetError: si la conexión no apunta a la base de production
            o si el inventario de tablas públicas no es el esperado.
    """
    _exigir_sin_ejecucion_previa()
    base = _validar_base_production(conexion)
    validar_inventario_tablas_publicas(conexion)
    sentencias_esquema = _leer_sentencias_esquema()

    cursor = conexion.cursor()
    try:
        cursor.execute(_SENTENCIA_VACIADO)
        for sentencia in sentencias_esquema:
            cursor.execute(sentencia)
        conexion.commit()
    except Exception as error:
        conexion.rollback()
        logger.error("El reset único falló y se revirtió: tipo=%s", type(error).__name__)
        raise
    finally:
        cursor.close()

    _registrar_evidencia(base)
    logger.info("Reset único completado: una transacción con vaciado y esquema nuevo")
    return base


def _validar_base_production(conexion: ConexionPostgres) -> str:
    """Aborta si la conexión operativa no apunta a la base de production.

    La conexión operativa pertenece al rol dueño de las tablas (decisión
    operativa de H4); el rol de la aplicación se valida aparte con el
    preflight de ``operacion/reset/preflight.py``.

    Args:
        conexion: conexión operativa abierta.

    Returns:
        El nombre de la base validada.

    Raises:
        PreflightResetError: si falta la variable ``DB_PRODUCTION_NAME`` o si
            la conexión apunta a otra base.
    """
    base_esperada = os.getenv("DB_PRODUCTION_NAME")
    if not base_esperada:
        raise PreflightResetError(
            "PostgreSQL",
            "reset_unico",
            "falta la variable DB_PRODUCTION_NAME",
        )
    base_actual, _rol = _consultar_identidad(conexion)
    if base_actual != base_esperada:
        raise PreflightResetError(
            "PostgreSQL",
            "reset_unico",
            f"conexión distinta: base={base_actual!r}",
        )
    return base_actual


def _exigir_sin_ejecucion_previa() -> None:
    """Aborta si el reset único ya tiene evidencia de una ejecución anterior.

    Raises:
        ResetYaEjecutadoError: si existe la evidencia de una ejecución previa.
    """
    if RUTA_EVIDENCIA.exists():
        raise ResetYaEjecutadoError(
            "PostgreSQL",
            "reset_unico",
            "ya existe evidencia de una ejecución previa; el reset no se repite",
        )


def _leer_sentencias_esquema() -> list[str]:
    """Lee las sentencias de la migración aditiva del esquema nuevo.

    Returns:
        Las sentencias SQL de ``sql/migrations/002_google_place_id.sql``.

    Raises:
        OSError: si la migración no se puede leer.
    """
    texto = RUTA_MIGRACION_ESQUEMA.read_text(encoding="utf-8")
    sentencias = []
    for parte in texto.split(";"):
        contenido = "\n".join(
            linea
            for linea in parte.splitlines()
            if not linea.strip().startswith("--")
        ).strip()
        if contenido:
            sentencias.append(contenido)
    return sentencias


def _registrar_evidencia(base: str) -> None:
    """Registra en disco la evidencia del reset único ya confirmado.

    La evidencia impide ejecuciones posteriores (RF-9) y deja trazable la
    única transacción con su fecha, base, tablas vaciadas y esquema aplicado.

    Args:
        base: nombre de la base de production vaciada.
    """
    evidencia = {
        "fecha": datetime.now(timezone.utc).isoformat(),
        "base": base,
        "transaccion": "unica",
        "tablas": list(INVENTARIO_TABLAS_DOMINIO),
        "esquema": RUTA_MIGRACION_ESQUEMA.name,
    }
    RUTA_EVIDENCIA.write_text(
        json.dumps(evidencia, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
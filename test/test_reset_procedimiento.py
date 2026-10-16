import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from operacion.reset import ejecutar, procedimiento
from operacion.reset.preflight import INVENTARIO_TABLAS_DOMINIO
from src.config import database

TABLAS_DOMINIO = (
    "busquedas",
    "recomendaciones",
    "evaluaciones_ia",
    "atracciones",
    "hospedajes",
    "destinos",
    "usuarios",
)

VARIABLES_PRODUCTION = {
    "DB_PRODUCTION_NAME": "destino3_db",
    "DB_PRODUCTION_USER": "usuario_production",
}

VARIABLES_COMPLETAS = {
    "ENVIRONMENT": "production",
    "DB_HOST": "localhost",
    "DB_PORT": "5432",
    "DB_PRODUCTION_NAME": "destino3_db",
    "DB_PRODUCTION_USER": "usuario_production",
    "DB_PRODUCTION_PASSWORD": "password-production",
    "DB_USER": "usuario_dueño",
    "DB_PASSWORD": "password-dueño",
}


class CursorFalso:
    """Cursor que registra cada sentencia y falla en la sentencia indicada."""

    def __init__(self, conexion):
        self._conexion = conexion
        self._resultados = []

    def execute(self, sentencia, *_parametros):
        self._conexion.sentencias.append(sentencia)
        if self._conexion.fallar_en and self._conexion.fallar_en in sentencia:
            raise RuntimeError("fallo inducido")
        if "current_database" in sentencia:
            self._resultados = [(self._conexion.base, self._conexion.rol)]
        elif "pg_tables" in sentencia:
            self._resultados = [(nombre,) for nombre in self._conexion.tablas]

    def fetchone(self):
        return self._resultados[0]

    def fetchall(self):
        return self._resultados

    def close(self):
        return None


class ConexionFalsa:
    """Conexión falsa que registra el ciclo transaccional sin tocar PostgreSQL."""

    def __init__(self, base, rol, tablas=(), fallar_en=None):
        self.base = base
        self.rol = rol
        self.tablas = tuple(tablas)
        self.fallar_en = fallar_en
        self.sentencias = []
        self.commits = 0
        self.rollbacks = 0
        self.autocommit = False

    def cursor(self):
        return CursorFalso(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        return None


class TestProcedimientoTransaccional(unittest.TestCase):

    def setUp(self):
        directorio = tempfile.TemporaryDirectory()
        self.addCleanup(directorio.cleanup)
        parche = patch.object(
            procedimiento,
            "RUTA_EVIDENCIA",
            Path(directorio.name) / "evidencia_reset.json",
        )
        parche.start()
        self.addCleanup(parche.stop)

    def test_reset_ejecuta_vaciado_esquema_y_commit_en_una_transaccion(self):
        conexion = ConexionFalsa("destino3_db", "usuario_production", tablas=TABLAS_DOMINIO)
        with patch.dict(os.environ, VARIABLES_PRODUCTION, clear=True):
            procedimiento.ejecutar_reset_unico(conexion)

        vaciados = [s for s in conexion.sentencias if "TRUNCATE" in s]
        self.assertEqual(len(vaciados), 1)
        for tabla in TABLAS_DOMINIO:
            self.assertIn(tabla, vaciados[0])
        alteraciones = [s for s in conexion.sentencias if "ALTER TABLE" in s]
        self.assertEqual(len(alteraciones), 1)
        indices = [s for s in conexion.sentencias if "CREATE UNIQUE INDEX" in s]
        self.assertEqual(len(indices), 1)
        posicion_vaciado = conexion.sentencias.index(vaciados[0])
        posicion_alteracion = conexion.sentencias.index(alteraciones[0])
        self.assertLess(posicion_vaciado, posicion_alteracion)
        self.assertEqual(conexion.commits, 1)
        self.assertEqual(conexion.rollbacks, 0)
        self.assertTrue(procedimiento.RUTA_EVIDENCIA.exists())
        evidencia = json.loads(procedimiento.RUTA_EVIDENCIA.read_text(encoding="utf-8"))
        self.assertEqual(evidencia["base"], "destino3_db")
        self.assertEqual(evidencia["transaccion"], "unica")
        self.assertEqual(tuple(evidencia["tablas"]), TABLAS_DOMINIO)
        self.assertIn("fecha", evidencia)

    def test_reset_propaga_error_con_rollback_y_sin_reintentos(self):
        conexion = ConexionFalsa(
            "destino3_db", "usuario_production", tablas=TABLAS_DOMINIO, fallar_en="ALTER TABLE"
        )
        with patch.dict(os.environ, VARIABLES_PRODUCTION, clear=True):
            with self.assertRaises(RuntimeError):
                procedimiento.ejecutar_reset_unico(conexion)

        vaciados = [s for s in conexion.sentencias if "TRUNCATE" in s]
        self.assertEqual(len(vaciados), 1)
        alteraciones = [s for s in conexion.sentencias if "ALTER TABLE" in s]
        self.assertEqual(len(alteraciones), 1)
        indice_fallo = next(
            i for i, sentencia in enumerate(conexion.sentencias) if "ALTER TABLE" in sentencia
        )
        self.assertEqual(conexion.sentencias[indice_fallo + 1:], [])
        self.assertEqual(conexion.rollbacks, 1)
        self.assertEqual(conexion.commits, 0)
        self.assertFalse(procedimiento.RUTA_EVIDENCIA.exists())

    def test_reset_rechazado_si_ya_fue_ejecutado(self):
        conexion = ConexionFalsa("destino3_db", "usuario_production", tablas=TABLAS_DOMINIO)
        with patch.dict(os.environ, VARIABLES_PRODUCTION, clear=True):
            procedimiento.ejecutar_reset_unico(conexion)
            with self.assertRaises(procedimiento.ResetYaEjecutadoError):
                procedimiento.ejecutar_reset_unico(conexion)

        self.assertEqual(conexion.commits, 1)

    def test_reset_aborta_en_preflight_sin_abrir_transaccion(self):
        conexion = ConexionFalsa("destino3_test_db", "usuario_production", tablas=TABLAS_DOMINIO)
        with patch.dict(os.environ, VARIABLES_PRODUCTION, clear=True):
            with self.assertRaises(procedimiento.PreflightResetError):
                procedimiento.ejecutar_reset_unico(conexion)

        vaciados = [s for s in conexion.sentencias if "TRUNCATE" in s]
        self.assertEqual(vaciados, [])
        self.assertEqual(conexion.commits, 0)
        self.assertEqual(conexion.rollbacks, 0)


class TestEjecutarOrquestador(unittest.TestCase):

    def setUp(self):
        directorio = tempfile.TemporaryDirectory()
        self.addCleanup(directorio.cleanup)
        parche = patch.object(
            procedimiento,
            "RUTA_EVIDENCIA",
            Path(directorio.name) / "evidencia_reset.json",
        )
        parche.start()
        self.addCleanup(parche.stop)

    def test_orquestador_preflight_con_production_y_transaccion_como_dueño(self):
        conexion_production = ConexionFalsa(
            "destino3_db", "usuario_production", tablas=TABLAS_DOMINIO
        )
        conexion_operativa = ConexionFalsa(
            "destino3_db", "usuario_dueño", tablas=TABLAS_DOMINIO
        )

        with patch.dict(os.environ, VARIABLES_COMPLETAS, clear=True):
            with patch.object(
                database.psycopg2, "connect", side_effect=[conexion_production, conexion_operativa]
            ) as conectar:
                ejecutar.ejecutar_reset_operacional()

        self.assertEqual(conectar.call_count, 2)
        base_llamada = conectar.call_args_list[0].kwargs["database"]
        self.assertEqual(base_llamada, "destino3_db")
        self.assertEqual(
            conectar.call_args_list[0].kwargs["user"], "usuario_production"
        )
        self.assertEqual(
            conectar.call_args_list[1].kwargs["user"], "usuario_dueño"
        )
        self.assertEqual(conexion_operativa.commits, 1)
        self.assertEqual(conexion_operativa.rollbacks, 0)
        self.assertTrue(procedimiento.RUTA_EVIDENCIA.exists())

    def test_orquestador_aborta_si_el_preflight_de_production_falla(self):
        conexion_production = ConexionFalsa(
            "demo_db", "usuario_production", tablas=TABLAS_DOMINIO
        )

        with patch.dict(os.environ, VARIABLES_COMPLETAS, clear=True):
            with patch.object(
                database.psycopg2, "connect", side_effect=[conexion_production]
            ) as conectar:
                with self.assertRaises(procedimiento.PreflightResetError):
                    ejecutar.ejecutar_reset_operacional()

        self.assertEqual(conectar.call_count, 1)
        begins = [
            s for s in conexion_production.sentencias if s.strip() == "BEGIN"
        ]
        self.assertEqual(begins, [])
        self.assertEqual(conexion_production.commits, 0)
        self.assertEqual(conexion_production.rollbacks, 0)
        self.assertFalse(procedimiento.RUTA_EVIDENCIA.exists())

    def test_no_contiene_backup_reintentos_ni_restauracion(self):
        fuente = Path(procedimiento.__file__).read_text(encoding="utf-8")

        self.assertNotIn("backup", fuente.lower())
        self.assertNotIn("restore", fuente.lower())
        self.assertNotIn("retry", fuente.lower())
        self.assertNotIn("while True", fuente)
        self.assertIn("INVENTARIO_TABLAS_DOMINIO", fuente)


if __name__ == "__main__":
    unittest.main()

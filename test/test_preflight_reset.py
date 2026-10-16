import os
import unittest
from unittest.mock import patch

from operacion.reset.preflight import (
    INVENTARIO_TABLAS_DOMINIO,
    PreflightResetError,
    ejecutar_preflight,
    validar_conexion_production,
    validar_inventario_tablas_publicas,
)

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


class CursorFalso:
    """Cursor que responde las consultas de identidad e inventario del preflight."""

    def __init__(self, conexion):
        self._conexion = conexion
        self._resultados = []

    def execute(self, sentencia, *_parametros):
        self._conexion.consultas.append(sentencia)
        if "current_database" in sentencia:
            self._resultados = [(self._conexion.base, self._conexion.rol)]
        elif "pg_tables" in sentencia:
            self._resultados = [(nombre,) for nombre in self._conexion.tablas]
        else:
            raise AssertionError(f"Consulta inesperada del preflight: {sentencia}")

    def fetchone(self):
        return self._resultados[0]

    def fetchall(self):
        return self._resultados

    def close(self):
        return None


class ConexionFalsa:
    """Conexión falsa que no toca PostgreSQL: solo registra lo que se consulta."""

    def __init__(self, base, rol, tablas=()):
        self.base = base
        self.rol = rol
        self.tablas = tuple(tablas)
        self.consultas = []

    def cursor(self):
        return CursorFalso(self)


class TestInventarioTablasDominio(unittest.TestCase):

    def test_el_inventario_documenta_las_siete_tablas_de_dominio(self):
        self.assertEqual(set(INVENTARIO_TABLAS_DOMINIO), set(TABLAS_DOMINIO))


class TestValidarConexionProduction(unittest.TestCase):

    def test_conexion_de_production_pasa(self):
        conexion = ConexionFalsa("destino3_db", "usuario_production")
        with patch.dict(os.environ, VARIABLES_PRODUCTION, clear=True):
            validar_conexion_production(conexion)

    def test_base_distinta_aborta(self):
        conexion = ConexionFalsa("destino3_test_db", "usuario_production")
        with patch.dict(os.environ, VARIABLES_PRODUCTION, clear=True):
            with self.assertRaises(PreflightResetError):
                validar_conexion_production(conexion)

    def test_rol_distinto_aborta(self):
        conexion = ConexionFalsa("destino3_db", "usuario_testing")
        with patch.dict(os.environ, VARIABLES_PRODUCTION, clear=True):
            with self.assertRaises(PreflightResetError):
                validar_conexion_production(conexion)

    def test_variables_de_production_ausentes_aborta(self):
        conexion = ConexionFalsa("destino3_db", "usuario_production")
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(PreflightResetError):
                validar_conexion_production(conexion)


class TestValidarInventarioTablasPublicas(unittest.TestCase):

    def test_inventario_exacto_pasa(self):
        conexion = ConexionFalsa("destino3_db", "usuario_production", tablas=TABLAS_DOMINIO)
        validar_inventario_tablas_publicas(conexion)

    def test_tabla_publica_inesperada_aborta(self):
        conexion = ConexionFalsa(
            "destino3_db", "usuario_production", tablas=TABLAS_DOMINIO + ("tabla_ajena",)
        )
        with self.assertRaises(PreflightResetError):
            validar_inventario_tablas_publicas(conexion)

    def test_falta_una_tabla_de_dominio_aborta(self):
        conexion = ConexionFalsa("destino3_db", "usuario_production", tablas=TABLAS_DOMINIO[:-1])
        with self.assertRaises(PreflightResetError):
            validar_inventario_tablas_publicas(conexion)


class TestEjecutarPreflight(unittest.TestCase):

    def test_preflight_completo_pasa_con_produccion_e_inventario_exacto(self):
        conexion = ConexionFalsa("destino3_db", "usuario_production", tablas=TABLAS_DOMINIO)
        with patch.dict(os.environ, VARIABLES_PRODUCTION, clear=True):
            ejecutar_preflight(conexion)

        self.assertEqual(len(conexion.consultas), 2)

    def test_conexion_distinta_aborta_sin_consultar_el_inventario(self):
        conexion = ConexionFalsa("demo_db", "usuario_demo", tablas=TABLAS_DOMINIO)
        with patch.dict(os.environ, VARIABLES_PRODUCTION, clear=True):
            with self.assertRaises(PreflightResetError):
                ejecutar_preflight(conexion)

        consultas_de_tablas = [c for c in conexion.consultas if "pg_tables" in c]
        self.assertEqual(consultas_de_tablas, [])


if __name__ == "__main__":
    unittest.main()
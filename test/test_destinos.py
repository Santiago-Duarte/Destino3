import os
os.environ['ENVIRONMENT'] = 'testing'

import unittest
from unittest.mock import MagicMock, patch

from test.db_test_case import BaseDBTestCase

from src.models.destino import Destino
from src.services.db_service import (
    guardar_destino,
    obtener_destinos,
    obtener_o_crear_destino,
)


class TestDestinos(BaseDBTestCase):

    def test_guardar_y_obtener_destino(self):
        destino_id = self.crear_destino()

        destinos = obtener_destinos()

        self.assertEqual(len(destinos), 1)
        destino = destinos[0]
        self.assertEqual(destino.id, destino_id)
        self.assertEqual(destino.ciudad, "Medellin")
        self.assertEqual(destino.pais, "Colombia")

    def test_obtener_destinos_sin_registros(self):
        self.assertEqual(obtener_destinos(), [])

    def test_obtener_destinos_con_varios_registros(self):
        self.crear_destino(ciudad="Medellin", pais="Colombia")
        self.crear_destino(ciudad="Bogota", pais="Colombia")
        self.crear_destino(ciudad="Buenos Aires", pais="Argentina")

        destinos = obtener_destinos()

        self.assertEqual(len(destinos), 3)
        self.assertEqual({d.ciudad for d in destinos},
                         {"Medellin", "Bogota", "Buenos Aires"})

    def test_guardar_destino_con_caracteres_especiales(self):
        self.crear_destino(ciudad="Ciudad de México", pais="México")

        destinos = obtener_destinos()

        self.assertEqual(len(destinos), 1)
        self.assertEqual(destinos[0].ciudad, "Ciudad de México")
        self.assertEqual(destinos[0].pais, "México")

    def test_guardar_destino_invalido_devuelve_none_y_no_guarda(self):
        resultado = guardar_destino(Destino(ciudad=None, pais="Colombia"))

        self.assertIsNone(resultado)
        self.assertEqual(obtener_destinos(), [])

    def test_crear_destino_cuando_no_existe(self):
        nuevo_destino = Destino(ciudad="medellin", pais="colombia")

        resultado = obtener_o_crear_destino(nuevo_destino)
        destinos = obtener_destinos()

        self.assertIsInstance(resultado, int)
        self.assertEqual(len(destinos), 1)
        self.assertEqual(destinos[0].ciudad, "medellin")
        self.assertEqual(destinos[0].pais, "colombia")

    def test_llamar_dos_veces_la_misma_ciudad_devuelve_el_mismo_id(self):
        nuevo_destino = Destino(ciudad="Medellin", pais="Colombia")

        resultado1 = obtener_o_crear_destino(nuevo_destino)
        resultado2 = obtener_o_crear_destino(nuevo_destino)

        self.assertEqual(len(obtener_destinos()), 1)
        self.assertEqual(resultado1, resultado2)

    def test_no_se_crea_destino_porque_es_invalido(self):
        self.assertIsNone(obtener_o_crear_destino(Destino(ciudad=None, pais="Colombia")))
        self.assertIsNone(obtener_o_crear_destino(Destino(ciudad="", pais="Colombia")))

        self.assertEqual(obtener_destinos(), [])

    def test_no_se_crea_destino_con_solo_espacios(self):
        self.assertIsNone(obtener_o_crear_destino(Destino(ciudad="   ", pais="Colombia")))

        self.assertEqual(obtener_destinos(), [])


class TestObtenerOCrearDestinoCarrera(unittest.TestCase):
    """Rama carrera db_service.py:161-169: INSERT ON CONFLICT DO NOTHING sin RETURNING -> segundo SELECT"""

    @patch("src.services.db_service.obtener_conexion")
    def test_rama_carrera_on_conflict_do_nothing_segundo_select(self, mock_obtener_conexion):
        # Arrange: conexion y cursor mockeados para simular carrera entre SELECT e INSERT
        mock_conexion = MagicMock()
        mock_cursor = MagicMock()
        mock_obtener_conexion.return_value = mock_conexion
        mock_conexion.cursor.return_value = mock_cursor
        # Secuencia fetchone: 1º SELECT inicial -> None (no existe), 2º INSERT ON CONFLICT -> None (otro proceso insertó), 3º SELECT carrera -> (99,)
        mock_cursor.fetchone.side_effect = [None, None, (99,)]

        destino_entrada = Destino(ciudad="  MEdellin  ", pais="  CoLombia  ")

        # Act: debe entrar al segundo SELECT de db_service.py:161-169
        resultado = obtener_o_crear_destino(destino_entrada)

        # Assert: retorno correcto por carrera
        self.assertEqual(resultado, 99)

        # Assert: exactamente 3 executes (SELECT inicial, INSERT ON CONFLICT, SELECT carrera)
        self.assertEqual(mock_cursor.execute.call_count, 3)

        # 1º execute: SELECT inicial con normalización lower+strip
        query1, params1 = mock_cursor.execute.call_args_list[0][0]
        self.assertIn("SELECT id FROM destinos WHERE LOWER(TRIM(ciudad))", query1)
        self.assertEqual(params1, ("medellin", "colombia"))

        # 2º execute: INSERT ON CONFLICT DO NOTHING RETURNING id con misma normalización
        query2, params2 = mock_cursor.execute.call_args_list[1][0]
        self.assertIn("INSERT INTO destinos", query2)
        self.assertIn("ON CONFLICT DO NOTHING", query2)
        self.assertIn("RETURNING id", query2)
        self.assertEqual(params2, ("medellin", "colombia"))

        # 3º execute: segundo SELECT explícito de rama carrera (db_service.py:162-165)
        query3, params3 = mock_cursor.execute.call_args_list[2][0]
        self.assertIn("SELECT id FROM destinos WHERE LOWER(TRIM(ciudad))", query3)
        self.assertEqual(params3, ("medellin", "colombia"))

        # Assert: fetchone llamado 3 veces en orden
        self.assertEqual(mock_cursor.fetchone.call_count, 3)

        # Assert: commit tras encontrar existente por carrera (linea 168) y sin rollback
        mock_conexion.commit.assert_called_once()
        mock_conexion.rollback.assert_not_called()

        # Assert: limpieza finally cierra cursor y conexion
        mock_cursor.close.assert_called_once()
        mock_conexion.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
import os
os.environ['ENVIRONMENT'] = 'testing'

import unittest
from unittest.mock import MagicMock, patch

from test.db_test_case import BaseDBTestCase

from src.models.destino import Destino


class TestDestinos(BaseDBTestCase):

    def test_guardar_y_obtener_destino(self):
        destino_id = self.crear_destino()

        destinos = self.destino_repo.obtener_todos()

        self.assertEqual(len(destinos), 1)
        destino = destinos[0]
        self.assertEqual(destino.id, destino_id)
        self.assertEqual(destino.ciudad, "Medellin")
        self.assertEqual(destino.pais, "Colombia")

    def test_obtener_destinos_sin_registros(self):
        self.assertEqual(self.destino_repo.obtener_todos(), [])

    def test_obtener_destinos_con_varios_registros(self):
        self.crear_destino(ciudad="Medellin", pais="Colombia")
        self.crear_destino(ciudad="Bogota", pais="Colombia")
        self.crear_destino(ciudad="Buenos Aires", pais="Argentina")

        destinos = self.destino_repo.obtener_todos()

        self.assertEqual(len(destinos), 3)
        self.assertEqual({d.ciudad for d in destinos},
                         {"Medellin", "Bogota", "Buenos Aires"})

    def test_guardar_destino_con_caracteres_especiales(self):
        self.crear_destino(ciudad="Ciudad de México", pais="México")

        destinos = self.destino_repo.obtener_todos()

        self.assertEqual(len(destinos), 1)
        self.assertEqual(destinos[0].ciudad, "Ciudad de México")
        self.assertEqual(destinos[0].pais, "México")

    def test_guardar_destino_invalido_devuelve_none_y_no_guarda(self):
        resultado = self.destino_repo.guardar(Destino(ciudad=None, pais="Colombia"))

        self.assertIsNone(resultado)
        self.assertEqual(self.destino_repo.obtener_todos(), [])

    def test_crear_destino_cuando_no_existe(self):
        nuevo_destino = Destino(ciudad="medellin", pais="colombia")

        resultado = self.destino_repo.obtener_o_crear(nuevo_destino)
        destinos = self.destino_repo.obtener_todos()

        self.assertIsInstance(resultado, int)
        self.assertEqual(len(destinos), 1)
        self.assertEqual(destinos[0].ciudad, "medellin")
        self.assertEqual(destinos[0].pais, "colombia")

    def test_llamar_dos_veces_la_misma_ciudad_devuelve_el_mismo_id(self):
        nuevo_destino = Destino(ciudad="Medellin", pais="Colombia")

        resultado1 = self.destino_repo.obtener_o_crear(nuevo_destino)
        resultado2 = self.destino_repo.obtener_o_crear(nuevo_destino)

        self.assertEqual(len(self.destino_repo.obtener_todos()), 1)
        self.assertEqual(resultado1, resultado2)

    def test_no_se_crea_destino_porque_es_invalido(self):
        self.assertIsNone(self.destino_repo.obtener_o_crear(Destino(ciudad=None, pais="Colombia")))
        self.assertIsNone(self.destino_repo.obtener_o_crear(Destino(ciudad="", pais="Colombia")))

        self.assertEqual(self.destino_repo.obtener_todos(), [])

    def test_no_se_crea_destino_con_solo_espacios(self):
        self.assertIsNone(self.destino_repo.obtener_o_crear(Destino(ciudad="   ", pais="Colombia")))

        self.assertEqual(self.destino_repo.obtener_todos(), [])

    def test_buscar_hospedajes_cuando_no_estan_bien_escritos(self):

        nuevo_destino = Destino(" MEdellin  ", " CoLombia")

        destino_creado = self.destino_repo.obtener_o_crear(nuevo_destino)

        resultado = self.destino_repo.obtener_todos()

        self.assertEqual(resultado[0].ciudad, "MEdellin")
        self.assertEqual(resultado[0].pais, "CoLombia")


class TestObtenerOCrearDestinoCarrera(BaseDBTestCase):
    """Tests para la rama de carrera en obtener_o_crear"""

    @patch("src.repositories.base_repository.BaseRepository._obtener_conexion")
    def test_carrera_retorna_id_correcto(self, mock_obtener_conexion):
        mock_conexion = MagicMock()
        mock_cursor = MagicMock()
        mock_obtener_conexion.return_value = mock_conexion
        mock_conexion.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [None, None, (99,)]

        resultado = self.destino_repo.obtener_o_crear(Destino(ciudad="Medellin", pais="Colombia"))

        self.assertEqual(resultado, 99)

    @patch("src.repositories.base_repository.BaseRepository._obtener_conexion")
    def test_carrera_ejecuta_tres_queries(self, mock_obtener_conexion):
        mock_conexion = MagicMock()
        mock_cursor = MagicMock()
        mock_obtener_conexion.return_value = mock_conexion
        mock_conexion.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [None, None, (99,)]

        self.destino_repo.obtener_o_crear(Destino(ciudad="Medellin", pais="Colombia"))

        self.assertEqual(mock_cursor.execute.call_count, 3)

    @patch("src.repositories.base_repository.BaseRepository._obtener_conexion")
    def test_carrera_hace_commit_sin_rollback(self, mock_obtener_conexion):
        mock_conexion = MagicMock()
        mock_cursor = MagicMock()
        mock_obtener_conexion.return_value = mock_conexion
        mock_conexion.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [None, None, (99,)]

        self.destino_repo.obtener_o_crear(Destino(ciudad="Medellin", pais="Colombia"))

        mock_conexion.commit.assert_called_once()
        mock_conexion.rollback.assert_not_called()

    @patch("src.repositories.base_repository.BaseRepository._obtener_conexion")
    def test_carrera_cierra_conexion_correctamente(self, mock_obtener_conexion):
        mock_conexion = MagicMock()
        mock_cursor = MagicMock()
        mock_obtener_conexion.return_value = mock_conexion
        mock_conexion.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [None, None, (99,)]

        self.destino_repo.obtener_o_crear(Destino(ciudad="Medellin", pais="Colombia"))

        mock_cursor.close.assert_called_once()
        mock_conexion.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
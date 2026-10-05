import unittest
from unittest.mock import MagicMock, patch

from src.models.destino import Destino
from test.db_test_case import BaseDBTestCase


class TestDestinoRepository(BaseDBTestCase):

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

    def test_guardar_destino_invalido_lanza_value_error_y_no_guarda(self):
        with self.assertRaises(ValueError):
            self.destino_repo.guardar(Destino(ciudad=None, pais="Colombia"))

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

    def test_obtener_o_crear_con_ciudad_invalida_lanza_value_error(self):
        with self.assertRaises(ValueError):
            self.destino_repo.obtener_o_crear(Destino(ciudad=None, pais="Colombia"))
        with self.assertRaises(ValueError):
            self.destino_repo.obtener_o_crear(Destino(ciudad="", pais="Colombia"))

        self.assertEqual(self.destino_repo.obtener_todos(), [])

    def test_obtener_o_crear_con_solo_espacios_lanza_value_error(self):
        with self.assertRaises(ValueError):
            self.destino_repo.obtener_o_crear(Destino(ciudad="   ", pais="Colombia"))

        self.assertEqual(self.destino_repo.obtener_todos(), [])

    def test_obtener_o_crear_conserva_el_formato_de_ciudad_y_pais(self):
        nuevo_destino = Destino(" MEdellin  ", " CoLombia")

        self.destino_repo.obtener_o_crear(nuevo_destino)

        resultado = self.destino_repo.obtener_todos()

        self.assertEqual(resultado[0].ciudad, "MEdellin")
        self.assertEqual(resultado[0].pais, "CoLombia")


class TestObtenerOCrearDestinoCarrera(BaseDBTestCase):
    """Otra transacción inserta el destino entre el SELECT inicial y el INSERT."""

    def _resolver_carrera(self, obtener_conexion):
        """Simula la carrera y devuelve (id obtenido, cursor y conexión simulados)."""
        conexion = MagicMock()
        cursor = MagicMock()
        obtener_conexion.return_value = conexion
        conexion.cursor.return_value = cursor
        cursor.fetchone.side_effect = [None, None, (99,)]

        resultado = self.destino_repo.obtener_o_crear(Destino(ciudad="Medellin", pais="Colombia"))
        return resultado, cursor, conexion

    @patch("src.repositories.base_repository.BaseRepository._obtener_conexion")
    def test_devuelve_el_id_que_inserto_la_otra_transaccion(self, obtener_conexion):
        resultado, _, _ = self._resolver_carrera(obtener_conexion)

        self.assertEqual(resultado, 99)

    @patch("src.repositories.base_repository.BaseRepository._obtener_conexion")
    def test_ejecuta_tres_queries(self, obtener_conexion):
        _, cursor, _ = self._resolver_carrera(obtener_conexion)

        self.assertEqual(cursor.execute.call_count, 3)

    @patch("src.repositories.base_repository.BaseRepository._obtener_conexion")
    def test_hace_commit_sin_rollback(self, obtener_conexion):
        _, _, conexion = self._resolver_carrera(obtener_conexion)

        conexion.commit.assert_called_once()
        conexion.rollback.assert_not_called()

    @patch("src.repositories.base_repository.BaseRepository._obtener_conexion")
    def test_cierra_cursor_y_conexion(self, obtener_conexion):
        _, cursor, conexion = self._resolver_carrera(obtener_conexion)

        cursor.close.assert_called_once()
        conexion.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()

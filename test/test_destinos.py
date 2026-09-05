import os
os.environ['ENVIRONMENT'] = 'testing'

import unittest
from unittest.mock import MagicMock, patch

from test.db_test_case import BaseDBTestCase

from src.models.destino import Destino
from src.models.recomendaciones import Recomendaciones
from src.models.busqueda import Busqueda
from src.repositories.destino_repository import DestinoRepository
from src.repositories.busqueda_repository import BusquedaRepository
from src.repositories.recomendacion_repository import RecomendacionRepository


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


class TestObtenerOCrearDestinoCarrera(BaseDBTestCase):
    """Tests para la rama de carrera en obtener_o_crear"""

    @patch("src.repositories.destino_repository.DestinoRepository._obtener_conexion")
    def test_carrera_retorna_id_correcto(self, mock_obtener_conexion):
        mock_conexion = MagicMock()
        mock_cursor = MagicMock()
        mock_obtener_conexion.return_value = mock_conexion
        mock_conexion.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [None, None, (99,)]

        resultado = self.destino_repo.obtener_o_crear(Destino(ciudad="Medellin", pais="Colombia"))

        self.assertEqual(resultado, 99)

    @patch("src.repositories.destino_repository.DestinoRepository._obtener_conexion")
    def test_carrera_ejecuta_tres_queries(self, mock_obtener_conexion):
        mock_conexion = MagicMock()
        mock_cursor = MagicMock()
        mock_obtener_conexion.return_value = mock_conexion
        mock_conexion.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [None, None, (99,)]

        self.destino_repo.obtener_o_crear(Destino(ciudad="Medellin", pais="Colombia"))

        self.assertEqual(mock_cursor.execute.call_count, 3)

    @patch("src.repositories.destino_repository.DestinoRepository._obtener_conexion")
    def test_carrera_hace_commit_sin_rollback(self, mock_obtener_conexion):
        mock_conexion = MagicMock()
        mock_cursor = MagicMock()
        mock_obtener_conexion.return_value = mock_conexion
        mock_conexion.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [None, None, (99,)]

        self.destino_repo.obtener_o_crear(Destino(ciudad="Medellin", pais="Colombia"))

        mock_conexion.commit.assert_called_once()
        mock_conexion.rollback.assert_not_called()

    @patch("src.repositories.destino_repository.DestinoRepository._obtener_conexion")
    def test_carrera_cierra_conexion_correctamente(self, mock_obtener_conexion):
        mock_conexion = MagicMock()
        mock_cursor = MagicMock()
        mock_obtener_conexion.return_value = mock_conexion
        mock_conexion.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [None, None, (99,)]

        self.destino_repo.obtener_o_crear(Destino(ciudad="Medellin", pais="Colombia"))

        mock_cursor.close.assert_called_once()
        mock_conexion.close.assert_called_once()


class TestDBRecomendaciones(BaseDBTestCase):

    def test_insertar_busqueda_con_3_recomendaciones_verificar_que_se_guardo(self):

        destino_id = self.crear_destino()
        h1 = self.crear_hospedaje(destino_id, nombre="Hotel 1")
        h2 = self.crear_hospedaje(destino_id, nombre="Hotel 2")
        h3 = self.crear_hospedaje(destino_id, nombre="Hotel 3")

        busqueda_repo = BusquedaRepository()
        recomendacion_repo = RecomendacionRepository()

        busqueda = Busqueda(
            id=1,
            usuario_id=self.usuario_seed_id,
            destino_id=destino_id,
            zona="El poblado",
            presupuesto=200000,
            fecha_inicio="2023-01-01",
            fecha_fin="2023-01-02"
        )

        busqueda_id = busqueda_repo.guardar(busqueda)

        recomendaciones = [Recomendaciones(id=1, busqueda_id=busqueda_id, hospedaje_id=h1, posicion=1),
                          Recomendaciones(id=2, busqueda_id=busqueda_id, hospedaje_id=h2, posicion=2),
                          Recomendaciones(id=3, busqueda_id=busqueda_id, hospedaje_id=h3, posicion=3)]

        recomendacion_repo.guardar_varias(recomendaciones, busqueda_id)

        cursor = self.conexion.cursor()

        query = "SELECT id, busqueda_id, hospedaje_id, posicion FROM recomendaciones"

        cursor.execute(query)

        resultado = cursor.fetchall()

        self.assertEqual(resultado[0], (recomendaciones[0].id,
                                        recomendaciones[0].busqueda_id,
                                        recomendaciones[0].hospedaje_id,
                                        recomendaciones[0].posicion))

    def test_insertar_busqueda_con_mismo_destino_pero_otra_zona_debe_ser_independiente(self):

        destino_id = self.crear_destino()

        busqueda_repo = BusquedaRepository()

        busqueda1 = Busqueda(
            id=1,
            usuario_id=self.usuario_seed_id,
            destino_id=destino_id,
            zona="El poblado",
            presupuesto=200000,
            fecha_inicio="2023-01-01",
            fecha_fin="2023-01-02"
        )

        busqueda2 = Busqueda(
            id=2,
            usuario_id=self.usuario_seed_id,
            destino_id=destino_id,
            zona="La Candelaria",
            presupuesto=200000,
            fecha_inicio="2023-01-01",
            fecha_fin="2023-01-02"
        )

        busqueda_repo.guardar(busqueda1)
        busqueda_repo.guardar(busqueda2)

        cursor = self.conexion.cursor()
        cursor.execute("SELECT COUNT(*) FROM busquedas")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 2)


if __name__ == '__main__':
    unittest.main()
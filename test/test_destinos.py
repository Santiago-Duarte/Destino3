import os
os.environ['ENVIRONMENT'] = 'testing'

import unittest

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


if __name__ == '__main__':
    unittest.main()
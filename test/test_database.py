import os
os.environ['ENVIRONMENT'] = 'testing'

import unittest
from src.config.database import obtener_conexion
from src.services.db_service import guardar_destino, guardar_hospedaje, obtener_destinos, obtener_hospedajes_por_destino
from src.models.destino import Destino
from src.models.hospedaje import Hospedaje

class TestDatabase(unittest.TestCase):

    def setUp(self):
        self.conexion = obtener_conexion()
        self.cursor = self.conexion.cursor()

        query = "DELETE FROM hospedajes; DELETE FROM destinos;"
        self.cursor.execute(query)
        self.conexion.commit()

        self.nuevo_destino = Destino(ciudad="Medellin", pais="Colombia")
        self.destino_id = guardar_destino(self.nuevo_destino)
        self.nuevo_hospedaje = Hospedaje(
            nombre="Hotel 1",
            tipo="hotel",
            precio_noche=100,
            calificacion=4,
            direccion="Calle 1",
            url_reserva="https://www.hotel1.com",
            destino_id=self.destino_id
        )
        self.hospedaje_id = guardar_hospedaje(self.nuevo_hospedaje)


    def tearDown(self):
        self.cursor.close()
        self.conexion.close()

    def test_conexion_exitosa(self):
        self.assertIsNotNone(self.conexion)

    def test_guardar_y_obtener_destino(self):
        self.assertIsInstance(self.destino_id, int)
        destino = obtener_destinos()
        self.assertIsInstance(destino, list)
        self.assertEqual(len(destino), 1)
        self.assertEqual(destino[0].ciudad, "Medellin")
        self.assertEqual(destino[0].pais, "Colombia")

    def test_guardar_y_obtener_hospedaje(self):
        self.assertIsInstance(self.hospedaje_id, int)

        hospedajes = obtener_hospedajes_por_destino(self.destino_id)
        self.assertIsInstance(hospedajes, list)
        self.assertEqual(len(hospedajes), 1)

        self.assertEqual(hospedajes[0].nombre, "Hotel 1")
        self.assertEqual(hospedajes[0].destino_id, self.destino_id)

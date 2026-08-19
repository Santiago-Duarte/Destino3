import os
os.environ['ENVIRONMENT'] = 'testing'

import unittest
from src.config.database import obtener_conexion
from src.models.destino import Destino
from src.models.hospedaje import Hospedaje
from src.services.db_service import guardar_destino, guardar_hospedaje


class BaseDBTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.conexion = obtener_conexion()
        if cls.conexion is None:
            raise unittest.SkipTest("No se pudo conectar a la base de datos de testing")
        cls.cursor = cls.conexion.cursor()

    @classmethod
    def tearDownClass(cls):
        cls.cursor.close()
        cls.conexion.close()

    def setUp(self):
        with self.conexion.cursor() as cursor:
            cursor.execute("DELETE FROM hospedajes; DELETE FROM destinos;")
        self.conexion.commit()

    def crear_destino(self, ciudad="Medellin", pais="Colombia"):
        return guardar_destino(Destino(ciudad=ciudad, pais=pais))

    def crear_hospedaje(self, destino_id, **campos):
        valores = dict(
            nombre="Hotel 1",
            tipo="hotel",
            precio_noche=100,
            calificacion=4,
            direccion="Calle 1",
            url_reserva="https://www.hotel1.com",
            destino_id=destino_id,
        )
        valores.update(campos)
        return guardar_hospedaje(Hospedaje(**valores))

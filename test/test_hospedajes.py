import os
os.environ['ENVIRONMENT'] = 'testing'

import unittest

from test.db_test_case import BaseDBTestCase

from src.models.hospedaje import Hospedaje
from src.repositories.hospedaje_repository import HospedajeRepository


class TestHospedajes(BaseDBTestCase):

    def test_guardar_y_obtener_hospedaje(self):
        destino_id = self.crear_destino()
        hospedaje_id = self.crear_hospedaje(destino_id)

        hospedajes = self.hospedaje_repo.obtener_por_destino(destino_id)

        self.assertEqual(len(hospedajes), 1)
        hospedaje = hospedajes[0]
        self.assertEqual(hospedaje.id, hospedaje_id)
        self.assertEqual(hospedaje.nombre, "Hotel 1")
        self.assertEqual(hospedaje.tipo, "hotel")
        self.assertEqual(float(hospedaje.precio_noche), 100.0)
        self.assertEqual(float(hospedaje.calificacion), 4.0)
        self.assertEqual(hospedaje.direccion, "Calle 1")
        self.assertEqual(hospedaje.url_reserva, "https://www.hotel1.com")
        self.assertEqual(hospedaje.destino_id, destino_id)

    def test_obtener_hospedajes_sin_registros(self):
        destino_id = self.crear_destino()

        self.assertEqual(self.hospedaje_repo.obtener_por_destino(destino_id), [])

    def test_obtener_hospedajes_solo_del_destino_solicitado(self):
        destino_1 = self.crear_destino()
        destino_2 = self.crear_destino(ciudad="Bogota")
        self.crear_hospedaje(destino_1)
        self.crear_hospedaje(destino_2, nombre="Hotel 2")

        hospedajes = self.hospedaje_repo.obtener_por_destino(destino_1)

        self.assertEqual(len(hospedajes), 1)
        self.assertEqual(hospedajes[0].nombre, "Hotel 1")

    def test_guardar_hospedaje_con_campos_opcionales_nulos(self):
        destino_id = self.crear_destino()
        hospedaje = Hospedaje(
            nombre="Hostal",
            tipo=None,
            precio_noche=None,
            calificacion=None,
            direccion=None,
            url_reserva=None,
            destino_id=destino_id,
        )

        hospedaje_id = self.hospedaje_repo.guardar(hospedaje)

        self.assertIsInstance(hospedaje_id, int)
        hospedajes = self.hospedaje_repo.obtener_por_destino(destino_id)
        self.assertEqual(len(hospedajes), 1)
        self.assertEqual(hospedajes[0].nombre, "Hostal")
        self.assertIsNone(hospedajes[0].tipo)
        self.assertIsNone(hospedajes[0].precio_noche)
        self.assertIsNone(hospedajes[0].calificacion)
        self.assertIsNone(hospedajes[0].direccion)
        self.assertIsNone(hospedajes[0].url_reserva)

    def test_guardar_hospedaje_con_destino_inexistente_devuelve_none(self):
        destino_id = self.crear_destino()

        hospedaje_id = self.crear_hospedaje(destino_id=999999)

        self.assertIsNone(hospedaje_id)
        self.assertEqual(self.hospedaje_repo.obtener_por_destino(destino_id), [])

    def test_guardar_hospedaje_sin_destino_devuelve_none(self):
        hospedaje = Hospedaje(
            nombre="Hotel 1",
            tipo="hotel",
            precio_noche=100,
            calificacion=4,
            direccion="Calle 1",
            url_reserva="https://www.hotel1.com",
            destino_id=None,
        )

        hospedaje_id = self.hospedaje_repo.guardar(hospedaje)

        self.assertIsNone(hospedaje_id)
        self.assertEqual(self.destino_repo.obtener_todos(), [])
        with self.conexion.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM hospedajes;")
            self.assertEqual(cursor.fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
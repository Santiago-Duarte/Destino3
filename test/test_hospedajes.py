import os
os.environ['ENVIRONMENT'] = 'testing'

import unittest

from test.db_test_case import BaseDBTestCase

from src.models.hospedaje import Hospedaje
from src.services.db_service import (
    guardar_hospedaje,
    obtener_hospedajes_por_destino,
)


class TestHospedajes(BaseDBTestCase):

    def test_guardar_y_obtener_hospedaje(self):
        destino_id = self.crear_destino()
        hospedaje_id = self.crear_hospedaje(destino_id)

        hospedajes = obtener_hospedajes_por_destino(destino_id)

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

        self.assertEqual(obtener_hospedajes_por_destino(destino_id), [])

    def test_obtener_hospedajes_solo_del_destino_solicitado(self):
        destino_1 = self.crear_destino()
        destino_2 = self.crear_destino(ciudad="Bogota")
        self.crear_hospedaje(destino_1)
        self.crear_hospedaje(destino_2, nombre="Hotel 2")

        hospedajes = obtener_hospedajes_por_destino(destino_1)

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

        hospedaje_id = guardar_hospedaje(hospedaje)

        self.assertIsInstance(hospedaje_id, int)
        hospedajes = obtener_hospedajes_por_destino(destino_id)
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
        self.assertEqual(obtener_hospedajes_por_destino(destino_id), [])


if __name__ == '__main__':
    unittest.main()
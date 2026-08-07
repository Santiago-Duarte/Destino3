import os
os.environ['ENVIRONMENT'] = 'testing'

import unittest
from src.config.database import obtener_conexion
from src.services.db_service import guardar_destino, guardar_hospedaje, obtener_destinos, obtener_hospedajes_por_destino
from src.models.destino import Destino
from src.models.hospedaje import Hospedaje


class TestDatabase(unittest.TestCase):

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

    def test_guardar_y_obtener_destino(self):
        destino_id = self.crear_destino()

        destinos = obtener_destinos()

        self.assertEqual(len(destinos), 1)
        destino = destinos[0]
        self.assertEqual(destino.id, destino_id)
        self.assertEqual(destino.ciudad, "Medellin")
        self.assertEqual(destino.pais, "Colombia")

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

    def test_obtener_destinos_sin_registros(self):
        self.assertEqual(obtener_destinos(), [])

    def test_obtener_hospedajes_sin_registros(self):
        destino_id = self.crear_destino()

        self.assertEqual(obtener_hospedajes_por_destino(destino_id), [])

    def test_obtener_destinos_con_varios_registros(self):
        self.crear_destino(ciudad="Medellin", pais="Colombia")
        self.crear_destino(ciudad="Bogota", pais="Colombia")
        self.crear_destino(ciudad="Buenos Aires", pais="Argentina")

        destinos = obtener_destinos()

        self.assertEqual(len(destinos), 3)
        self.assertEqual({d.ciudad for d in destinos},
                         {"Medellin", "Bogota", "Buenos Aires"})

    def test_obtener_hospedajes_solo_del_destino_solicitado(self):
        destino_1 = self.crear_destino()
        destino_2 = self.crear_destino(ciudad="Bogota")
        self.crear_hospedaje(destino_1)
        self.crear_hospedaje(destino_2, nombre="Hotel 2")

        hospedajes = obtener_hospedajes_por_destino(destino_1)

        self.assertEqual(len(hospedajes), 1)
        self.assertEqual(hospedajes[0].nombre, "Hotel 1")

    def test_guardar_destino_con_caracteres_especiales(self):
        self.crear_destino(ciudad="Ciudad de México", pais="México")

        destinos = obtener_destinos()

        self.assertEqual(len(destinos), 1)
        self.assertEqual(destinos[0].ciudad, "Ciudad de México")
        self.assertEqual(destinos[0].pais, "México")

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

    def test_guardar_destino_invalido_devuelve_none_y_no_guarda(self):
        resultado = guardar_destino(Destino(ciudad=None, pais="Colombia"))

        self.assertIsNone(resultado)
        self.assertEqual(obtener_destinos(), [])

    def test_guardar_hospedaje_con_destino_inexistente_devuelve_none(self):
        destino_id = self.crear_destino()

        hospedaje_id = self.crear_hospedaje(destino_id=999999)

        self.assertIsNone(hospedaje_id)
        self.assertEqual(obtener_hospedajes_por_destino(destino_id), [])


if __name__ == '__main__':
    unittest.main()

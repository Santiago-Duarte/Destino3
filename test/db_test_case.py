import os
os.environ['ENVIRONMENT'] = 'testing'

import unittest
from src.config.database import obtener_conexion
from src.models.destino import Destino
from src.models.hospedaje import Hospedaje
from src.services.db_service import guardar_destino, guardar_hospedaje

_TABLAS = "busquedas, recomendaciones, hospedajes, destinos, usuarios"


class BaseDBTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.conexion = obtener_conexion()
        if cls.conexion is None:
            raise unittest.SkipTest("No se pudo conectar a la base de datos de testing")
        cls.cursor = cls.conexion.cursor()
        cls._insertar_seed_user()

    @classmethod
    def tearDownClass(cls):
        cls._clean_db()
        cls.cursor.close()
        cls.conexion.close()

    def setUp(self):
        self._clean_db()
        self._insertar_seed_user()

    def tearDown(self):
        self._clean_db()

    @classmethod
    def _clean_db(cls):
        with cls.conexion.cursor() as cursor:
            cursor.execute(f"TRUNCATE {_TABLAS} RESTART IDENTITY CASCADE")
        cls.conexion.commit()

    @classmethod
    def _insertar_seed_user(cls):
        cls.cursor.execute(
            "INSERT INTO usuarios (nombre, apellido, correo, password_hash) "
            "VALUES ('admin', 'admin', 'admin@admin.com', 'admin') "
            "ON CONFLICT (correo) DO UPDATE SET nombre = 'admin' "
            "RETURNING id"
        )
        cls.usuario_seed_id = cls.cursor.fetchone()[0]
        cls.conexion.commit()

    @staticmethod
    def crear_destino(ciudad="Medellin", pais="Colombia"):
        return guardar_destino(Destino(ciudad=ciudad, pais=pais))

    @staticmethod
    def crear_hospedaje(destino_id, **campos):
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

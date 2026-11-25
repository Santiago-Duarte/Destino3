import os
import unittest
from unittest.mock import patch

from src.config.database import obtener_conexion
from src.models.destino import Destino
from src.models.hospedaje import Hospedaje
from src.repositories import base_repository
from src.repositories.destino_repository import DestinoRepository
from src.repositories.hospedaje_repository import HospedajeRepository
from test.adaptador_transaccion import ConexionConSavepoint


def conexion_de_pruebas():
    """Obtiene conexión o salta la prueba si PostgreSQL no está disponible."""
    conexion = obtener_conexion()
    if conexion is None:
        if os.getenv("REQUIRE_DB_TESTS") == "1":
            raise ConnectionError(
                "No se pudo conectar a la base de datos de testing; "
                "levanta PostgreSQL antes de correr la suite."
            )
        raise unittest.SkipTest(
            "PostgreSQL no disponible; se omite la prueba de integración."
        )
    return conexion


class BaseDBTestCase(unittest.TestCase):
    """Abre una conexión por prueba y revierte todo al terminar."""

    @classmethod
    def setUpClass(cls):
        cls.destino_repo = DestinoRepository()
        cls.hospedaje_repo = HospedajeRepository()

    def setUp(self):
        self.conexion_externa = conexion_de_pruebas()

        self.conexion = ConexionConSavepoint(self.conexion_externa)
        self._parche_conexion = patch.object(
            base_repository,
            "obtener_conexion",
            return_value=self.conexion,
        )
        self._parche_conexion.start()

    def tearDown(self):
        try:
            self.conexion_externa.rollback()
        finally:
            self._parche_conexion.stop()
            self.conexion_externa.close()

    def crear_destino(self, ciudad="Medellin", pais="Colombia"):
        return self.destino_repo.guardar(Destino(ciudad=ciudad, pais=pais))

    def crear_hospedaje(self, destino_id, **campos):
        valores = dict(
            nombre="Hotel 1",
            tipo="hotel",
            precio_noche=100,
            calificacion=4,
            descripcion="Descripción de prueba",
            direccion="Calle 1",
            url_reserva="https://www.hotel1.com",
            destino_id=destino_id,
            google_place_id=None,
        )
        valores.update(campos)
        return self.hospedaje_repo.guardar_lote([Hospedaje(**valores)])[0]

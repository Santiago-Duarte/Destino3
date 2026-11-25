import unittest
import uuid
from unittest.mock import patch

from src.models.destino import Destino
from src.repositories import base_repository
from src.repositories.destino_repository import DestinoRepository
from test.adaptador_transaccion import ConexionConSavepoint
from test.caso_prueba_bd import conexion_de_pruebas


class TestRepositoriosConTransaccionExterna(unittest.TestCase):
    def test_commit_del_repository_y_close_no_escapan_del_rollback_externo(self):
        conexion_externa = conexion_de_pruebas()

        ciudad = f"E3_{uuid.uuid4().hex}"
        adaptador = ConexionConSavepoint(conexion_externa)
        parche_conexion = patch.object(
            base_repository,
            "obtener_conexion",
            return_value=adaptador,
        )

        try:
            parche_conexion.start()
            DestinoRepository().guardar(Destino(ciudad=ciudad, pais="Colombia"))

            self.assertFalse(conexion_externa.closed)
            with conexion_externa.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM destinos WHERE ciudad = %s AND pais = %s",
                    (ciudad, "Colombia"),
                )
                self.assertEqual(cursor.fetchone()[0], 1)

            conexion_externa.rollback()

            with conexion_externa.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM destinos WHERE ciudad = %s AND pais = %s",
                    (ciudad, "Colombia"),
                )
                self.assertEqual(cursor.fetchone()[0], 0)
        finally:
            parche_conexion.stop()
            conexion_externa.rollback()
            conexion_externa.close()



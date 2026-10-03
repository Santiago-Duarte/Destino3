import os
os.environ['ENVIRONMENT'] = 'testing'

import unittest

import psycopg2

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

    def test_guardar_varios_con_campos_opcionales_nulos(self):
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

        ids = self.hospedaje_repo.guardar_varios([hospedaje])

        self.assertIsInstance(ids[0], int)
        hospedajes = self.hospedaje_repo.obtener_por_destino(destino_id)
        self.assertEqual(len(hospedajes), 1)
        self.assertEqual(hospedajes[0].nombre, "Hostal")
        self.assertIsNone(hospedajes[0].tipo)
        self.assertIsNone(hospedajes[0].precio_noche)
        self.assertIsNone(hospedajes[0].calificacion)
        self.assertIsNone(hospedajes[0].direccion)
        self.assertIsNone(hospedajes[0].url_reserva)

    def test_guardar_varios_con_destino_inexistente_lanza_error(self):
        destino_id = self.crear_destino()
        hospedaje = Hospedaje(
            nombre="Hotel 1",
            tipo="hotel",
            precio_noche=100,
            calificacion=4,
            direccion="Calle 1",
            url_reserva="https://www.hotel1.com",
            destino_id=999999,
        )

        with self.assertRaises(psycopg2.IntegrityError):
            self.hospedaje_repo.guardar_varios([hospedaje])

        self.assertEqual(self.hospedaje_repo.obtener_por_destino(destino_id), [])

    def test_guardar_varios_sin_destino_lanza_error(self):
        hospedaje = Hospedaje(
            nombre="Hotel 1",
            tipo="hotel",
            precio_noche=100,
            calificacion=4,
            direccion="Calle 1",
            url_reserva="https://www.hotel1.com",
            destino_id=None,
        )

        with self.assertRaises(psycopg2.IntegrityError):
            self.hospedaje_repo.guardar_varios([hospedaje])

        self.assertEqual(self.destino_repo.obtener_todos(), [])
        with self.conexion.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM hospedajes;")
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_el_repositorio_no_tiene_insercion_unitaria(self):
        """RF-4: los hospedajes solo se persisten como lote todo-o-nada."""
        self.assertFalse(hasattr(self.hospedaje_repo, "guardar"))


class TestGuardarVariosHospedajes(BaseDBTestCase):
    """RF-4: el lote de hospedajes se persiste en una única transacción."""

    def _crear_lote(self, destino_id, cantidad=3):
        return [
            Hospedaje(
                nombre=f"Hotel {i}",
                tipo="hotel",
                precio_noche=100,
                calificacion=4,
                direccion="Calle 1",
                url_reserva=f"https://www.hotel{i}.com",
                destino_id=destino_id,
            )
            for i in range(1, cantidad + 1)
        ]

    def _contar_hospedajes(self):
        with self.conexion.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM hospedajes;")
            return cursor.fetchone()[0]

    def test_guardar_varios_devuelve_tres_ids_enteros(self):
        destino_id = self.crear_destino()

        ids = self.hospedaje_repo.guardar_varios(self._crear_lote(destino_id))

        self.assertEqual(len(ids), 3)
        for id_generado in ids:
            self.assertIsInstance(id_generado, int)
        self.assertEqual(self._contar_hospedajes(), 3)

    def test_con_error_en_el_tercero_la_tabla_queda_sin_filas(self):
        destino_id = self.crear_destino()
        lote = self._crear_lote(destino_id, cantidad=2)
        lote.append(self._crear_lote(999999, cantidad=1)[0])

        with self.assertRaises(psycopg2.IntegrityError):
            self.hospedaje_repo.guardar_varios(lote)

        self.assertEqual(self._contar_hospedajes(), 0)


if __name__ == '__main__':
    unittest.main()
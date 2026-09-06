import os
os.environ['ENVIRONMENT'] = 'testing'

import unittest

from test.db_test_case import BaseDBTestCase

from src.models.recomendaciones import Recomendaciones
from src.models.busqueda import Busqueda
from src.repositories.busqueda_repository import BusquedaRepository
from src.repositories.recomendacion_repository import RecomendacionRepository


class TestDBRecomendaciones(BaseDBTestCase):

    def test_insertar_busqueda_con_3_recomendaciones_verificar_que_se_guardo(self):
        destino_id = self.crear_destino()
        busqueda_id, recomendaciones = self.crear_busqueda_con_recomendaciones(destino_id)

        cursor = self.conexion.cursor()
        query = "SELECT id, busqueda_id, hospedaje_id, posicion FROM recomendaciones"
        cursor.execute(query)
        resultado = cursor.fetchall()

        self.assertEqual(resultado[0], (recomendaciones[0].id,
                                        recomendaciones[0].busqueda_id,
                                        recomendaciones[0].hospedaje_id,
                                        recomendaciones[0].posicion))

    def test_insertar_busqueda_con_mismo_destino_pero_otra_zona_debe_ser_independiente(self):

        destino_id = self.crear_destino()

        busqueda_repo = BusquedaRepository()

        busqueda1 = Busqueda(
            id=1,
            usuario_id=self.usuario_seed_id,
            destino_id=destino_id,
            zona="El poblado",
            presupuesto=200000,
            fecha_inicio="2023-01-01",
            fecha_fin="2023-01-02"
        )

        busqueda2 = Busqueda(
            id=2,
            usuario_id=self.usuario_seed_id,
            destino_id=destino_id,
            zona="La Candelaria",
            presupuesto=200000,
            fecha_inicio="2023-01-01",
            fecha_fin="2023-01-02"
        )

        busqueda_repo.guardar(busqueda1)
        busqueda_repo.guardar(busqueda2)

        cursor = self.conexion.cursor()
        cursor.execute("SELECT COUNT(*) FROM busquedas")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 2)

    def test_verificar_orden_posicion_se_respeta(self):

        destino_id = self.crear_destino()
        busqueda_id, recomendaciones = self.crear_busqueda_con_recomendaciones(destino_id)

        cursor = self.conexion.cursor()

        query = "SELECT posicion FROM recomendaciones"

        cursor.execute(query)

        resultado = cursor.fetchall()

        self.assertEqual(resultado, [(1,), (2,), (3,)])

    def test_verificar_no_repetir_posicion_en_la_misma_busqueda(self):

        destino_id = self.crear_destino()
        busqueda = Busqueda(
            id=1,
            usuario_id=self.usuario_seed_id,
            destino_id=destino_id,
            zona="El poblado",
            presupuesto=200000,
            fecha_inicio="2023-01-01",
            fecha_fin="2023-01-02"
        )

        hospedajes = []
        for i in range(1, 4):
            h = self.crear_hospedaje(destino_id=destino_id, nombre=f"Hotel {i}")
            hospedajes.append(h)

        recomendaciones = [
            Recomendaciones(id=1, busqueda_id=1, hospedaje_id=hospedajes[0], posicion=1),
            Recomendaciones(id=2, busqueda_id=1, hospedaje_id=hospedajes[1], posicion=2),
            Recomendaciones(id=3, busqueda_id=1, hospedaje_id=hospedajes[2], posicion=2)
        ]

        busqueda_repo = BusquedaRepository()
        busqueda_id = busqueda_repo.guardar(busqueda)

        recomendacion_repo = RecomendacionRepository()
        resultado = recomendacion_repo.guardar_varias(recomendaciones, busqueda_id)

        self.assertFalse(resultado)


if __name__ == '__main__':
    unittest.main()

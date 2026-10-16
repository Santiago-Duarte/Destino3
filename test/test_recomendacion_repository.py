import unittest
import uuid

from psycopg2 import errors

from src.models.busqueda import Busqueda
from src.models.recomendacion import Recomendacion
from src.repositories.busqueda_repository import BusquedaRepository
from src.repositories.recomendacion_repository import RecomendacionRepository
from test.db_test_case import BaseDBTestCase


def _ciudad_unica(ciudad="Medellin"):
    return f"{ciudad}_{uuid.uuid4().hex}"


class TestRecomendacionRepository(BaseDBTestCase):

    def test_las_tres_recomendaciones_se_persisten_con_su_busqueda(self):
        destino_id = self.crear_destino(ciudad=_ciudad_unica())
        busqueda_id, recomendaciones = self.crear_busqueda_con_recomendaciones(destino_id)

        with self.conexion.cursor() as cursor:
            cursor.execute(
                "SELECT busqueda_id, hospedaje_id, posicion "
                "FROM recomendaciones WHERE busqueda_id = %s ORDER BY posicion",
                (busqueda_id,),
            )
            resultado = cursor.fetchall()

        self.assertEqual(resultado, [
            (recomendacion.busqueda_id, recomendacion.hospedaje_id, recomendacion.posicion)
            for recomendacion in recomendaciones
        ])

    def test_las_posiciones_se_guardan_en_orden(self):
        destino_id = self.crear_destino(ciudad=_ciudad_unica())
        busqueda_id, _ = self.crear_busqueda_con_recomendaciones(destino_id)

        with self.conexion.cursor() as cursor:
            cursor.execute(
                "SELECT posicion FROM recomendaciones "
                "WHERE busqueda_id = %s ORDER BY posicion",
                (busqueda_id,),
            )
            resultado = cursor.fetchall()

        self.assertEqual(resultado, [(1,), (2,), (3,)])

    def test_posicion_repetida_en_la_misma_busqueda_falla(self):
        destino_id = self.crear_destino(ciudad=_ciudad_unica())
        busqueda = Busqueda(
            id=None,
            usuario_id=self.usuario_seed_id,
            destino_id=destino_id,
            zona="El poblado",
            presupuesto=200000,
            fecha_inicio="2023-01-01",
            fecha_fin="2023-01-02"
        )
        busqueda_id = BusquedaRepository().guardar(busqueda)

        hospedajes = [
            self.crear_hospedaje(destino_id=destino_id, nombre=f"Hotel {i}")
            for i in range(1, 4)
        ]
        recomendaciones = [
            Recomendacion(id=None, busqueda_id=busqueda_id, hospedaje_id=hospedajes[0], posicion=1),
            Recomendacion(id=None, busqueda_id=busqueda_id, hospedaje_id=hospedajes[1], posicion=2),
            Recomendacion(id=None, busqueda_id=busqueda_id, hospedaje_id=hospedajes[2], posicion=2),
        ]

        with self.assertRaises(errors.UniqueViolation):
            RecomendacionRepository().guardar_lote(recomendaciones)


class TestBusquedaRepository(BaseDBTestCase):

    def test_dos_busquedas_en_el_mismo_destino_con_zona_distinta_son_independientes(self):
        destino_id = self.crear_destino(ciudad=_ciudad_unica())
        busqueda_repo = BusquedaRepository()

        busqueda1 = Busqueda(
            id=None,
            usuario_id=self.usuario_seed_id,
            destino_id=destino_id,
            zona="El poblado",
            presupuesto=200000,
            fecha_inicio="2023-01-01",
            fecha_fin="2023-01-02"
        )
        busqueda2 = Busqueda(
            id=None,
            usuario_id=self.usuario_seed_id,
            destino_id=destino_id,
            zona="La Candelaria",
            presupuesto=200000,
            fecha_inicio="2023-01-01",
            fecha_fin="2023-01-02"
        )

        busqueda_1_id = busqueda_repo.guardar(busqueda1)
        busqueda_2_id = busqueda_repo.guardar(busqueda2)

        with self.conexion.cursor() as cursor:
            cursor.execute(
                "SELECT id, zona FROM busquedas WHERE id IN (%s, %s) ORDER BY id",
                (busqueda_1_id, busqueda_2_id),
            )
            resultados = cursor.fetchall()

        self.assertEqual(
            resultados,
            sorted([
                (busqueda_1_id, "El poblado"),
                (busqueda_2_id, "La Candelaria"),
            ]),
        )


if __name__ == '__main__':
    unittest.main()

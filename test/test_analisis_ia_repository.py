import unittest
import uuid

import psycopg2
from psycopg2 import errors

from src.models.analisis import Analisis
from src.repositories.analisis_ia_repository import AnalisisIARepository
from test.db_test_case import BaseDBTestCase


def _ciudad_unica():
    return f"Medellin_{uuid.uuid4().hex}"


class TestAnalisisIARepository(BaseDBTestCase):

    def setUp(self):
        super().setUp()
        self.repo = AnalisisIARepository()

    def test_guardar_y_recuperar_analisis(self):
        destino_id = self.crear_destino(ciudad=_ciudad_unica())
        hospedaje_id = self.crear_hospedaje(destino_id)

        analisis = Analisis(
            resumen_ejecutivo="Excelente opción cerca al centro",
            puntos_fuertes="Ubicación céntrica; desayuno incluido",
            puntos_debiles="Ruido nocturno",
            hospedaje_id=hospedaje_id,
        )

        analisis_id = self.repo.guardar(analisis)
        self.assertIsNotNone(analisis_id)

        recuperado = self.repo.obtener_por_hospedaje(hospedaje_id)
        self.assertIsNotNone(recuperado)
        self.assertEqual(recuperado.id, analisis_id)
        self.assertEqual(recuperado.resumen_ejecutivo, "Excelente opción cerca al centro")
        self.assertEqual(recuperado.puntos_fuertes, "Ubicación céntrica; desayuno incluido")
        self.assertEqual(recuperado.puntos_debiles, "Ruido nocturno")
        self.assertEqual(recuperado.hospedaje_id, hospedaje_id)

    def test_la_tabla_no_tiene_columna_de_score(self):
        with self.conexion.cursor() as cursor:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'analisis_ia';"
            )
            columnas = {fila[0] for fila in cursor.fetchall()}

        self.assertIn("resumen_ejecutivo", columnas)
        self.assertIn("puntos_fuertes", columnas)
        self.assertIn("puntos_debiles", columnas)
        self.assertNotIn("score_calidad_precio", columnas)

    def test_duplicar_analisis_del_mismo_hospedaje_falla(self):
        destino_id = self.crear_destino(ciudad=_ciudad_unica())
        hospedaje_id = self.crear_hospedaje(destino_id)

        self.repo.guardar(Analisis(
            resumen_ejecutivo="Primera versión",
            puntos_fuertes="Fuertes",
            puntos_debiles="Débiles",
            hospedaje_id=hospedaje_id,
        ))

        with self.assertRaises(errors.UniqueViolation):
            self.repo.guardar(Analisis(
                resumen_ejecutivo="Segunda versión",
                puntos_fuertes="Otros fuertes",
                puntos_debiles="Otros débiles",
                hospedaje_id=hospedaje_id,
            ))


class TestObtenerPorVariosHospedajes(BaseDBTestCase):

    def setUp(self):
        super().setUp()
        self.repo = AnalisisIARepository()

    def test_devuelve_solo_los_analisis_que_existen(self):
        destino_id = self.crear_destino(ciudad=_ciudad_unica())
        con_analisis = self.crear_hospedaje(destino_id, nombre="Hotel A")
        sin_analisis = self.crear_hospedaje(destino_id, nombre="Hotel B")
        self.repo.guardar(Analisis(
            resumen_ejecutivo="Análisis de A",
            puntos_fuertes="Fuertes",
            puntos_debiles="Débiles",
            hospedaje_id=con_analisis,
        ))

        recuperados = self.repo.obtener_por_hospedajes([con_analisis, sin_analisis])

        self.assertEqual(set(recuperados), {con_analisis})
        self.assertEqual(recuperados[con_analisis].resumen_ejecutivo, "Análisis de A")

    def test_lista_vacia_no_abre_transaccion(self):
        self.assertEqual(self.repo.obtener_por_hospedajes([]), {})


class TestGuardarLoteAnalisis(BaseDBTestCase):
    """El lote de análisis se persiste todo-o-nada."""

    def setUp(self):
        super().setUp()
        self.repo = AnalisisIARepository()

    def _crear_lote(self, hospedaje_ids):
        return [
            Analisis(
                resumen_ejecutivo=f"Análisis {indice}",
                puntos_fuertes=f"Fuertes {indice}",
                puntos_debiles=f"Débiles {indice}",
                hospedaje_id=hospedaje_id,
            )
            for indice, hospedaje_id in enumerate(hospedaje_ids, start=1)
        ]

    def _contar_analisis(self, hospedaje_id=None):
        with self.conexion.cursor() as cursor:
            if hospedaje_id is None:
                cursor.execute("SELECT COUNT(*) FROM analisis_ia;")
            else:
                cursor.execute(
                    "SELECT COUNT(*) FROM analisis_ia WHERE hospedaje_id = %s;",
                    (hospedaje_id,),
                )
            return cursor.fetchone()[0]

    def test_guardar_lote_devuelve_ids_enteros_asociados_a_su_hospedaje(self):
        destino_id = self.crear_destino(ciudad=_ciudad_unica())
        hospedaje_1 = self.crear_hospedaje(destino_id, nombre="Hotel A")
        hospedaje_2 = self.crear_hospedaje(destino_id, nombre="Hotel B")

        ids = self.repo.guardar_lote(self._crear_lote([hospedaje_1, hospedaje_2]))

        self.assertEqual(len(ids), 2)
        self.assertTrue(all(isinstance(id_generado, int) for id_generado in ids))
        recuperados = self.repo.obtener_por_hospedajes([hospedaje_1, hospedaje_2])
        self.assertEqual(recuperados[hospedaje_1].id, ids[0])
        self.assertEqual(recuperados[hospedaje_2].id, ids[1])
        self.assertEqual(self._contar_analisis(), 2)

    def test_con_error_en_el_ultimo_la_tabla_queda_sin_filas_parciales(self):
        destino_id = self.crear_destino(ciudad=_ciudad_unica())
        hospedaje_1 = self.crear_hospedaje(destino_id, nombre="Hotel A")
        lote = self._crear_lote([hospedaje_1, hospedaje_1])
        analisis_antes = self._contar_analisis()

        with self.assertRaises(errors.UniqueViolation):
            self.repo.guardar_lote(lote)

        self.assertEqual(self._contar_analisis(), analisis_antes)

    def test_con_hospedaje_inexistente_la_tabla_queda_sin_filas(self):
        destino_id = self.crear_destino(ciudad=_ciudad_unica())
        hospedaje_1 = self.crear_hospedaje(destino_id, nombre="Hotel A")
        lote = self._crear_lote([hospedaje_1])
        lote.append(Analisis(
            resumen_ejecutivo="Huérfano",
            puntos_fuertes="Ninguno",
            puntos_debiles="FK inexistente",
            hospedaje_id=999999,
        ))
        analisis_antes = self._contar_analisis()

        with self.assertRaises(psycopg2.IntegrityError):
            self.repo.guardar_lote(lote)

        self.assertEqual(self._contar_analisis(), analisis_antes)

    def test_lote_vacio_no_inserta_nada(self):
        analisis_antes = self._contar_analisis()

        self.assertEqual(self.repo.guardar_lote([]), [])
        self.assertEqual(self._contar_analisis(), analisis_antes)


if __name__ == "__main__":
    unittest.main()

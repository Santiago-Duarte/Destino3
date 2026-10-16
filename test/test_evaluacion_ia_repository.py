import unittest
import uuid
from pathlib import Path

import psycopg2
from psycopg2 import errors

import src.repositories
from src.models.evaluacion import Evaluacion
from src.repositories.evaluacion_ia_repository import EvaluacionIARepository
from test.db_test_case import BaseDBTestCase


def _ciudad_unica():
    return f"Medellin_{uuid.uuid4().hex}"


class TestEvaluacionIARepository(BaseDBTestCase):

    def setUp(self):
        super().setUp()
        self.repo = EvaluacionIARepository()

    def test_guardar_y_recuperar_evaluacion(self):
        destino_id = self.crear_destino(ciudad=_ciudad_unica())
        hospedaje_id = self.crear_hospedaje(destino_id)

        evaluacion = Evaluacion(
            resumen_ejecutivo="Excelente opción cerca al centro",
            puntos_fuertes="Ubicación céntrica, desayuno incluido",
            puntos_debiles="Ruido nocturno",
            score_calidad_precio=8,
            hospedaje_id=hospedaje_id,
        )

        evaluacion_id = self.repo.guardar(evaluacion)
        self.assertIsNotNone(evaluacion_id)

        recuperada = self.repo.obtener_por_hospedaje(hospedaje_id)
        self.assertIsNotNone(recuperada)
        self.assertEqual(recuperada.resumen_ejecutivo, "Excelente opción cerca al centro")
        self.assertEqual(recuperada.puntos_fuertes, "Ubicación céntrica, desayuno incluido")
        self.assertEqual(recuperada.puntos_debiles, "Ruido nocturno")
        self.assertEqual(recuperada.score_calidad_precio, 8)

    def test_duplicar_evaluacion_mismo_hospedaje_falla(self):
        destino_id = self.crear_destino(ciudad=_ciudad_unica())
        hospedaje_id = self.crear_hospedaje(destino_id)

        evaluacion = Evaluacion(
            resumen_ejecutivo="Primera evaluación",
            puntos_fuertes="Puntos fuertes",
            puntos_debiles="Puntos débiles",
            score_calidad_precio=7,
            hospedaje_id=hospedaje_id,
        )

        self.repo.guardar(evaluacion)

        evaluacion_duplicada = Evaluacion(
            resumen_ejecutivo="Segunda evaluación",
            puntos_fuertes="Otros puntos fuertes",
            puntos_debiles="Otros puntos débiles",
            score_calidad_precio=9,
            hospedaje_id=hospedaje_id,
        )

        with self.assertRaises(errors.UniqueViolation):
            self.repo.guardar(evaluacion_duplicada)


class TestGuardarLoteEvaluaciones(BaseDBTestCase):
    """RF-7, RF-8 (tarea C2): el lote de evaluaciones se persiste todo-o-nada."""

    def setUp(self):
        super().setUp()
        self.repo = EvaluacionIARepository()

    def _crear_lote(self, hospedaje_ids):
        return [
            Evaluacion(
                resumen_ejecutivo=f"Evaluación {i}",
                puntos_fuertes=f"Fuertes {i}",
                puntos_debiles=f"Débiles {i}",
                score_calidad_precio=5 + i,
                hospedaje_id=hospedaje_id,
            )
            for i, hospedaje_id in enumerate(hospedaje_ids, start=1)
        ]

    def _contar_evaluaciones(self, hospedaje_id=None):
        with self.conexion.cursor() as cursor:
            if hospedaje_id is None:
                cursor.execute("SELECT COUNT(*) FROM evaluaciones_ia;")
            else:
                cursor.execute(
                    "SELECT COUNT(*) FROM evaluaciones_ia WHERE hospedaje_id = %s;",
                    (hospedaje_id,),
                )
            return cursor.fetchone()[0]

    def test_guardar_lote_devuelve_ids_enteros_asociados_a_su_hospedaje(self):
        destino_id = self.crear_destino(ciudad=_ciudad_unica())
        hospedaje_1 = self.crear_hospedaje(destino_id, nombre="Hotel A")
        hospedaje_2 = self.crear_hospedaje(destino_id, nombre="Hotel B")

        ids = self.repo.guardar_lote(self._crear_lote([hospedaje_1, hospedaje_2]))

        self.assertEqual(len(ids), 2)
        for id_generado in ids:
            self.assertIsInstance(id_generado, int)

        recuperada_1 = self.repo.obtener_por_hospedaje(hospedaje_1)
        recuperada_2 = self.repo.obtener_por_hospedaje(hospedaje_2)
        self.assertEqual(recuperada_1.id, ids[0])
        self.assertEqual(recuperada_1.hospedaje_id, hospedaje_1)
        self.assertEqual(recuperada_1.score_calidad_precio, 6)
        self.assertEqual(recuperada_2.id, ids[1])
        self.assertEqual(recuperada_2.hospedaje_id, hospedaje_2)
        self.assertEqual(self._contar_evaluaciones(hospedaje_1), 1)
        self.assertEqual(self._contar_evaluaciones(hospedaje_2), 1)

    def test_con_error_en_el_ultimo_la_tabla_queda_sin_filas_parciales(self):
        destino_id = self.crear_destino(ciudad=_ciudad_unica())
        hospedaje_1 = self.crear_hospedaje(destino_id, nombre="Hotel A")
        lote = self._crear_lote([hospedaje_1, hospedaje_1])
        evaluaciones_antes = self._contar_evaluaciones(hospedaje_1)

        with self.assertRaises(errors.UniqueViolation):
            self.repo.guardar_lote(lote)

        self.assertEqual(self._contar_evaluaciones(hospedaje_1), evaluaciones_antes)

    def test_con_hospedaje_inexistente_la_tabla_queda_sin_filas(self):
        destino_id = self.crear_destino(ciudad=_ciudad_unica())
        hospedaje_1 = self.crear_hospedaje(destino_id, nombre="Hotel A")
        lote = self._crear_lote([hospedaje_1])
        lote.append(
            Evaluacion(
                resumen_ejecutivo="Huérfana",
                puntos_fuertes="Ninguno",
                puntos_debiles="FK inexistente",
                score_calidad_precio=3,
                hospedaje_id=999999,
            )
        )
        evaluaciones_antes = self._contar_evaluaciones(hospedaje_1)

        with self.assertRaises(psycopg2.IntegrityError):
            self.repo.guardar_lote(lote)

        self.assertEqual(self._contar_evaluaciones(hospedaje_1), evaluaciones_antes)

    def test_lote_vacio_no_inserta_nada(self):
        evaluaciones_antes = self._contar_evaluaciones()

        self.assertEqual(self.repo.guardar_lote([]), [])
        self.assertEqual(self._contar_evaluaciones(), evaluaciones_antes)

    def test_los_repositories_no_mencionan_id_temporal(self):
        """C2: id_temporal jamás llega a la capa de SQL (constitución #4)."""
        repositorio = Path(src.repositories.__file__).parent
        offenders = []
        for archivo in repositorio.glob("*.py"):
            if "id_temporal" in archivo.read_text(encoding="utf-8"):
                offenders.append(archivo.name)
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()

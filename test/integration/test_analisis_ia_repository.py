import uuid
from unittest.mock import patch

import psycopg2

from src.models.analisis import Analisis
from src.repositories.analisis_ia_repository import AnalisisIARepository
from test.caso_prueba_bd import BaseDBTestCase


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

        analisis_id = self.repo.guardar_lote([analisis])[0]
        self.assertIsNotNone(analisis_id)

        recuperado = self.repo.obtener_por_hospedajes([hospedaje_id])[hospedaje_id]
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
        self.assertIn("version", columnas)
        self.assertIn("actualizado_en", columnas)
        self.assertNotIn("score_calidad_precio", columnas)

    def test_duplicar_analisis_del_mismo_hospedaje_actualiza_la_fila(self):
        destino_id = self.crear_destino(ciudad=_ciudad_unica())
        hospedaje_id = self.crear_hospedaje(destino_id)

        primer_id = self.repo.guardar_lote([Analisis(
            resumen_ejecutivo="Primera versión",
            puntos_fuertes="Fuertes",
            puntos_debiles="Débiles",
            hospedaje_id=hospedaje_id,
        )])[0]
        segundo_id = self.repo.guardar_lote([Analisis(
            resumen_ejecutivo="Segunda versión",
            puntos_fuertes="Otros fuertes",
            puntos_debiles="Otros débiles",
            hospedaje_id=hospedaje_id,
        )])[0]

        self.assertEqual(primer_id, segundo_id)
        recuperado = self.repo.obtener_por_hospedajes([hospedaje_id])[hospedaje_id]
        self.assertEqual(recuperado.resumen_ejecutivo, "Segunda versión")
        self.assertEqual(recuperado.puntos_fuertes, "Otros fuertes")

    @patch("src.repositories.analisis_ia_repository.settings.ANALISIS_VERSION", 2)
    def test_un_analisis_de_otra_version_se_ignora_y_se_regenera(self):
        destino_id = self.crear_destino(ciudad=_ciudad_unica())
        hospedaje_id = self.crear_hospedaje(destino_id)
        with patch(
                "src.repositories.analisis_ia_repository.settings.ANALISIS_VERSION",
                1,
        ):
            self.repo.guardar_lote([Analisis(
                resumen_ejecutivo="Análisis de la versión anterior",
                puntos_fuertes="Fuertes",
                puntos_debiles="Débiles",
                hospedaje_id=hospedaje_id,
            )])

        self.assertEqual(self.repo.obtener_por_hospedajes([hospedaje_id]), {})

        self.repo.guardar_lote([Analisis(
            resumen_ejecutivo="Análisis regenerado",
            puntos_fuertes="Nuevos fuertes",
            puntos_debiles="Nuevos débiles",
            hospedaje_id=hospedaje_id,
        )])

        recuperado = self.repo.obtener_por_hospedajes([hospedaje_id])[hospedaje_id]
        self.assertEqual(recuperado.resumen_ejecutivo, "Análisis regenerado")


class TestObtenerPorVariosHospedajes(BaseDBTestCase):

    def setUp(self):
        super().setUp()
        self.repo = AnalisisIARepository()

    def test_devuelve_solo_los_analisis_que_existen(self):
        destino_id = self.crear_destino(ciudad=_ciudad_unica())
        con_analisis = self.crear_hospedaje(destino_id, nombre="Hotel A")
        sin_analisis = self.crear_hospedaje(destino_id, nombre="Hotel B")
        self.repo.guardar_lote([Analisis(
            resumen_ejecutivo="Análisis de A",
            puntos_fuertes="Fuertes",
            puntos_debiles="Débiles",
            hospedaje_id=con_analisis,
        )])

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

    def test_con_error_en_medio_del_lote_la_tabla_queda_sin_filas_parciales(self):
        destino_id = self.crear_destino(ciudad=_ciudad_unica())
        hospedaje_1 = self.crear_hospedaje(destino_id, nombre="Hotel A")
        hospedaje_2 = self.crear_hospedaje(destino_id, nombre="Hotel B")
        lote = self._crear_lote([hospedaje_1, hospedaje_2])
        # Insertar uno inválido EN MEDIO
        lote.insert(1, Analisis(
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



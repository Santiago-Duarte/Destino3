import uuid

import psycopg2
from psycopg2 import sql

from test.db_test_case import BaseDBTestCase


class TestContratoEsquema(BaseDBTestCase):
    def test_google_place_id_es_nullable_y_tiene_indice_unico_valido(self):
        with self.conexion.cursor() as cursor:
            cursor.execute(
                "SELECT data_type, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = %s AND column_name = %s",
                ("public", "hospedajes", "google_place_id"),
            )
            columna = cursor.fetchone()

            cursor.execute(
                "SELECT i.indisunique, i.indisvalid, i.indisready, "
                "i.indpred IS NULL, pg_get_indexdef(i.indexrelid) "
                "FROM pg_class AS indice "
                "JOIN pg_namespace AS esquema ON esquema.oid = indice.relnamespace "
                "JOIN pg_index AS i ON i.indexrelid = indice.oid "
                "WHERE esquema.nspname = %s AND indice.relname = %s",
                ("public", "idx_hospedajes_google_place_id_unico"),
            )
            indice = cursor.fetchone()

        self.assertEqual(columna, ("text", "YES"))
        self.assertIsNotNone(indice)
        self.assertEqual(indice[:4], (True, True, True, True))
        self.assertIn("(google_place_id)", indice[4])

    def test_esquema_conserva_las_claves_foraneas_esperadas(self):
        esperadas = {
            ("atracciones", "FOREIGN KEY (hospedaje_id) REFERENCES hospedajes(id) ON DELETE CASCADE"),
            ("busquedas", "FOREIGN KEY (destino_id) REFERENCES destinos(id) ON DELETE CASCADE"),
            ("busquedas", "FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE"),
            ("evaluaciones_ia", "FOREIGN KEY (hospedaje_id) REFERENCES hospedajes(id) ON DELETE CASCADE"),
            ("hospedajes", "FOREIGN KEY (destino_id) REFERENCES destinos(id) ON DELETE CASCADE"),
            ("recomendaciones", "FOREIGN KEY (busqueda_id) REFERENCES busquedas(id) ON DELETE CASCADE"),
            ("recomendaciones", "FOREIGN KEY (hospedaje_id) REFERENCES hospedajes(id) ON DELETE CASCADE"),
        }

        with self.conexion.cursor() as cursor:
            cursor.execute(
                "SELECT conrelid::regclass::text, pg_get_constraintdef(oid) "
                "FROM pg_constraint "
                "WHERE connamespace = 'public'::regnamespace AND contype = 'f'"
            )
            encontradas = {
                (tabla, " ".join(definicion.split()))
                for tabla, definicion in cursor.fetchall()
            }

        self.assertTrue(esperadas.issubset(encontradas))

    def test_esquema_conserva_las_restricciones_check_esperadas(self):
        esperadas = {
            ("hospedajes", "hospedajes_tipo_check"),
            ("evaluaciones_ia", "evaluaciones_ia_score_calidad_precio_check"),
            ("busquedas", "chk_busqueda_presupuesto"),
            ("busquedas", "chk_busqueda_fechas"),
            ("recomendaciones", "chk_recomendacion_posicion"),
        }

        with self.conexion.cursor() as cursor:
            cursor.execute(
                "SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid) "
                "FROM pg_constraint "
                "WHERE connamespace = 'public'::regnamespace AND contype = 'c'"
            )
            checks = {
                (tabla, nombre): " ".join(definicion.lower().split())
                for tabla, nombre, definicion in cursor.fetchall()
            }

        self.assertTrue(esperadas.issubset(checks))
        self.assertIn("'hotel'", checks[("hospedajes", "hospedajes_tipo_check")])
        self.assertIn("'airbnb'", checks[("hospedajes", "hospedajes_tipo_check")])
        self.assertIn("'otro'", checks[("hospedajes", "hospedajes_tipo_check")])
        self.assertIn(
            "score_calidad_precio >= 1",
            checks[("evaluaciones_ia", "evaluaciones_ia_score_calidad_precio_check")],
        )
        self.assertIn(
            "score_calidad_precio <= 10",
            checks[("evaluaciones_ia", "evaluaciones_ia_score_calidad_precio_check")],
        )
        self.assertIn(
            "presupuesto >",
            checks[("busquedas", "chk_busqueda_presupuesto")],
        )
        self.assertIn(
            "(0)::numeric",
            checks[("busquedas", "chk_busqueda_presupuesto")],
        )
        self.assertIn(
            "fecha_fin >= fecha_inicio",
            checks[("busquedas", "chk_busqueda_fechas")],
        )
        self.assertIn(
            "posicion >= 1",
            checks[("recomendaciones", "chk_recomendacion_posicion")],
        )
        self.assertIn(
            "posicion <= 3",
            checks[("recomendaciones", "chk_recomendacion_posicion")],
        )

    def _snapshot_esquema_publico(self):
        with self.conexion.cursor() as cursor:
            cursor.execute(
                "SELECT table_name, column_name, ordinal_position, data_type, "
                "is_nullable, column_default "
                "FROM information_schema.columns "
                "WHERE table_schema = %s ORDER BY table_name, ordinal_position",
                ("public",),
            )
            columnas = tuple(cursor.fetchall())
            cursor.execute(
                "SELECT tablename, indexname, indexdef FROM pg_indexes "
                "WHERE schemaname = %s ORDER BY tablename, indexname",
                ("public",),
            )
            indices = tuple(cursor.fetchall())
            cursor.execute(
                "SELECT conrelid::regclass::text, conname, contype, "
                "pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE connamespace = 'public'::regnamespace "
                "ORDER BY conrelid::regclass::text, conname"
            )
            restricciones = tuple(cursor.fetchall())
        return columnas, indices, restricciones

    def test_ddl_fallida_revierte_esquema_temporal_y_no_cambia_el_publico(self):
        esquema_antes = self._snapshot_esquema_publico()
        tabla_temporal = f"g3_rollback_{uuid.uuid4().hex}"
        crear_tabla = sql.SQL("CREATE TEMP TABLE {} (id INTEGER PRIMARY KEY)").format(
            sql.Identifier(tabla_temporal)
        )

        with self.conexion.cursor() as cursor:
            cursor.execute(crear_tabla)
            with self.assertRaises(psycopg2.errors.DuplicateTable):
                cursor.execute(crear_tabla)

        self.conexion.rollback()

        with self.conexion.cursor() as cursor:
            cursor.execute(
                "SELECT EXISTS ("
                "SELECT 1 FROM pg_class "
                "WHERE relname = %s AND relpersistence = 't'"
                ")",
                (tabla_temporal,),
            )
            tabla_temporal_persistida = cursor.fetchone()[0]

        self.assertFalse(tabla_temporal_persistida)
        self.assertEqual(self._snapshot_esquema_publico(), esquema_antes)

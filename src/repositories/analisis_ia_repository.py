from src.config import settings
from src.models.analisis import Analisis
from src.repositories.base_repository import BaseRepository


class AnalisisIARepository(BaseRepository):

    def guardar_lote(self, analisis: list[Analisis]) -> list[int]:
        """Persiste el análisis y devuelve un id por cada elemento.

        ``UNIQUE (hospedaje_id)`` convierte el insert en upsert: si el hotel
        ya tenía análisis se refresca, y un duplicado dentro del lote no
        rompe la transacción. La versión permite invalidar análisis viejos
        cuando cambia el prompt que los generó.
        """
        if not analisis:
            return []

        guardar_analisis = """
            INSERT INTO analisis_ia (
                resumen_ejecutivo, puntos_fuertes, puntos_debiles,
                hospedaje_id, version, actualizado_en
            )
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (hospedaje_id) DO UPDATE SET
                resumen_ejecutivo = EXCLUDED.resumen_ejecutivo,
                puntos_fuertes = EXCLUDED.puntos_fuertes,
                puntos_debiles = EXCLUDED.puntos_debiles,
                version = EXCLUDED.version,
                actualizado_en = CURRENT_TIMESTAMP
            RETURNING id;
        """

        with self._transaccion() as cursor:
            ids_generados = []
            for item in analisis:
                cursor.execute(
                    guardar_analisis,
                    (
                        item.resumen_ejecutivo,
                        item.puntos_fuertes,
                        item.puntos_debiles,
                        item.hospedaje_id,
                        settings.ANALISIS_VERSION,
                    ),
                )
                ids_generados.append(cursor.fetchone()[0])
            return ids_generados

    def obtener_por_hospedajes(self, hospedaje_ids: list[int]) -> dict[int, Analisis]:
        if not hospedaje_ids:
            return {}

        with self._transaccion() as cursor:
            cursor.execute(
                """
                SELECT id, resumen_ejecutivo, puntos_fuertes, puntos_debiles, hospedaje_id
                FROM analisis_ia
                WHERE hospedaje_id = ANY(%s) AND version = %s;
                """,
                (hospedaje_ids, settings.ANALISIS_VERSION),
            )
            return {
                fila[4]: Analisis(
                    id=fila[0],
                    resumen_ejecutivo=fila[1],
                    puntos_fuertes=fila[2],
                    puntos_debiles=fila[3],
                    hospedaje_id=fila[4],
                )
                for fila in cursor.fetchall()
            }

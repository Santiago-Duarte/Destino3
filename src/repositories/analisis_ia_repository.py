from src.models.analisis import Analisis
from src.repositories.base_repository import BaseRepository


class AnalisisIARepository(BaseRepository):

    def guardar_lote(self, analisis: list[Analisis]) -> list[int]:
        if not analisis:
            return []

        # El análisis se liga al id real del hospedaje, no a un índice temporal del lote.
        insertar_analisis = """
            INSERT INTO analisis_ia (
                resumen_ejecutivo, puntos_fuertes, puntos_debiles, hospedaje_id
            )
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """

        with self._transaccion() as cursor:
            ids_generados = []
            for item in analisis:
                cursor.execute(
                    insertar_analisis,
                    (
                        item.resumen_ejecutivo,
                        item.puntos_fuertes,
                        item.puntos_debiles,
                        item.hospedaje_id,
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
                WHERE hospedaje_id = ANY(%s);
                """,
                (hospedaje_ids,),
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

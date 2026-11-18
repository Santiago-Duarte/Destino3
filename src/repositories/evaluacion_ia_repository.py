from src.models.evaluacion import Evaluacion
from src.repositories.base_repository import BaseRepository


class EvaluacionIARepository(BaseRepository):

    def guardar_lote(self, evaluaciones: list[Evaluacion]) -> list[int]:
        if not evaluaciones:
            return []

        # `id_temporal` es efímero: nunca se persiste.
        insertar_evaluacion = """
            INSERT INTO evaluaciones_ia (
                resumen_ejecutivo, puntos_fuertes, puntos_debiles,
                score_calidad_precio, hospedaje_id
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """

        with self._transaccion() as cursor:
            ids_generados = []
            for evaluacion in evaluaciones:
                cursor.execute(
                    insertar_evaluacion,
                    (
                        evaluacion.resumen_ejecutivo,
                        evaluacion.puntos_fuertes,
                        evaluacion.puntos_debiles,
                        evaluacion.score_calidad_precio,
                        evaluacion.hospedaje_id,
                    ),
                )
                ids_generados.append(cursor.fetchone()[0])
            return ids_generados

    def guardar(self, evaluacion: Evaluacion) -> int:
        return self.guardar_lote([evaluacion])[0]

    def obtener_por_hospedaje(self, hospedaje_id: int) -> Evaluacion | None:
        with self._transaccion() as cursor:
            cursor.execute(
                """
                SELECT id, resumen_ejecutivo, puntos_fuertes, puntos_debiles,
                score_calidad_precio, hospedaje_id
                FROM evaluaciones_ia
                WHERE hospedaje_id = %s;
                """,
                (hospedaje_id,),
            )
            fila = cursor.fetchone()
            if fila is None:
                return None
            return Evaluacion(
                id=fila[0],
                resumen_ejecutivo=fila[1],
                puntos_fuertes=fila[2],
                puntos_debiles=fila[3],
                score_calidad_precio=fila[4],
                hospedaje_id=fila[5],
            )

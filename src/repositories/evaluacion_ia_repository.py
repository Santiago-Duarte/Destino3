from src.models.evaluacion import Evaluacion
from src.repositories.base_repository import BaseRepository


class EvaluacionIARepository(BaseRepository):

    def guardar_lote(self, evaluaciones: list[Evaluacion]) -> list[int]:
        """Inserta un lote de evaluaciones en una sola transacción (todo-o-nada).

        Solo se persisten campos de negocio más ``hospedaje_id`` real: la tabla
        ``evaluaciones_ia`` nunca recibe los tokens de correlación efímeros de
        la IA (constitución #4), que quedan reservados para el ciclo en memoria
        con el proveedor.

        Returns:
            Los ids generados, uno por cada evaluación, en el mismo orden.
        """
        if not evaluaciones:
            return []

        consulta = """
            INSERT INTO evaluaciones_ia (resumen_ejecutivo, puntos_fuertes, puntos_debiles, score_calidad_precio, hospedaje_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """

        with self._transaccion() as cursor:
            ids = []
            for evaluacion in evaluaciones:
                cursor.execute(
                    consulta,
                    (
                        evaluacion.resumen_ejecutivo,
                        evaluacion.puntos_fuertes,
                        evaluacion.puntos_debiles,
                        evaluacion.score_calidad_precio,
                        evaluacion.hospedaje_id,
                    )
                )
                ids.append(cursor.fetchone()[0])
            return ids

    def guardar(self, evaluacion: Evaluacion) -> int:
        return self.guardar_lote([evaluacion])[0]

    def obtener_por_hospedaje(self, hospedaje_id: int) -> Evaluacion | None:
        with self._transaccion() as cursor:
            cursor.execute(
                """
                SELECT id, resumen_ejecutivo, puntos_fuertes, puntos_debiles, score_calidad_precio, hospedaje_id
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

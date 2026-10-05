from src.models.hospedaje import Hospedaje
from src.repositories.base_repository import BaseRepository


class HospedajeRepository(BaseRepository):

    def guardar_lote(self, hospedajes: list[Hospedaje]) -> list[int]:
        """Inserta un lote de hospedajes en una sola transacción (todo-o-nada).

        Returns:
            Los ids generados, uno por cada hospedaje, en el mismo orden.
        """
        consulta = """
            INSERT INTO hospedajes (nombre, tipo, precio_noche, calificacion, direccion, url_reserva, destino_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """

        with self._transaccion() as cursor:
            ids = []
            for hospedaje in hospedajes:
                cursor.execute(
                    consulta,
                    (
                        hospedaje.nombre, hospedaje.tipo,
                        hospedaje.precio_noche, hospedaje.calificacion,
                        hospedaje.direccion, hospedaje.url_reserva,
                        hospedaje.destino_id
                    )
                )
                ids.append(cursor.fetchone()[0])
            return ids

    def obtener_por_destino(self, destino_id: int) -> list[Hospedaje]:
        with self._transaccion() as cursor:
            cursor.execute(
                """
                SELECT id, nombre, tipo, precio_noche, calificacion,
                direccion, url_reserva, destino_id FROM hospedajes
                WHERE destino_id = %s;
                """,
                (destino_id,),
            )
            return [
                Hospedaje(
                    id=fila[0],
                    nombre=fila[1],
                    tipo=fila[2],
                    precio_noche=fila[3],
                    calificacion=fila[4],
                    direccion=fila[5],
                    url_reserva=fila[6],
                    destino_id=fila[7]
                )
                for fila in cursor.fetchall()
            ]

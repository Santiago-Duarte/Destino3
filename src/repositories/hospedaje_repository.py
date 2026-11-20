from src.models.hospedaje import Hospedaje
from src.repositories.base_repository import BaseRepository


class HospedajeRepository(BaseRepository):

    def guardar_lote(self, hospedajes: list[Hospedaje]) -> list[int]:
        if not hospedajes:
            return []

        insertar_hospedaje = """
            INSERT INTO hospedajes (
                nombre, tipo, precio_noche, calificacion, direccion,
                url_reserva, destino_id, google_place_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        actualizar_hospedaje = """
            UPDATE hospedajes
            SET precio_noche = %s, calificacion = %s, url_reserva = %s
            WHERE id = %s;
        """

        with self._transaccion() as cursor:
            existentes = self._existentes_por_token(cursor, hospedajes)
            ids_generados = []
            for hospedaje in hospedajes:
                id_ya_persistido = existentes.get(hospedaje.google_place_id)
                if id_ya_persistido is not None:
                    # Ya existe: se reutiliza la fila y se refrescan los datos que cambian por búsqueda.
                    cursor.execute(
                        actualizar_hospedaje,
                        (
                            hospedaje.precio_noche,
                            hospedaje.calificacion,
                            hospedaje.url_reserva,
                            id_ya_persistido,
                        ),
                    )
                    ids_generados.append(id_ya_persistido)
                    continue

                cursor.execute(
                    insertar_hospedaje,
                    (
                        hospedaje.nombre, hospedaje.tipo,
                        hospedaje.precio_noche, hospedaje.calificacion,
                        hospedaje.direccion, hospedaje.url_reserva,
                        hospedaje.destino_id, hospedaje.google_place_id,
                    ),
                )
                ids_generados.append(cursor.fetchone()[0])
            return ids_generados

    @staticmethod
    def _existentes_por_token(cursor, hospedajes: list[Hospedaje]) -> dict[str, int]:
        tokens = [hospedaje.google_place_id for hospedaje in hospedajes if hospedaje.google_place_id]
        if not tokens:
            return {}

        cursor.execute(
            "SELECT id, google_place_id FROM hospedajes WHERE google_place_id = ANY(%s);",
            (tokens,),
        )
        return {fila[1]: fila[0] for fila in cursor.fetchall()}

    def obtener_por_destino(self, destino_id: int) -> list[Hospedaje]:
        with self._transaccion() as cursor:
            cursor.execute(
                """
                SELECT id, nombre, tipo, precio_noche, calificacion,
                direccion, url_reserva, destino_id, google_place_id
                FROM hospedajes
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
                    destino_id=fila[7],
                    google_place_id=fila[8],
                )
                for fila in cursor.fetchall()
            ]

from src.models.hospedaje import Hospedaje
from src.repositories.base_repository import BaseRepository


class HospedajeRepository(BaseRepository):

    def guardar_lote(self, hospedajes: list[Hospedaje]) -> list[int]:
        """Persiste el lote y devuelve un id por cada hospedaje recibido.

        Con token de Google se hace upsert por ``google_place_id``: resuelve
        duplicados dentro del lote, carreras entre búsquedas y refresca todos
        los datos mutables. Sin token se inserta una fila nueva.
        """
        if not hospedajes:
            return []

        insertar_con_token = """
            INSERT INTO hospedajes (
                nombre, tipo, precio_noche, calificacion, descripcion,
                direccion, url_reserva, destino_id, google_place_id,
                latitud, longitud
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (google_place_id) DO UPDATE SET
                nombre = EXCLUDED.nombre,
                tipo = EXCLUDED.tipo,
                precio_noche = EXCLUDED.precio_noche,
                calificacion = EXCLUDED.calificacion,
                descripcion = EXCLUDED.descripcion,
                direccion = EXCLUDED.direccion,
                url_reserva = EXCLUDED.url_reserva,
                destino_id = EXCLUDED.destino_id,
                latitud = COALESCE(EXCLUDED.latitud, hospedajes.latitud),
                longitud = COALESCE(EXCLUDED.longitud, hospedajes.longitud)
            RETURNING id;
        """
        insertar_sin_token = """
            INSERT INTO hospedajes (
                nombre, tipo, precio_noche, calificacion, descripcion,
                direccion, url_reserva, destino_id, google_place_id,
                latitud, longitud
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, %s)
            RETURNING id;
        """

        with self._transaccion() as cursor:
            ids_generados = []
            for hospedaje in hospedajes:
                parametros = (
                    hospedaje.nombre,
                    hospedaje.tipo,
                    hospedaje.precio_noche,
                    hospedaje.calificacion,
                    hospedaje.descripcion,
                    hospedaje.direccion,
                    hospedaje.url_reserva,
                    hospedaje.destino_id,
                )
                if hospedaje.google_place_id:
                    cursor.execute(
                        insertar_con_token,
                        (*parametros, hospedaje.google_place_id,
                         hospedaje.latitud, hospedaje.longitud),
                    )
                else:
                    cursor.execute(
                        insertar_sin_token,
                        (*parametros, hospedaje.latitud, hospedaje.longitud),
                    )
                ids_generados.append(cursor.fetchone()[0])
            return ids_generados

    def obtener_por_destino(self, destino_id: int) -> list[Hospedaje]:
        with self._transaccion() as cursor:
            cursor.execute(
                """
                SELECT id, nombre, tipo, precio_noche, calificacion,
                descripcion, direccion, url_reserva, destino_id, google_place_id,
                latitud, longitud
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
                    descripcion=fila[5],
                    direccion=fila[6],
                    url_reserva=fila[7],
                    destino_id=fila[8],
                    google_place_id=fila[9],
                    latitud=fila[10],
                    longitud=fila[11],
                )
                for fila in cursor.fetchall()
            ]

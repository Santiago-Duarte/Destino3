from src.models.busqueda import Busqueda
from src.repositories.base_repository import BaseRepository


class BusquedaRepository(BaseRepository):

    def guardar(self, busqueda: Busqueda) -> int:
        with self._transaccion() as cursor:
            cursor.execute(
                """INSERT INTO busquedas (usuario_id, destino_id, zona, presupuesto, fecha_inicio, fecha_fin)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;""",
                (busqueda.usuario_id,
                 busqueda.destino_id,
                 busqueda.zona,
                 busqueda.presupuesto,
                 busqueda.fecha_inicio,
                 busqueda.fecha_fin)
            )
            return cursor.fetchone()[0]

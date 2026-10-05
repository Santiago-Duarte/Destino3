from src.models.recomendacion import Recomendacion
from src.repositories.base_repository import BaseRepository


class RecomendacionRepository(BaseRepository):

    def guardar_lote(self, recomendaciones: list[Recomendacion]) -> None:
        """Inserta las recomendaciones de una búsqueda en una sola transacción (todo-o-nada)."""
        with self._transaccion() as cursor:
            for recomendacion in recomendaciones:
                cursor.execute(
                    "INSERT INTO recomendaciones (busqueda_id, hospedaje_id, posicion) VALUES (%s, %s, %s);",
                    (recomendacion.busqueda_id, recomendacion.hospedaje_id, recomendacion.posicion)
                )

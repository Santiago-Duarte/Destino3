from src.exceptions import PersistenciaError
from src.models.destino import Destino
from src.repositories.base_repository import BaseRepository


class DestinoRepository(BaseRepository):

    @staticmethod
    def _normalizar_ciudad_y_pais(destino: Destino) -> tuple[str, str]:
        ciudad = (destino.ciudad or "").strip()
        pais = (destino.pais or "").strip()
        if not ciudad or not pais:
            raise ValueError("La ciudad y el país del destino son obligatorios")
        return ciudad, pais

    def guardar(self, destino: Destino) -> int:
        ciudad, pais = self._normalizar_ciudad_y_pais(destino)

        with self._transaccion() as cursor:
            cursor.execute(
                "INSERT INTO destinos (ciudad, pais) VALUES (%s, %s) RETURNING id;",
                (ciudad, pais),
            )
            return cursor.fetchone()[0]

    def obtener_todos(self) -> list[Destino]:
        with self._transaccion() as cursor:
            cursor.execute("SELECT id, ciudad, pais FROM destinos;")
            return [
                Destino(id=fila[0], ciudad=fila[1], pais=fila[2])
                for fila in cursor.fetchall()
            ]

    def obtener_o_crear(self, destino: Destino) -> int:
        ciudad, pais = self._normalizar_ciudad_y_pais(destino)

        buscar_destino = (
            "SELECT id FROM destinos "
            "WHERE LOWER(TRIM(ciudad)) = LOWER(%s) AND LOWER(TRIM(pais)) = LOWER(%s);"
        )

        with self._transaccion() as cursor:
            cursor.execute(buscar_destino, (ciudad, pais))
            fila_existente = cursor.fetchone()
            if fila_existente:
                return fila_existente[0]

            cursor.execute(
                "INSERT INTO destinos (ciudad, pais) VALUES (%s, %s) "
                "ON CONFLICT DO NOTHING RETURNING id;",
                (ciudad, pais),
            )
            fila_insertada = cursor.fetchone()
            if fila_insertada:
                return fila_insertada[0]

            # Otra transacción insertó el destino entre el SELECT y el INSERT.
            cursor.execute(buscar_destino, (ciudad, pais))
            fila_existente = cursor.fetchone()
            if fila_existente:
                return fila_existente[0]
            raise PersistenciaError(
                "PostgreSQL",
                "obtener_o_crear_destino",
                f"No se pudo obtener ni crear el destino {ciudad}/{pais}",
            )

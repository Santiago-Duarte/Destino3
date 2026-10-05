from src.models.destino import Destino
from src.repositories.base_repository import BaseRepository


class DestinoRepository(BaseRepository):

    @staticmethod
    def _ciudad_y_pais_validados(destino: Destino) -> tuple[str, str]:
        ciudad = (destino.ciudad or "").strip()
        pais = (destino.pais or "").strip()
        if not ciudad or not pais:
            raise ValueError("La ciudad y el país del destino son obligatorios")
        return ciudad, pais

    def guardar(self, destino: Destino) -> int:
        ciudad, pais = self._ciudad_y_pais_validados(destino)

        with self._transaccion() as cursor:
            cursor.execute(
                "INSERT INTO destinos (ciudad, pais) VALUES (%s, %s) RETURNING id;",
                (ciudad, pais),
            )
            return cursor.fetchone()[0]

    def obtener_todos(self) -> list[Destino]:
        with self._transaccion() as cursor:
            cursor.execute("SELECT id, ciudad, pais FROM destinos;")
            return [Destino(id=fila[0], ciudad=fila[1], pais=fila[2]) for fila in cursor.fetchall()]

    def obtener_o_crear(self, destino: Destino) -> int:
        """Devuelve el id de un destino por ciudad/país o lo crea si no existe.

        La comparación ignora mayúsculas y espacios sobrantes porque el índice
        único es ``LOWER(TRIM(...))``. Ante una inserción concurrente que
        dispare ese índice único, se vuelve a consultar para recuperar el
        registro que ya insertó la otra transacción.

        Returns:
            El id del destino existente o recién creado.

        Raises:
            ValueError: Si ciudad o país quedan vacíos.
            RuntimeError: Si tras el conflicto de índice la otra transacción ya
                no es visible y no aparece ningún registro.
        """
        ciudad, pais = self._ciudad_y_pais_validados(destino)

        consulta = (
            "SELECT id FROM destinos "
            "WHERE LOWER(TRIM(ciudad)) = LOWER(%s) AND LOWER(TRIM(pais)) = LOWER(%s);"
        )

        with self._transaccion() as cursor:
            cursor.execute(consulta, (ciudad, pais))
            existente = cursor.fetchone()
            if existente:
                return existente[0]

            cursor.execute(
                "INSERT INTO destinos (ciudad, pais) VALUES (%s, %s) ON CONFLICT DO NOTHING RETURNING id;",
                (ciudad, pais),
            )
            insertado = cursor.fetchone()
            if insertado:
                return insertado[0]

            # Carrera: otra transacción insertó el destino entre el SELECT y el INSERT.
            cursor.execute(consulta, (ciudad, pais))
            existente = cursor.fetchone()
            if existente:
                return existente[0]
            raise RuntimeError(f"No se pudo obtener ni crear el destino {ciudad}/{pais}")

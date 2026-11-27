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
                "INSERT INTO destinos (ciudad, pais, latitud, longitud, latitud_ref, longitud_ref, punto_referencia_usado) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;",
                (ciudad, pais, destino.latitud, destino.longitud, destino.latitud_ref, destino.longitud_ref, destino.punto_referencia_usado),
            )
            return cursor.fetchone()[0]

    def obtener_todos(self) -> list[Destino]:
        with self._transaccion() as cursor:
            cursor.execute(
                "SELECT id, ciudad, pais, latitud, longitud, latitud_ref, longitud_ref, punto_referencia_usado FROM destinos;"
            )
            return [
                Destino(
                    id=fila[0],
                    ciudad=fila[1],
                    pais=fila[2],
                    latitud=fila[3],
                    longitud=fila[4],
                    latitud_ref=fila[5],
                    longitud_ref=fila[6],
                    punto_referencia_usado=fila[7],
                )
                for fila in cursor.fetchall()
            ]

    def obtener_por_ciudad_pais(
            self,
            ciudad: str,
            pais: str,
    ) -> Destino | None:
        ciudad = (ciudad or "").strip()
        pais = (pais or "").strip()
        if not ciudad or not pais:
            return None

        with self._transaccion() as cursor:
            cursor.execute(
                "SELECT id, ciudad, pais, latitud, longitud, latitud_ref, longitud_ref, punto_referencia_usado FROM destinos "
                "WHERE LOWER(TRIM(ciudad)) = LOWER(%s) "
                "AND LOWER(TRIM(pais)) = LOWER(%s);",
                (ciudad, pais),
            )
            fila = cursor.fetchone()
            if not fila:
                return None
            return Destino(
                id=fila[0],
                ciudad=fila[1],
                pais=fila[2],
                latitud=fila[3],
                longitud=fila[4],
                latitud_ref=fila[5],
                longitud_ref=fila[6],
                punto_referencia_usado=fila[7],
            )

    def actualizar_coordenadas(
            self,
            destino_id: int,
            latitud: float,
            longitud: float,
    ) -> None:
        with self._transaccion() as cursor:
            cursor.execute(
                "UPDATE destinos SET latitud = %s, longitud = %s WHERE id = %s;",
                (latitud, longitud, destino_id),
            )

    def actualizar_coordenadas_referencia(
            self,
            destino_id: int,
            latitud: float,
            longitud: float,
            punto_referencia: str,
    ) -> None:
        with self._transaccion() as cursor:
            cursor.execute(
                "UPDATE destinos SET latitud_ref = %s, longitud_ref = %s, punto_referencia_usado = %s WHERE id = %s;",
                (latitud, longitud, punto_referencia, destino_id),
            )

    def obtener_o_crear(self, destino: Destino) -> int:
        ciudad, pais = self._normalizar_ciudad_y_pais(destino)

        buscar_destino = (
            "SELECT id, latitud, longitud, latitud_ref, longitud_ref, punto_referencia_usado FROM destinos "
            "WHERE LOWER(TRIM(ciudad)) = LOWER(%s) AND LOWER(TRIM(pais)) = LOWER(%s);"
        )

        with self._transaccion() as cursor:
            cursor.execute(buscar_destino, (ciudad, pais))
            fila_existente = cursor.fetchone()
            if fila_existente:
                self._completar_coordenadas(cursor, fila_existente, destino)
                return fila_existente[0]

            cursor.execute(
                "INSERT INTO destinos (ciudad, pais, latitud, longitud, latitud_ref, longitud_ref, punto_referencia_usado) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT DO NOTHING RETURNING id;",
                (ciudad, pais, destino.latitud, destino.longitud, destino.latitud_ref, destino.longitud_ref, destino.punto_referencia_usado),
            )
            fila_insertada = cursor.fetchone()
            if fila_insertada:
                return fila_insertada[0]

            # Otra transacción insertó el destino entre el SELECT y el INSERT.
            cursor.execute(buscar_destino, (ciudad, pais))
            fila_existente = cursor.fetchone()
            if fila_existente:
                self._completar_coordenadas(cursor, fila_existente, destino)
                return fila_existente[0]
            raise PersistenciaError(
                "PostgreSQL",
                "obtener_o_crear_destino",
                f"No se pudo obtener ni crear el destino {ciudad}/{pais}",
            )

    @staticmethod
    def _completar_coordenadas(cursor, fila, destino: Destino) -> None:
        """Rellena coordenadas del destino existente si le faltan y las tenemos."""
        # Centro de la ciudad
        if destino.latitud is not None and destino.longitud is not None:
            latitud_existente = fila[1] if len(fila) > 1 else None
            longitud_existente = fila[2] if len(fila) > 2 else None
            if latitud_existente is None or longitud_existente is None:
                cursor.execute(
                    "UPDATE destinos SET latitud = %s, longitud = %s WHERE id = %s;",
                    (destino.latitud, destino.longitud, fila[0]),
                )

        # Punto de referencia
        if destino.latitud_ref is not None and destino.longitud_ref is not None and destino.punto_referencia_usado:
            latitud_ref_existente = fila[3] if len(fila) > 3 else None
            longitud_ref_existente = fila[4] if len(fila) > 4 else None
            punto_existente = fila[5] if len(fila) > 5 else None
            if latitud_ref_existente is None or longitud_ref_existente is None or not punto_existente:
                cursor.execute(
                    "UPDATE destinos SET latitud_ref = %s, longitud_ref = %s, punto_referencia_usado = %s WHERE id = %s;",
                    (destino.latitud_ref, destino.longitud_ref, destino.punto_referencia_usado, fila[0]),
                )

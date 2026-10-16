from typing import Any

from psycopg2.extensions import connection as ConexionPostgres, cursor as CursorPostgres


class ConexionConSavepoint:
    """Adapta una conexión externa para absorber el control transaccional interno."""

    _NOMBRE_SAVEPOINT = "destino3_test_savepoint"

    def __init__(self, conexion: ConexionPostgres) -> None:
        self._conexion = conexion
        self._ejecutar_control(
            f"SAVEPOINT {self._NOMBRE_SAVEPOINT}",
        )

    def cursor(self, *args: Any, **kwargs: Any) -> CursorPostgres:
        """Obtiene un cursor de la conexión externa sin sustituirlo."""
        return self._conexion.cursor(*args, **kwargs)

    def commit(self) -> None:
        """Confirma solo el trabajo interno recreando el savepoint."""
        self._ejecutar_control(
            f"RELEASE SAVEPOINT {self._NOMBRE_SAVEPOINT}",
            f"SAVEPOINT {self._NOMBRE_SAVEPOINT}",
        )

    def rollback(self) -> None:
        """Revierte el trabajo interno y deja disponible el savepoint."""
        self._ejecutar_control(
            f"ROLLBACK TO SAVEPOINT {self._NOMBRE_SAVEPOINT}",
            f"RELEASE SAVEPOINT {self._NOMBRE_SAVEPOINT}",
            f"SAVEPOINT {self._NOMBRE_SAVEPOINT}",
        )

    def close(self) -> None:
        """No cierra la conexión externa administrada por el harness."""
        return None

    def _ejecutar_control(self, *sentencias: str) -> None:
        cursor = self._conexion.cursor()
        try:
            for sentencia in sentencias:
                cursor.execute(sentencia)
        finally:
            cursor.close()

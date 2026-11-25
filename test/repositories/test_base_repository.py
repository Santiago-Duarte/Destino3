import unittest
from unittest.mock import MagicMock, patch

from src.exceptions import PersistenciaError
from src.repositories.base_repository import BaseRepository


class TestBaseRepository(unittest.TestCase):

    @patch("src.repositories.base_repository.obtener_conexion", return_value=None)
    def test_sin_conexion_lanza_persistencia_error(self, _conexion):
        repo = BaseRepository()
        with self.assertRaises(PersistenciaError) as ctx:
            repo._obtener_conexion()

        self.assertEqual(ctx.exception.proveedor, "PostgreSQL")
        self.assertEqual(ctx.exception.operacion, "conexion")

    def test_fallo_al_crear_cursor_cierra_conexion_y_relanza(self):
        conexion = MagicMock()
        conexion.cursor.side_effect = RuntimeError("cursor roto")
        with patch("src.repositories.base_repository.obtener_conexion", return_value=conexion):
            repo = BaseRepository()
            with self.assertRaises(RuntimeError):
                with repo._transaccion():
                    pass

        conexion.close.assert_called_once()

    def test_transaccion_hace_commit_y_cierra_en_exito(self):
        cursor = MagicMock()
        conexion = MagicMock()
        conexion.cursor.return_value = cursor

        with patch("src.repositories.base_repository.obtener_conexion", return_value=conexion):
            repo = BaseRepository()
            with repo._transaccion() as c:
                self.assertIs(c, cursor)

        conexion.commit.assert_called_once()
        cursor.close.assert_called_once()
        conexion.close.assert_called_once()

    def test_transaccion_hace_rollback_y_cierra_en_error(self):
        cursor = MagicMock()
        conexion = MagicMock()
        conexion.cursor.return_value = cursor

        with patch("src.repositories.base_repository.obtener_conexion", return_value=conexion):
            repo = BaseRepository()
            with self.assertRaises(RuntimeError):
                with repo._transaccion():
                    raise RuntimeError("falla en la tx")

        conexion.rollback.assert_called_once()
        cursor.close.assert_called_once()
        conexion.close.assert_called_once()
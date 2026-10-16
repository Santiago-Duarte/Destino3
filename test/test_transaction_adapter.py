import unittest
from unittest.mock import MagicMock, call

from test.transaction_adapter import ConexionConSavepoint


class TestConexionConSavepoint(unittest.TestCase):
    def _crear_adaptador(self):
        conexion = MagicMock()
        cursor = MagicMock()
        conexion.cursor.return_value = cursor
        adaptador = ConexionConSavepoint(conexion)
        cursor.reset_mock()
        return adaptador, conexion, cursor

    def test_crea_el_savepoint_inicial(self):
        conexion = MagicMock()
        cursor = MagicMock()
        conexion.cursor.return_value = cursor

        ConexionConSavepoint(conexion)

        cursor.execute.assert_called_once_with("SAVEPOINT destino3_test_savepoint")
        cursor.close.assert_called_once_with()

    def test_commit_recrea_savepoint_sin_confirmar_conexion_externa(self):
        adaptador, conexion, cursor = self._crear_adaptador()

        adaptador.commit()

        self.assertEqual(
            cursor.execute.call_args_list,
            [
                call("RELEASE SAVEPOINT destino3_test_savepoint"),
                call("SAVEPOINT destino3_test_savepoint"),
            ],
        )
        conexion.commit.assert_not_called()

    def test_rollback_vuelve_al_savepoint_y_lo_recrea(self):
        adaptador, conexion, cursor = self._crear_adaptador()

        adaptador.rollback()

        self.assertEqual(
            cursor.execute.call_args_list,
            [
                call("ROLLBACK TO SAVEPOINT destino3_test_savepoint"),
                call("RELEASE SAVEPOINT destino3_test_savepoint"),
                call("SAVEPOINT destino3_test_savepoint"),
            ],
        )
        conexion.rollback.assert_not_called()

    def test_close_no_cierra_la_conexion_externa(self):
        adaptador, conexion, _ = self._crear_adaptador()

        adaptador.close()

        conexion.close.assert_not_called()

    def test_cursor_delega_en_la_conexion_externa(self):
        adaptador, conexion, cursor = self._crear_adaptador()

        resultado = adaptador.cursor("cursor-nombre")

        self.assertIs(resultado, cursor)
        conexion.cursor.assert_called_with("cursor-nombre")


if __name__ == "__main__":
    unittest.main()

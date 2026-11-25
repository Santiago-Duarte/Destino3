import unittest
from datetime import date

from src.models.busqueda import EspecificacionBusqueda


class TestTieneRequisitos(unittest.TestCase):

    def test_sin_campos_no_tiene_requisitos(self):
        espec = EspecificacionBusqueda()

        self.assertFalse(espec.tiene_requisitos())

    def test_con_presupuesto_o_preferencias_tiene_requisitos(self):
        self.assertTrue(
            EspecificacionBusqueda(presupuesto_max_noche=100).tiene_requisitos()
        )
        self.assertTrue(
            EspecificacionBusqueda(preferencias="cerca del metro").tiene_requisitos()
        )

    def test_preferencias_en_blanco_no_cuenta_como_requisito(self):
        self.assertFalse(
            EspecificacionBusqueda(preferencias="   ").tiene_requisitos()
        )


class TestNoches(unittest.TestCase):

    def test_sin_fechas_no_hay_noches(self):
        espec = EspecificacionBusqueda()

        self.assertIsNone(espec.noches())

    def test_cuenta_las_noches_entre_entrada_y_salida(self):
        espec = EspecificacionBusqueda(
            fecha_entrada=date(2026, 12, 4),
            fecha_salida=date(2026, 12, 6),
        )

        self.assertEqual(espec.noches(), 2)



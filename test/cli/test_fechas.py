import unittest
from datetime import date, timedelta

from src.cli.fechas import (
    MAX_DIAS_ANTELACION,
    MAX_NOCHES,
    error_de_fechas,
    formatear_fecha,
    parsear_fecha,
    proximo_fin_de_semana,
    validar_entrada,
    validar_estancia,
)
from src.models.busqueda import EspecificacionBusqueda

HOY = date(2026, 11, 25)  # miércoles


class TestProximoFinDeSemana(unittest.TestCase):

    def test_desde_un_miercoles_usa_el_viernes_de_esta_semana(self):
        entrada, salida = proximo_fin_de_semana(HOY)

        self.assertEqual(entrada, date(2026, 11, 27))
        self.assertEqual(salida, date(2026, 11, 29))

    def test_desde_un_sabado_usa_el_viernes_siguiente(self):
        sabado = date(2026, 11, 28)
        entrada, salida = proximo_fin_de_semana(sabado)

        self.assertEqual(entrada, date(2026, 12, 4))
        self.assertEqual(salida, date(2026, 12, 6))

    def test_desde_un_domingo_usa_el_viernes_siguiente(self):
        domingo = date(2026, 11, 29)
        entrada, salida = proximo_fin_de_semana(domingo)

        self.assertEqual(entrada, date(2026, 12, 4))
        self.assertEqual(salida, date(2026, 12, 6))

    def test_si_hoy_es_viernes_usa_el_viernes_siguiente(self):
        viernes = date(2026, 11, 27)

        entrada, salida = proximo_fin_de_semana(viernes)

        self.assertEqual(entrada, date(2026, 12, 4))
        self.assertEqual(salida, date(2026, 12, 6))


class TestParsearFecha(unittest.TestCase):

    def test_acepta_dia_y_mes_del_ano_actual(self):
        self.assertEqual(parsear_fecha("12/12", HOY), date(2026, 12, 12))

    def test_dia_y_mes_pasado_usa_el_ano_siguiente(self):
        self.assertEqual(parsear_fecha("12/01", HOY), date(2027, 1, 12))

    def test_acepta_dia_mes_y_ano(self):
        self.assertEqual(parsear_fecha("12/12/2027", HOY), date(2027, 12, 12))

    def test_acepta_formato_iso(self):
        self.assertEqual(parsear_fecha("2027-01-05", HOY), date(2027, 1, 5))

    def test_rechaza_fechas_imposibles_y_texto(self):
        for texto in ("31/02", "abc", "", "   "):
            with self.subTest(texto=texto):
                self.assertIsNone(parsear_fecha(texto, HOY))

    def test_rechaza_el_29_de_febrero_en_ano_no_bisiesto(self):
        self.assertIsNone(parsear_fecha("29/02/2027", HOY))

    def test_29_feb_sin_ano_usa_el_proximo_bisiesto(self):
        """Si hoy no es bisiesto, 29/02 salta al siguiente año bisiesto."""
        hoy_no_bisiesto = date(2026, 1, 1)  # 2026 no es bisiesto
        self.assertEqual(parsear_fecha("29/02", hoy_no_bisiesto), date(2028, 2, 29))

    def test_29_feb_sin_ano_en_ano_bisiesto_usa_este_ano(self):
        """Si hoy es bisiesto y la fecha ya pasó, usa este año."""
        hoy_bisiesto = date(2028, 1, 1)
        self.assertEqual(parsear_fecha("29/02", hoy_bisiesto), date(2028, 2, 29))


class TestValidaciones(unittest.TestCase):

    def test_entrada_en_el_pasado(self):
        self.assertIsNotNone(validar_entrada(HOY - timedelta(days=1), HOY))

    def test_entrada_demasiado_lejana(self):
        lejana = HOY + timedelta(days=MAX_DIAS_ANTELACION + 1)

        self.assertIsNotNone(validar_entrada(lejana, HOY))

    def test_entrada_de_hoy_es_valida(self):
        self.assertIsNone(validar_entrada(HOY, HOY))

    def test_salida_anterior_o_igual_a_la_entrada(self):
        entrada = HOY + timedelta(days=10)

        self.assertIsNotNone(validar_estancia(entrada, entrada))
        self.assertIsNotNone(validar_estancia(entrada, entrada - timedelta(days=1)))

    def test_estancia_demasiado_larga(self):
        entrada = HOY + timedelta(days=10)

        self.assertIsNotNone(
            validar_estancia(entrada, entrada + timedelta(days=MAX_NOCHES + 1))
        )

    def test_estancia_valida(self):
        entrada = HOY + timedelta(days=10)

        self.assertIsNone(validar_estancia(entrada, entrada + timedelta(days=2)))

    def test_error_de_fechas_sin_datos(self):
        espec = EspecificacionBusqueda(ciudad="Medellin", pais="Colombia")

        self.assertIsNotNone(error_de_fechas(espec, HOY))

    def test_error_de_fechas_valido(self):
        entrada = HOY + timedelta(days=10)
        espec = EspecificacionBusqueda(
            ciudad="Medellin",
            pais="Colombia",
            fecha_entrada=entrada,
            fecha_salida=entrada + timedelta(days=2),
        )

        self.assertIsNone(error_de_fechas(espec, HOY))


class TestFormatearFecha(unittest.TestCase):

    def test_incluye_dia_semana_y_dia_mes(self):
        self.assertEqual(formatear_fecha(date(2026, 11, 27)), "vie 27/11")



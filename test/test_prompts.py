import io
import unittest
from contextlib import redirect_stdout
from datetime import date
from unittest.mock import patch

from src.cli.prompts import (
    completar_especificacion,
    confirmar,
    pedir_frase,
    resumen,
)
from src.models.busqueda import EspecificacionBusqueda

HOY = date(2026, 11, 25)  # miércoles


def espec(**cambios) -> EspecificacionBusqueda:
    datos = {
        "ciudad": "Medellin",
        "pais": "Colombia",
        "fecha_entrada": date(2026, 12, 4),
        "fecha_salida": date(2026, 12, 6),
        "adultos": 2,
        "ninos": 0,
        "mascotas": False,
        "presupuesto_max_noche": 100,
        "preferencias": "cerca del metro",
    }
    datos.update(cambios)
    return EspecificacionBusqueda(**datos)


class TestPedirFrase(unittest.TestCase):

    def test_repite_hasta_recibir_texto(self):
        with patch("builtins.input", side_effect=["", "   ", "hoteles en Cali"]):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(pedir_frase(), "hoteles en Cali")

    def test_interrupcion_devuelve_none(self):
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            with redirect_stdout(io.StringIO()):
                self.assertIsNone(pedir_frase())

    def test_fin_de_entrada_devuelve_none(self):
        with patch("builtins.input", side_effect=EOFError):
            with redirect_stdout(io.StringIO()):
                self.assertIsNone(pedir_frase())


class TestCompletarEspecificacion(unittest.TestCase):

    def test_sin_faltantes_no_pregunta_nada(self):
        with patch("builtins.input") as entrada:
            with redirect_stdout(io.StringIO()):
                inferidos = completar_especificacion(espec(), hoy=HOY)

        self.assertFalse(inferidos)
        entrada.assert_not_called()

    def test_pide_fechas_con_default_de_fin_de_semana(self):
        actual = espec(fecha_entrada=None, fecha_salida=None)

        with patch("builtins.input", side_effect=["", ""]):
            with redirect_stdout(io.StringIO()):
                inferidos = completar_especificacion(actual, hoy=HOY)

        self.assertTrue(inferidos)
        self.assertEqual(actual.fecha_entrada, date(2026, 11, 27))
        self.assertEqual(actual.fecha_salida, date(2026, 11, 29))

    def test_acepta_fechas_escritas(self):
        actual = espec(fecha_entrada=None, fecha_salida=None)

        with patch("builtins.input", side_effect=["10/12", "12/12"]):
            with redirect_stdout(io.StringIO()):
                completar_especificacion(actual, hoy=HOY)

        self.assertEqual(actual.fecha_entrada, date(2026, 12, 10))
        self.assertEqual(actual.fecha_salida, date(2026, 12, 12))

    def test_fecha_pasada_muestra_error_y_vuelve_a_preguntar(self):
        actual = espec(fecha_entrada=None, fecha_salida=None)
        salida = io.StringIO()

        with patch("builtins.input", side_effect=["25/11/2025", "10/12", "12/12"]):
            with redirect_stdout(salida):
                completar_especificacion(actual, hoy=HOY)

        self.assertIn("no puede ser anterior a hoy", salida.getvalue())
        self.assertEqual(actual.fecha_entrada, date(2026, 12, 10))

    def test_salida_anterior_a_la_entrada_se_rechaza(self):
        actual = espec(fecha_entrada=None, fecha_salida=None)
        salida = io.StringIO()

        with patch("builtins.input", side_effect=["10/12", "09/12", "12/12"]):
            with redirect_stdout(salida):
                completar_especificacion(actual, hoy=HOY)

        self.assertIn("posterior a la entrada", salida.getvalue())
        self.assertEqual(actual.fecha_salida, date(2026, 12, 12))

    def test_pide_ocupacion_y_mascotas_solo_si_faltan(self):
        actual = espec(adultos=None, ninos=None, mascotas=None)

        with patch("builtins.input", side_effect=["3", "1", "s"]):
            with redirect_stdout(io.StringIO()):
                inferidos = completar_especificacion(actual, hoy=HOY)

        self.assertTrue(inferidos)
        self.assertEqual(actual.adultos, 3)
        self.assertEqual(actual.ninos, 1)
        self.assertTrue(actual.mascotas)

    def test_adultos_fuera_de_rango_se_rechaza(self):
        actual = espec(adultos=None, ninos=None, mascotas=None)
        salida = io.StringIO()

        with patch("builtins.input", side_effect=["0", "4", "", ""]):
            with redirect_stdout(salida):
                completar_especificacion(actual, hoy=HOY)

        self.assertIn("Debe estar entre", salida.getvalue())
        self.assertEqual(actual.adultos, 4)

    def test_interrupcion_devuelve_none(self):
        actual = espec(fecha_entrada=None, fecha_salida=None)

        with patch("builtins.input", side_effect=EOFError):
            with redirect_stdout(io.StringIO()):
                self.assertIsNone(completar_especificacion(actual, hoy=HOY))

    def test_si_solo_falta_una_fecha_la_otra_se_usa_como_default(self):
        actual = espec(fecha_salida=None)

        with patch("builtins.input", side_effect=["", ""]):
            with redirect_stdout(io.StringIO()):
                completar_especificacion(actual, hoy=HOY)

        self.assertEqual(actual.fecha_entrada, date(2026, 12, 4))
        self.assertEqual(actual.fecha_salida, date(2026, 12, 6))


class TestConfirmar(unittest.TestCase):

    def test_enter_y_s_confirman(self):
        for respuesta in ("", "s", "S", "si", "sí"):
            with self.subTest(respuesta=respuesta):
                with patch("builtins.input", return_value=respuesta):
                    with redirect_stdout(io.StringIO()):
                        self.assertTrue(confirmar(espec()))

    def test_n_cancela(self):
        with patch("builtins.input", return_value="n"):
            with redirect_stdout(io.StringIO()):
                self.assertFalse(confirmar(espec()))

    def test_respuesta_invalida_vuelve_a_preguntar(self):
        with patch("builtins.input", side_effect=["quizá", "s"]):
            with redirect_stdout(io.StringIO()):
                self.assertTrue(confirmar(espec()))

    def test_interrupcion_devuelve_none(self):
        with patch("builtins.input", side_effect=EOFError):
            with redirect_stdout(io.StringIO()):
                self.assertIsNone(confirmar(espec()))


class TestResumen(unittest.TestCase):

    def test_incluye_destino_fechas_ocupacion_y_presupuesto(self):
        texto = resumen(espec())

        self.assertIn("Medellin, Colombia", texto)
        self.assertIn("vie 04/12 → dom 06/12 (2 noches)", texto)
        self.assertIn("2 adultos, 0 niños, sin mascotas", texto)
        self.assertIn("hasta USD $100/noche", texto)
        self.assertIn("Preferencias: cerca del metro", texto)

    def test_ocupacion_en_singular(self):
        texto = resumen(espec(adultos=1, ninos=1))

        self.assertIn("1 adulto, 1 niño, sin mascotas", texto)

    def test_sin_presupuesto_ni_preferencias(self):
        texto = resumen(espec(
            presupuesto_max_noche=None,
            preferencias="",
            mascotas=True,
        ))

        self.assertIn("sin límite", texto)
        self.assertIn("con mascotas", texto)
        self.assertNotIn("Preferencias:", texto)

    def test_fechas_sin_definir(self):
        texto = resumen(espec(fecha_entrada=None, fecha_salida=None))

        self.assertIn("fechas sin definir", texto)


if __name__ == "__main__":
    unittest.main()

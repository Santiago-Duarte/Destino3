import io
import unittest
from contextlib import redirect_stdout
from datetime import date
from unittest.mock import patch

from src.cli.prompts import (
    completar_especificacion,
    confirmar,
    formatear_distancia,
    formatear_ocupacion,
    pedir_frase,
    resumen,
)
from src.models.busqueda import EspecificacionBusqueda
from src.models.hospedaje import Hospedaje

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

    def test_fecha_no_valida_muestra_error_y_vuelve_a_preguntar(self):
        actual = espec(fecha_entrada=None, fecha_salida=None)
        salida = io.StringIO()

        with patch("builtins.input", side_effect=["abc", "10/12", "12/12"]):
            with redirect_stdout(salida):
                completar_especificacion(actual, hoy=HOY)

        self.assertIn("Fecha no válida", salida.getvalue())
        self.assertEqual(actual.fecha_entrada, date(2026, 12, 10))
        self.assertEqual(actual.fecha_salida, date(2026, 12, 12))

    def test_interrupcion_durante_las_fechas_devuelve_none(self):
        actual = espec(fecha_entrada=None, fecha_salida=None)

        with patch("builtins.input", side_effect=[EOFError]):
            with redirect_stdout(io.StringIO()):
                self.assertIsNone(completar_especificacion(actual, hoy=HOY))

    def test_interrupcion_durante_la_salida_devuelve_none(self):
        actual = espec(fecha_entrada=None, fecha_salida=None)

        with patch("builtins.input", side_effect=["", EOFError]):
            with redirect_stdout(io.StringIO()):
                self.assertIsNone(completar_especificacion(actual, hoy=HOY))

    def test_interrupcion_durante_los_adultos_devuelve_none(self):
        actual = espec(adultos=None)

        with patch("builtins.input", side_effect=[EOFError]):
            with redirect_stdout(io.StringIO()):
                self.assertIsNone(completar_especificacion(actual, hoy=HOY))

    def test_interrupcion_durante_los_ninos_devuelve_none(self):
        actual = espec(ninos=None)

        with patch("builtins.input", side_effect=[EOFError]):
            with redirect_stdout(io.StringIO()):
                self.assertIsNone(completar_especificacion(actual, hoy=HOY))

    def test_interrupcion_durante_las_mascotas_devuelve_none(self):
        actual = espec(mascotas=None)

        with patch("builtins.input", side_effect=[EOFError]):
            with redirect_stdout(io.StringIO()):
                self.assertIsNone(completar_especificacion(actual, hoy=HOY))

    def test_ocupacion_no_numerica_vuelve_a_preguntar(self):
        actual = espec(adultos=None, ninos=None, mascotas=None)
        salida = io.StringIO()

        with patch("builtins.input", side_effect=["abc", "3", "1", "s"]):
            with redirect_stdout(salida):
                inferidos = completar_especificacion(actual, hoy=HOY)

        self.assertIn("Escribe un número entero.", salida.getvalue())
        self.assertTrue(inferidos)
        self.assertEqual(actual.adultos, 3)
        self.assertEqual(actual.ninos, 1)
        self.assertTrue(actual.mascotas)

    def test_respuesta_de_mascotas_invalida_vuelve_a_preguntar(self):
        actual = espec(mascotas=None)
        salida = io.StringIO()

        with patch("builtins.input", side_effect=["quizá", "n"]):
            with redirect_stdout(salida):
                completar_especificacion(actual, hoy=HOY)

        self.assertIn("Responde 's' o 'n'.", salida.getvalue())
        self.assertFalse(actual.mascotas)

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

    def test_mascotas_desconocidas_no_se_afirman_como_negadas(self):
        texto = resumen(espec(mascotas=None))

        self.assertIn("mascotas no especificadas", texto)
        self.assertNotIn("sin mascotas", texto)
        self.assertIn(
            "mascotas no especificadas",
            formatear_ocupacion(espec(mascotas=None)),
        )

    def test_incluye_la_distancia_maxima_cuando_se_pide(self):
        texto = resumen(espec(max_distancia_km=1.5))

        self.assertIn("Distancia máxima desde", texto)
        self.assertIn("1.5 km", texto)

    def test_sin_distancia_maxima_no_la_menciona(self):
        texto = resumen(espec())

        self.assertNotIn("Distancia máxima", texto)


class TestFormatearDistancia(unittest.TestCase):

    @staticmethod
    def _hospedaje(**campos) -> Hospedaje:
        hospedaje = Hospedaje(
            nombre="Hotel",
            tipo="hotel",
            precio_noche=100,
            calificacion=4.5,
            direccion="Calle 1",
            url_reserva="https://hotel.example",
            destino_id=1,
        )
        for campo, valor in campos.items():
            setattr(hospedaje, campo, valor)
        return hospedaje

    def test_sin_distancia_devuelve_none(self):
        self.assertIsNone(formatear_distancia(self._hospedaje()))

    def test_incluye_distancia_y_todos_los_tiempos(self):
        hospedaje = self._hospedaje(
            distancia_km=1.25,
            tiempo_auto_min=3,
            tiempo_transit_min=4,
            tiempo_walking_min=15,
        )

        texto = formatear_distancia(hospedaje, "centro")

        self.assertEqual(
            texto,
            "1.25 km de centro | auto 3 min | bus 4 min | a pie 15 min",
        )

    def test_omite_los_tiempos_no_disponibles(self):
        hospedaje = self._hospedaje(distancia_km=0.5, tiempo_auto_min=1)

        self.assertEqual(
            formatear_distancia(hospedaje, "centro"),
            "0.50 km de centro | auto 1 min",
        )



import io
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta
from unittest.mock import patch

from src.cli.fechas import proximo_fin_de_semana
from src.exceptions import SerpApiError
from src.main import main
from src.models.analisis import Analisis
from src.models.busqueda import EspecificacionBusqueda
from src.models.hospedaje import Hospedaje
from src.orchestrator.orquestador_integracion import (
    Candidato,
    ResultadoBusqueda,
    rankear_candidatos,
)

FRASE = "quiero hoteles en Medellin hasta 100 USD cerca del metro"


def espec_completa(**cambios) -> EspecificacionBusqueda:
    entrada = date.today() + timedelta(days=10)
    datos = {
        "ciudad": "Medellin",
        "pais": "Colombia",
        "fecha_entrada": entrada,
        "fecha_salida": entrada + timedelta(days=2),
        "adultos": 2,
        "ninos": 0,
        "mascotas": False,
        "presupuesto_max_noche": 100,
        "preferencias": "cerca del metro",
    }
    datos.update(cambios)
    return EspecificacionBusqueda(**datos)


def resultado_de_prueba(
        espec: EspecificacionBusqueda | None = None,
) -> ResultadoBusqueda:
    espec = espec or espec_completa()
    candidatos = [
        Candidato(
            hospedaje=Hospedaje(
                id=posicion,
                nombre=nombre,
                tipo="hotel",
                precio_noche=precio,
                calificacion=4.5,
                direccion="Calle 1",
                url_reserva="https://hotel.example",
                destino_id=1,
            ),
            analisis=Analisis(
                resumen_ejecutivo=f"Resumen de {nombre}",
                puntos_fuertes="Cerca del metro",
                puntos_debiles="Pocas amenidades",
                hospedaje_id=posicion,
            ),
            score_calidad=8,
            score_cumplimiento=cumplimiento,
            requisitos_cumplidos=["presupuesto hasta 100 USD", "cerca del metro"],
            requisitos_faltantes=[],
        )
        for posicion, (nombre, precio, cumplimiento) in enumerate(
            [("Hotel A", 50, 10), ("Hotel B", 60, 8), ("Hotel C", 70, 6)], start=1
        )
    ]
    return ResultadoBusqueda(espec, rankear_candidatos(candidatos))


def resultado_sin_puntajes() -> ResultadoBusqueda:
    resultado = resultado_de_prueba()
    for candidato in resultado.candidatos:
        candidato.score_calidad = None
        candidato.score_cumplimiento = None
    return resultado


def resultado_sin_requisitos_cumplidos() -> ResultadoBusqueda:
    resultado = resultado_de_prueba()
    for candidato in resultado.candidatos:
        candidato.score_calidad = 5
        candidato.score_cumplimiento = 5
        candidato.requisitos_cumplidos = []
        candidato.requisitos_faltantes = ["cerca del metro"]
    return resultado


class TestMain(unittest.TestCase):

    def setUp(self):
        self.espec = espec_completa()

        self.patch_input = patch("builtins.input", return_value=FRASE)
        self.input_mock = self.patch_input.start()
        self.addCleanup(self.patch_input.stop)

        self.patch_interpretador = patch(
            "src.services.interpretador_ia.InterpretadorIA"
        )
        self.interpretador = self.patch_interpretador.start()
        self.addCleanup(self.patch_interpretador.stop)
        self.interpretador.return_value.interpretar.return_value = self.espec

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_imprime_el_top_y_devuelve_cero(self, orquestador):
        orquestador.return_value.buscar.return_value = resultado_de_prueba(self.espec)
        salida = io.StringIO()

        with redirect_stdout(salida):
            codigo = main([])

        self.assertEqual(codigo, 0)
        texto = salida.getvalue()
        self.assertIn("Medellin, Colombia", texto)
        self.assertIn("TOP 3 de 3 candidatos", texto)
        self.assertIn("1. Hotel A", texto)
        self.assertIn("Cumplimiento 10/10", texto)
        self.assertIn("Fuertes: Cerca del metro", texto)
        self.assertIn("Reserva: https://hotel.example", texto)
        orquestador.return_value.buscar.assert_called_once_with(self.espec)

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_frase_sin_ciudad_devuelve_uno(self, orquestador):
        self.interpretador.return_value.interpretar.side_effect = ValueError(
            "La frase no indica la ciudad o el país de la búsqueda."
        )

        with redirect_stdout(io.StringIO()):
            codigo = main([])

        self.assertEqual(codigo, 1)
        orquestador.return_value.buscar.assert_not_called()

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_fallo_del_proveedor_devuelve_uno(self, orquestador):
        orquestador.return_value.buscar.side_effect = SerpApiError(
            "consulta", "sin conexión"
        )

        with redirect_stdout(io.StringIO()):
            codigo = main([])

        self.assertEqual(codigo, 1)

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_fallo_inesperado_devuelve_uno(self, orquestador):
        orquestador.return_value.buscar.side_effect = RuntimeError("caos")

        with redirect_stdout(io.StringIO()):
            codigo = main([])

        self.assertEqual(codigo, 1)

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_imprime_un_aviso_si_no_hay_hoteles(self, orquestador):
        orquestador.return_value.buscar.return_value = ResultadoBusqueda(
            self.espec, []
        )
        salida = io.StringIO()

        with redirect_stdout(salida):
            codigo = main([])

        self.assertEqual(codigo, 0)
        self.assertIn("No se encontraron hoteles", salida.getvalue())

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_avisa_cuando_la_ia_no_pudo_puntuar(self, orquestador):
        orquestador.return_value.buscar.return_value = resultado_sin_puntajes()
        salida = io.StringIO()

        with redirect_stdout(salida):
            codigo = main([])

        texto = salida.getvalue()
        self.assertEqual(codigo, 0)
        self.assertIn("La IA no pudo puntuar", texto)
        self.assertIn("1. Hotel A", texto)
        self.assertIn("Sin puntaje", texto)
        self.assertNotIn("Ningún hotel cumple", texto)

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_avisa_cuando_ninguno_cumple_los_requisitos(self, orquestador):
        orquestador.return_value.buscar.return_value = (
            resultado_sin_requisitos_cumplidos()
        )
        salida = io.StringIO()

        with redirect_stdout(salida):
            codigo = main([])

        texto = salida.getvalue()
        self.assertEqual(codigo, 0)
        self.assertIn("Ningún hotel cumple", texto)
        self.assertIn("Falta: cerca del metro", texto)

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_pide_la_frase_por_consola_y_busca_con_la_especificacion(
            self, orquestador
    ):
        orquestador.return_value.buscar.return_value = resultado_de_prueba(self.espec)

        with redirect_stdout(io.StringIO()):
            codigo = main([])

        self.assertEqual(codigo, 0)
        self.input_mock.assert_called_once()
        self.interpretador.return_value.interpretar.assert_called_once_with(FRASE)
        orquestador.return_value.buscar.assert_called_once_with(self.espec)

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_no_pide_confirmacion_si_la_frase_trae_todo(self, orquestador):
        orquestador.return_value.buscar.return_value = resultado_de_prueba(self.espec)
        salida = io.StringIO()

        with redirect_stdout(salida):
            codigo = main([])

        self.assertEqual(codigo, 0)
        self.assertNotIn("¿Buscar con estos datos?", salida.getvalue())

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_vuelve_a_preguntar_si_la_frase_esta_vacia(self, orquestador):
        self.input_mock.side_effect = ["", "   ", FRASE]
        orquestador.return_value.buscar.return_value = resultado_de_prueba(self.espec)

        with redirect_stdout(io.StringIO()):
            codigo = main([])

        self.assertEqual(codigo, 0)
        self.assertEqual(self.input_mock.call_count, 3)
        orquestador.return_value.buscar.assert_called_once_with(self.espec)

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_pide_fechas_con_default_si_la_frase_no_las_trae(self, orquestador):
        self.espec = espec_completa(fecha_entrada=None, fecha_salida=None)
        self.interpretador.return_value.interpretar.return_value = self.espec
        orquestador.return_value.buscar.return_value = resultado_de_prueba(self.espec)
        self.input_mock.side_effect = [FRASE, "", "", "s"]

        with redirect_stdout(io.StringIO()):
            codigo = main([])

        entrada, salida = proximo_fin_de_semana(date.today())
        self.assertEqual(codigo, 0)
        self.assertEqual(self.espec.fecha_entrada, entrada)
        self.assertEqual(self.espec.fecha_salida, salida)
        self.assertEqual(self.input_mock.call_count, 4)
        orquestador.return_value.buscar.assert_called_once_with(self.espec)

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_fechas_pasadas_se_vuelven_a_pedir(self, orquestador):
        hoy = date.today()
        self.espec = espec_completa(
            fecha_entrada=hoy - timedelta(days=30),
            fecha_salida=hoy - timedelta(days=28),
        )
        self.interpretador.return_value.interpretar.return_value = self.espec
        orquestador.return_value.buscar.return_value = resultado_de_prueba(self.espec)

        entrada = hoy + timedelta(days=10)
        salida = entrada + timedelta(days=2)
        self.input_mock.side_effect = [
            FRASE,
            entrada.strftime("%d/%m"),
            salida.strftime("%d/%m"),
            "s",
        ]
        salida_consola = io.StringIO()

        with redirect_stdout(salida_consola):
            codigo = main([])

        self.assertEqual(codigo, 0)
        self.assertIn("no puede ser anterior a hoy", salida_consola.getvalue())
        self.assertEqual(self.espec.fecha_entrada, entrada)
        self.assertEqual(self.espec.fecha_salida, salida)

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_pide_ocupacion_si_la_frase_no_la_trae(self, orquestador):
        self.espec = espec_completa(adultos=None, ninos=None, mascotas=None)
        self.interpretador.return_value.interpretar.return_value = self.espec
        orquestador.return_value.buscar.return_value = resultado_de_prueba(self.espec)
        self.input_mock.side_effect = [FRASE, "3", "1", "s", "s"]

        with redirect_stdout(io.StringIO()):
            codigo = main([])

        self.assertEqual(codigo, 0)
        self.assertEqual(self.espec.adultos, 3)
        self.assertEqual(self.espec.ninos, 1)
        self.assertTrue(self.espec.mascotas)
        self.assertEqual(self.input_mock.call_count, 5)

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_cancelar_la_confirmacion_no_busca(self, orquestador):
        self.espec = espec_completa(mascotas=None)
        self.interpretador.return_value.interpretar.return_value = self.espec
        self.input_mock.side_effect = [FRASE, "", "n"]
        salida = io.StringIO()

        with redirect_stdout(salida):
            codigo = main([])

        self.assertEqual(codigo, 0)
        self.assertIn("Búsqueda cancelada", salida.getvalue())
        orquestador.return_value.buscar.assert_not_called()

    def test_entrada_interrumpida_devuelve_uno(self):
        self.input_mock.side_effect = KeyboardInterrupt

        salida = io.StringIO()
        with redirect_stdout(salida):
            codigo = main([])

        self.assertEqual(codigo, 1)
        self.assertIn("No se recibió ninguna frase", salida.getvalue())

    def test_fin_de_entrada_sin_frase_devuelve_uno(self):
        self.input_mock.side_effect = EOFError

        with redirect_stdout(io.StringIO()):
            codigo = main([])

        self.assertEqual(codigo, 1)

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_fin_de_entrada_al_confirmar_devuelve_uno(self, orquestador):
        self.espec = espec_completa(mascotas=None)
        self.interpretador.return_value.interpretar.return_value = self.espec
        self.input_mock.side_effect = [FRASE, "", EOFError]

        with redirect_stdout(io.StringIO()):
            codigo = main([])

        self.assertEqual(codigo, 1)
        orquestador.return_value.buscar.assert_not_called()

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_fin_de_entrada_al_completar_especificacion_devuelve_uno(self, orquestador):
        """EOF al pedir ocupación durante completar_especificacion."""
        self.espec = espec_completa(adultos=None)
        self.interpretador.return_value.interpretar.return_value = self.espec
        self.input_mock.side_effect = [FRASE, "", EOFError]

        with redirect_stdout(io.StringIO()):
            codigo = main([])

        self.assertEqual(codigo, 1)
        orquestador.return_value.buscar.assert_not_called()

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_imprime_hotel_sin_precio_ni_calificacion_ni_fechas(self, orquestador):
        """Resultado con hospedaje sin precio, calificación y búsqueda sin fechas."""
        self.espec = EspecificacionBusqueda(ciudad="Medellin", pais="Colombia")
        candidatos = [
            Candidato(
                hospedaje=Hospedaje(
                    id=1,
                    nombre="Hotel Sin Datos",
                    tipo="hotel",
                    precio_noche=None,
                    calificacion=None,
                    direccion="Calle 1",
                    url_reserva="https://hotel.example",
                    destino_id=1,
                ),
                analisis=Analisis(
                    resumen_ejecutivo="Resumen",
                    puntos_fuertes="F",
                    puntos_debiles="D",
                    hospedaje_id=1,
                ),
                score_calidad=5,
                score_cumplimiento=5,
                requisitos_cumplidos=[],
                requisitos_faltantes=[],
            )
        ]
        from src.orchestrator.orquestador_integracion import rankear_candidatos
        resultado = ResultadoBusqueda(self.espec, rankear_candidatos(candidatos))
        orquestador.return_value.buscar.return_value = resultado
        salida = io.StringIO()

        with redirect_stdout(salida):
            codigo = main([])

        self.assertEqual(codigo, 0)
        texto = salida.getvalue()
        self.assertIn("Hotel Sin Datos", texto)
        self.assertIn("precio no disponible", texto)
        self.assertIn("sin calificación", texto)
        self.assertIn("fechas sin definir", texto)



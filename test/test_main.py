import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

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


def resultado_de_prueba() -> ResultadoBusqueda:
    espec = EspecificacionBusqueda(
        ciudad="Medellin",
        pais="Colombia",
        presupuesto_max_noche=100,
        preferencias="cerca del metro",
    )
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
        self.patch_input = patch("builtins.input", return_value=FRASE)
        self.input_mock = self.patch_input.start()
        self.addCleanup(self.patch_input.stop)

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_imprime_el_top_y_devuelve_cero(self, orquestador):
        orquestador.return_value.buscar_desde_frase.return_value = resultado_de_prueba()
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
        orquestador.return_value.buscar_desde_frase.assert_called_once_with(FRASE)

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_frase_sin_ciudad_devuelve_uno(self, orquestador):
        orquestador.return_value.buscar_desde_frase.side_effect = ValueError(
            "La frase no indica la ciudad o el país de la búsqueda."
        )

        with redirect_stdout(io.StringIO()):
            codigo = main([])

        self.assertEqual(codigo, 1)

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_fallo_del_proveedor_devuelve_uno(self, orquestador):
        orquestador.return_value.buscar_desde_frase.side_effect = SerpApiError(
            "consulta", "sin conexión"
        )

        with redirect_stdout(io.StringIO()):
            codigo = main([])

        self.assertEqual(codigo, 1)

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_fallo_inesperado_devuelve_uno(self, orquestador):
        orquestador.return_value.buscar_desde_frase.side_effect = RuntimeError("caos")

        with redirect_stdout(io.StringIO()):
            codigo = main([])

        self.assertEqual(codigo, 1)

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_imprime_un_aviso_si_no_hay_hoteles(self, orquestador):
        espec = EspecificacionBusqueda(ciudad="Medellin", pais="Colombia")
        orquestador.return_value.buscar_desde_frase.return_value = ResultadoBusqueda(espec, [])
        salida = io.StringIO()

        with redirect_stdout(salida):
            codigo = main([])

        self.assertEqual(codigo, 0)
        self.assertIn("No se encontraron hoteles", salida.getvalue())

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_avisa_cuando_la_ia_no_pudo_puntuar(self, orquestador):
        orquestador.return_value.buscar_desde_frase.return_value = resultado_sin_puntajes()
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
        orquestador.return_value.buscar_desde_frase.return_value = (
            resultado_sin_requisitos_cumplidos()
        )
        salida = io.StringIO()

        with redirect_stdout(salida):
            codigo = main([])

        texto = salida.getvalue()
        self.assertEqual(codigo, 0)
        self.assertIn("Ningún hotel cumple", texto)
        self.assertIn("Falta: cerca del metro", texto)

    def test_pide_la_frase_por_consola_y_la_envia_al_orquestador(self):
        with patch(
            "src.orchestrator.orquestador_integracion.OrquestadorIntegracion"
        ) as orquestador:
            orquestador.return_value.buscar_desde_frase.return_value = (
                resultado_de_prueba()
            )

            with redirect_stdout(io.StringIO()):
                codigo = main([])

        self.assertEqual(codigo, 0)
        self.input_mock.assert_called_once()
        orquestador.return_value.buscar_desde_frase.assert_called_once_with(FRASE)

    @patch("src.orchestrator.orquestador_integracion.OrquestadorIntegracion")
    def test_vuelve_a_preguntar_si_la_frase_esta_vacia(self, orquestador):
        self.input_mock.side_effect = ["", "   ", FRASE]
        orquestador.return_value.buscar_desde_frase.return_value = resultado_de_prueba()

        with redirect_stdout(io.StringIO()):
            codigo = main([])

        self.assertEqual(codigo, 0)
        self.assertEqual(self.input_mock.call_count, 3)
        orquestador.return_value.buscar_desde_frase.assert_called_once_with(FRASE)

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


if __name__ == "__main__":
    unittest.main()

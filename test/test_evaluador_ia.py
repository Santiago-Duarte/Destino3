import unittest
from unittest.mock import patch

from src.exceptions.evaluacion_ia import EvaluacionIALoteError
from src.models.hospedaje import Hospedaje
from src.services.evaluador_ia import EvaluadorIA, seleccionar_candidatos


def crear_hospedaje(nombre, precio_noche, calificacion):
    return Hospedaje(
        nombre=nombre,
        tipo="hotel",
        precio_noche=precio_noche,
        calificacion=calificacion,
        direccion="Calle 1",
        url_reserva="https://hotel.example",
        destino_id=1,
    )


class TestSeleccionarCandidatos(unittest.TestCase):

    def test_seleccionar_candidatos_con_lista_vacia(self):
        resultado = seleccionar_candidatos([], 100)
        self.assertEqual(resultado, [])

    def test_todos_los_hospedajes_en_el_presupuesto(self):
        hospedajes = [crear_hospedaje(f"h{i}", 10, 4.0) for i in range(5)]

        resultado = seleccionar_candidatos(hospedajes, 30)
        self.assertEqual(len(resultado), 5)

    def test_hospedajes_fuera_presupuesto(self):
        hospedajes = [crear_hospedaje(f"h{i}", 50, 4.0) for i in range(5)]

        resultado = seleccionar_candidatos(hospedajes, 30)
        self.assertEqual(resultado, [])

    def test_menos_de_5_hospedajes(self):
        hospedajes = [crear_hospedaje(f"h{i}", 10, 4.0) for i in range(3)]

        resultado = seleccionar_candidatos(hospedajes, 30)
        self.assertEqual(len(resultado), 3)

    def test_mas_de_5_hospedajes_devuelve_solo_los_5_mejores(self):
        hospedajes = [
            crear_hospedaje("h6", 10, 0.5),
            crear_hospedaje("h5", 10, 1.0),
            crear_hospedaje("h4", 10, 2.0),
            crear_hospedaje("h3", 10, 3.0),
            crear_hospedaje("h2", 10, 4.0),
            crear_hospedaje("h1", 10, 5.0),
        ]

        resultado = seleccionar_candidatos(hospedajes, 30)

        self.assertEqual(len(resultado), 5)
        nombres = [h.nombre for h in resultado]
        self.assertNotIn("h6", nombres)
        self.assertEqual(resultado[0].nombre, "h1")

    def test_orden_por_calificacion_descendente(self):
        hospedajes = [
            crear_hospedaje("h1", 20, 4.5),
            crear_hospedaje("h2", 15, 5.0),
            crear_hospedaje("h3", 10, 3.0),
            crear_hospedaje("h4", 25, 4.5),
            crear_hospedaje("h5", 12, 5.0),
        ]

        resultado = seleccionar_candidatos(hospedajes, 30)

        nombres = [h.nombre for h in resultado]
        self.assertEqual(nombres, ["h5", "h2", "h1", "h4", "h3"])

    def test_desempate_por_precio_ascendente(self):
        hospedajes = [
            crear_hospedaje("h1", 30, 5.0),
            crear_hospedaje("h2", 10, 5.0),
            crear_hospedaje("h3", 20, 5.0),
            crear_hospedaje("h4", 25, 5.0),
            crear_hospedaje("h5", 15, 5.0),
        ]

        resultado = seleccionar_candidatos(hospedajes, 30)

        precios = [h.precio_noche for h in resultado]
        self.assertEqual(precios, [10, 15, 20, 25, 30])

    def test_filtra_hospedajes_con_precio_none(self):
        hospedajes = [
            crear_hospedaje("h1", 10, 5.0),
            crear_hospedaje("h2", None, 5.0),
            crear_hospedaje("h3", 20, 4.0),
        ]

        resultado = seleccionar_candidatos(hospedajes, 30)

        nombres = [h.nombre for h in resultado]
        self.assertEqual(nombres, ["h1", "h3"])

    def test_calificacion_none_se_trata_como_cero(self):
        hospedajes = [
            crear_hospedaje("h1", 10, 5.0),
            crear_hospedaje("h2", 10, None),
            crear_hospedaje("h3", 10, 4.0),
        ]

        resultado = seleccionar_candidatos(hospedajes, 30)

        nombres = [h.nombre for h in resultado]
        self.assertEqual(nombres, ["h1", "h3", "h2"])

    def test_precio_igual_al_presupuesto_se_incluye(self):
        hospedajes = [crear_hospedaje("h1", 30, 4.0)]

        resultado = seleccionar_candidatos(hospedajes, 30)

        self.assertEqual(len(resultado), 1)


class TestReintentosEvaluadorIA(unittest.TestCase):

    def setUp(self):
        self.hospedajes = [crear_hospedaje("Hotel A", 50, 4.5)]
        self.respuesta_valida = (
            '{"evaluaciones": [{"id_temporal": 1, '
            '"resumen_ejecutivo": "Bueno", "puntos_fuertes": "Ubicación", '
            '"puntos_debiles": "Precio", "score_calidad_precio": 8}]}'
        )

    @patch("time.sleep")
    @patch("src.services.evaluador_ia.settings.GEMINI_BACKOFF_BASE", 0.5)
    @patch("src.services.evaluador_ia.settings.GEMINI_MAX_REINTENTOS", 2)
    @patch("src.services.evaluador_ia.settings.GEMINI_API_KEY", "clave-prueba")
    @patch("src.services.evaluador_ia.genai.Client")
    def test_falla_dos_veces_y_luego_devuelve_lote_valido(
            self, cliente_mock, sleep_mock
    ):
        respuesta = unittest.mock.Mock(text=self.respuesta_valida)
        generar = cliente_mock.return_value.models.generate_content
        generar.side_effect = [TimeoutError("timeout"), RuntimeError("temporal"), respuesta]

        resultado = EvaluadorIA().evaluar_lote(self.hospedajes, 100, "")

        self.assertIsNotNone(resultado)
        self.assertEqual(generar.call_count, 3)
        self.assertEqual(sleep_mock.call_args_list[0].args, (0.5,))
        self.assertEqual(sleep_mock.call_args_list[1].args, (1.0,))

    @patch("time.sleep")
    @patch("src.services.evaluador_ia.settings.GEMINI_MAX_REINTENTOS", 2)
    @patch("src.services.evaluador_ia.settings.GEMINI_API_KEY", "clave-prueba")
    @patch("src.services.evaluador_ia.genai.Client")
    def test_respuesta_invalida_agota_reintentos_y_lanza_error_de_lote(
            self, cliente_mock, sleep_mock
    ):
        respuesta_invalida = unittest.mock.Mock(text='{"resultado": "invalido"}')
        generar = cliente_mock.return_value.models.generate_content
        generar.return_value = respuesta_invalida

        with self.assertRaises(EvaluacionIALoteError) as contexto:
            EvaluadorIA().evaluar_lote(self.hospedajes, 100, "")

        self.assertIn("agotó los reintentos", str(contexto.exception))
        self.assertEqual(contexto.exception.proveedor, "Gemini")
        self.assertEqual(contexto.exception.operacion, "evaluar_lote")
        self.assertEqual(generar.call_count, 3)
        self.assertEqual(sleep_mock.call_count, 2)


if __name__ == "__main__":
    unittest.main()

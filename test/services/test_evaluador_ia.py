import unittest
from pathlib import Path
from unittest.mock import patch

from src.exceptions.LoteIAError import LoteIAError
from src.models.analisis import Analisis
from src.models.busqueda import EspecificacionBusqueda
from src.models.hospedaje import Hospedaje
from src.services.evaluador_ia import EvaluadorIA, preseleccionar_candidatos

RUTA_FIXTURES = Path(__file__).parent.parent / "fixtures"


def leer_fixture(nombre: str) -> str:
    return (RUTA_FIXTURES / nombre).read_text(encoding="utf-8")


def crear_hospedaje(nombre, precio_noche, calificacion, id=None):
    return Hospedaje(
        id=id,
        nombre=nombre,
        tipo="hotel",
        precio_noche=precio_noche,
        calificacion=calificacion,
        direccion="Calle 1",
        url_reserva="https://hotel.example",
        destino_id=1,
    )


def candidatos():
    return [
        crear_hospedaje("Hotel A", 50, 4.5, id=1),
        crear_hospedaje("Hotel B", 60, 4.0, id=2),
        crear_hospedaje("Hotel C", 70, 3.5, id=3),
    ]


class TestPreseleccionarCandidatos(unittest.TestCase):

    def test_preseleccionar_candidatos_con_lista_vacia(self):
        resultado = preseleccionar_candidatos([], 100)
        self.assertEqual(resultado, [])

    def test_todos_los_hospedajes_en_el_presupuesto(self):
        hospedajes = [crear_hospedaje(f"h{i}", 10, 4.0) for i in range(5)]

        resultado = preseleccionar_candidatos(hospedajes, 30)
        self.assertEqual(len(resultado), 5)

    def test_hospedajes_fuera_presupuesto(self):
        hospedajes = [crear_hospedaje(f"h{i}", 50, 4.0) for i in range(5)]

        resultado = preseleccionar_candidatos(hospedajes, 30)
        self.assertEqual(resultado, [])

    def test_menos_de_5_hospedajes(self):
        hospedajes = [crear_hospedaje(f"h{i}", 10, 4.0) for i in range(3)]

        resultado = preseleccionar_candidatos(hospedajes, 30)
        self.assertEqual(len(resultado), 3)

    def test_devuelve_como_maximo_diez_hospedajes(self):
        hospedajes = [crear_hospedaje(f"h{i}", 10, float(i)) for i in range(12)]

        resultado = preseleccionar_candidatos(hospedajes, 30)

        self.assertEqual(len(resultado), 10)
        self.assertEqual(resultado[0].nombre, "h11")
        nombres = [h.nombre for h in resultado]
        self.assertNotIn("h0", nombres)
        self.assertNotIn("h1", nombres)

    def test_orden_por_calificacion_descendente(self):
        hospedajes = [
            crear_hospedaje("h1", 20, 4.5),
            crear_hospedaje("h2", 15, 5.0),
            crear_hospedaje("h3", 10, 3.0),
            crear_hospedaje("h4", 25, 4.5),
            crear_hospedaje("h5", 12, 5.0),
        ]

        resultado = preseleccionar_candidatos(hospedajes, 30)

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

        resultado = preseleccionar_candidatos(hospedajes, 30)

        precios = [h.precio_noche for h in resultado]
        self.assertEqual(precios, [10, 15, 20, 25, 30])

    def test_filtra_hospedajes_con_precio_none(self):
        hospedajes = [
            crear_hospedaje("h1", 10, 5.0),
            crear_hospedaje("h2", None, 5.0),
            crear_hospedaje("h3", 20, 4.0),
        ]

        resultado = preseleccionar_candidatos(hospedajes, 30)

        nombres = [h.nombre for h in resultado]
        self.assertEqual(nombres, ["h1", "h3"])

    def test_sin_presupuesto_conserva_hoteles_sin_precio_al_final(self):
        hospedajes = [
            crear_hospedaje("sin-precio", None, 5.0),
            crear_hospedaje("caro", 500, 4.0),
            crear_hospedaje("barato", 50, 4.5),
        ]

        resultado = preseleccionar_candidatos(hospedajes, None)

        self.assertEqual(
            [h.nombre for h in resultado],
            ["sin-precio", "barato", "caro"],
        )

    def test_calificacion_none_se_trata_como_cero(self):
        hospedajes = [
            crear_hospedaje("h1", 10, 5.0),
            crear_hospedaje("h2", 10, None),
            crear_hospedaje("h3", 10, 4.0),
        ]

        resultado = preseleccionar_candidatos(hospedajes, 30)

        nombres = [h.nombre for h in resultado]
        self.assertEqual(nombres, ["h1", "h3", "h2"])

    def test_precio_igual_al_presupuesto_se_incluye(self):
        hospedajes = [crear_hospedaje("h1", 30, 4.0)]

        resultado = preseleccionar_candidatos(hospedajes, 30)

        self.assertEqual(len(resultado), 1)


class TestAnalizar(unittest.TestCase):

    @patch("time.sleep")
    @patch("src.services.gemini.settings.GEMINI_BACKOFF_BASE", 0.5)
    @patch("src.services.gemini.settings.GEMINI_MAX_REINTENTOS", 2)
    @patch("src.services.gemini.settings.GEMINI_API_KEY", "clave-prueba")
    @patch("src.services.gemini.genai.Client")
    def test_respuesta_valida_se_analiza_en_una_sola_llamada(self, cliente_mock, _sleep):
        generar = cliente_mock.return_value.models.generate_content
        generar.return_value = unittest.mock.Mock(text=leer_fixture("gemini_analisis_valida.json"))

        lote = EvaluadorIA().analizar(candidatos())

        self.assertEqual(len(lote), 3)
        self.assertEqual(generar.call_count, 1)
        prompt = generar.call_args.kwargs["contents"]
        for id_enviado in (1, 2, 3):
            self.assertIn(f'"hospedaje_id":{id_enviado}', prompt)
        self.assertNotIn("precio_noche", prompt)
        self.assertNotIn('"calificacion"', prompt)

    @patch("time.sleep")
    @patch("src.services.gemini.settings.GEMINI_BACKOFF_BASE", 0.5)
    @patch("src.services.gemini.settings.GEMINI_MAX_REINTENTOS", 2)
    @patch("src.services.gemini.settings.GEMINI_API_KEY", "clave-prueba")
    @patch("src.services.gemini.genai.Client")
    def test_falla_dos_veces_y_luego_devuelve_lote_valido(self, cliente_mock, sleep_mock):
        respuesta = unittest.mock.Mock(text=leer_fixture("gemini_analisis_valida.json"))
        generar = cliente_mock.return_value.models.generate_content
        generar.side_effect = [TimeoutError("timeout"), RuntimeError("temporal"), respuesta]

        lote = EvaluadorIA().analizar(candidatos())

        self.assertEqual(len(lote), 3)
        self.assertEqual(generar.call_count, 3)
        self.assertEqual(sleep_mock.call_args_list[0].args, (0.5,))
        self.assertEqual(sleep_mock.call_args_list[1].args, (1.0,))

    @patch("time.sleep")
    @patch("src.services.gemini.settings.GEMINI_MAX_REINTENTOS", 2)
    @patch("src.services.gemini.settings.GEMINI_API_KEY", "clave-prueba")
    @patch("src.services.gemini.genai.Client")
    def test_respuesta_invalida_agota_reintentos_y_lanza_error(self, cliente_mock, sleep_mock):
        respuesta_invalida = unittest.mock.Mock(
            text=leer_fixture("gemini_analisis_invalida.json")
        )
        generar = cliente_mock.return_value.models.generate_content
        generar.return_value = respuesta_invalida

        with self.assertRaises(LoteIAError) as contexto:
            EvaluadorIA().analizar(candidatos())

        self.assertIn("agotó los reintentos", str(contexto.exception))
        self.assertEqual(contexto.exception.proveedor, "Gemini")
        self.assertEqual(contexto.exception.operacion, "analizar")
        self.assertEqual(generar.call_count, 3)
        self.assertEqual(sleep_mock.call_count, 2)

    @patch("time.sleep")
    @patch("src.services.gemini.settings.GEMINI_MAX_REINTENTOS", 1)
    @patch("src.services.gemini.settings.GEMINI_API_KEY", "clave-prueba")
    @patch("src.services.gemini.genai.Client")
    def test_respuesta_parcial_devuelve_lo_obtenido(self, cliente_mock, _sleep):
        parcial = unittest.mock.Mock(text="""
            {"analisis": [
                {"hospedaje_id": 1, "resumen_ejecutivo": "A",
                 "puntos_fuertes": "F", "puntos_debiles": "D"},
                {"hospedaje_id": 2, "resumen_ejecutivo": "B",
                 "puntos_fuertes": "F", "puntos_debiles": "D"}
            ]}
        """)
        generar = cliente_mock.return_value.models.generate_content
        generar.return_value = parcial

        lote = EvaluadorIA().analizar(candidatos())

        self.assertEqual(len(lote), 2)
        self.assertEqual(generar.call_count, 2)


class TestPuntuar(unittest.TestCase):

    def _espec(self):
        return EspecificacionBusqueda(
            ciudad="Medellin",
            pais="Colombia",
            presupuesto_max_noche=100,
            preferencias="cerca del metro",
        )

    @patch("time.sleep")
    @patch("src.services.gemini.settings.GEMINI_API_KEY", "clave-prueba")
    @patch("src.services.gemini.genai.Client")
    def test_respuesta_valida_devuelve_doble_score_por_candidato(self, cliente_mock, _sleep):
        generar = cliente_mock.return_value.models.generate_content
        generar.return_value = unittest.mock.Mock(
            text=leer_fixture("gemini_puntuacion_valida.json")
        )

        lote = EvaluadorIA().puntuar(candidatos(), {}, self._espec())

        self.assertEqual(len(lote), 3)
        self.assertEqual(lote.hospedaje_ids(), {1, 2, 3})
        self.assertEqual(lote.puntuaciones[0].score_cumplimiento, 10)
        self.assertEqual(lote.puntuaciones[0].score_calidad, 9)

    @patch("time.sleep")
    @patch("src.services.gemini.settings.GEMINI_API_KEY", "clave-prueba")
    @patch("src.services.gemini.genai.Client")
    def test_el_prompt_lleva_las_especificaciones_y_el_analisis_previo(self, cliente_mock, _sleep):
        generar = cliente_mock.return_value.models.generate_content
        generar.return_value = unittest.mock.Mock(
            text=leer_fixture("gemini_puntuacion_valida.json")
        )
        analisis_previo = {1: Analisis(
            resumen_ejecutivo="Hotel a dos cuadras del metro",
            puntos_fuertes="Metro a 200 m",
            puntos_debiles="Pocas amenidades",
            hospedaje_id=1,
        )}

        EvaluadorIA().puntuar(candidatos(), analisis_previo, self._espec())

        prompt = generar.call_args.kwargs["contents"]
        self.assertIn("Medellin, Colombia", prompt)
        self.assertIn("USD $100 por noche", prompt)
        self.assertIn("cerca del metro", prompt)
        self.assertIn("Metro a 200 m", prompt)
        self.assertIn("Viaja con mascotas: no especificado", prompt)

    @patch("time.sleep")
    @patch("src.services.gemini.settings.GEMINI_API_KEY", "clave-prueba")
    @patch("src.services.gemini.genai.Client")
    def test_el_prompt_distingue_mascotas_desconocidas_de_negadas(self, cliente_mock, _sleep):
        generar = cliente_mock.return_value.models.generate_content
        generar.return_value = unittest.mock.Mock(
            text=leer_fixture("gemini_puntuacion_valida.json")
        )

        EvaluadorIA().puntuar(candidatos(), {}, self._espec().model_copy(
            update={"mascotas": True}
        ))

        self.assertIn(
            "Viaja con mascotas: sí",
            generar.call_args.kwargs["contents"],
        )

    @patch("time.sleep")
    @patch("src.services.gemini.settings.GEMINI_MAX_REINTENTOS", 2)
    @patch("src.services.gemini.settings.GEMINI_API_KEY", "clave-prueba")
    @patch("src.services.gemini.genai.Client")
    def test_respuesta_invalida_agota_reintentos_y_lanza_error(self, cliente_mock, sleep_mock):
        respuesta_invalida = unittest.mock.Mock(
            text=leer_fixture("gemini_puntuacion_invalida.json")
        )
        generar = cliente_mock.return_value.models.generate_content
        generar.return_value = respuesta_invalida

        with self.assertRaises(LoteIAError) as contexto:
            EvaluadorIA().puntuar(candidatos(), {}, self._espec())

        self.assertEqual(contexto.exception.operacion, "puntuar")
        self.assertEqual(generar.call_count, 3)
        self.assertEqual(sleep_mock.call_count, 2)

    @patch("time.sleep")
    @patch("src.services.gemini.settings.GEMINI_MAX_REINTENTOS", 1)
    @patch("src.services.gemini.settings.GEMINI_API_KEY", "clave-prueba")
    @patch("src.services.gemini.genai.Client")
    def test_devuelve_la_respuesta_parcial_si_nunca_llega_completa(self, cliente_mock, _sleep):
        parcial = unittest.mock.Mock(text="""
            {"puntuaciones": [
                {"hospedaje_id": 1, "score_calidad": 8, "score_cumplimiento": 9,
                 "requisitos_cumplidos": ["cerca del metro"], "requisitos_faltantes": []}
            ]}
        """)
        generar = cliente_mock.return_value.models.generate_content
        generar.return_value = parcial

        lote = EvaluadorIA().puntuar(candidatos(), {}, self._espec())

        self.assertEqual(len(lote), 1)
        self.assertEqual(generar.call_count, 2)

    @patch("time.sleep")
    @patch("src.services.gemini.settings.GEMINI_API_KEY", "clave-prueba")
    @patch("src.services.gemini.genai.Client")
    def test_el_prompt_incluye_distancias_y_tiempos_cuando_existen(self, cliente_mock, _sleep):
        generar = cliente_mock.return_value.models.generate_content
        generar.return_value = unittest.mock.Mock(
            text=leer_fixture("gemini_puntuacion_valida.json")
        )
        hoteles = candidatos()
        hoteles[0].distancia_km = 0.8
        hoteles[0].tiempo_auto_min = 2
        hoteles[0].tiempo_transit_min = 3
        hoteles[0].tiempo_walking_min = 10

        EvaluadorIA().puntuar(hoteles, {}, self._espec())

        prompt = generar.call_args.kwargs["contents"]
        self.assertIn('"distancia_km":0.8', prompt)
        self.assertIn('"tiempo_auto_min":2', prompt)
        self.assertIn('"tiempo_transit_min":3', prompt)
        self.assertIn('"tiempo_walking_min":10', prompt)
        self.assertIn("No inventes distancias ni ubicaciones", prompt)

    @patch("time.sleep")
    @patch("src.services.gemini.settings.GEMINI_API_KEY", "clave-prueba")
    @patch("src.services.gemini.genai.Client")
    def test_sin_distancia_el_prompt_no_incluye_el_campo(self, cliente_mock, _sleep):
        generar = cliente_mock.return_value.models.generate_content
        generar.return_value = unittest.mock.Mock(
            text=leer_fixture("gemini_puntuacion_valida.json")
        )

        EvaluadorIA().puntuar(candidatos(), {}, self._espec())

        prompt = generar.call_args.kwargs["contents"]
        self.assertNotIn('"distancia_km"', prompt)

    @patch("time.sleep")
    @patch("src.services.gemini.settings.GEMINI_API_KEY", "clave-prueba")
    @patch("src.services.gemini.genai.Client")
    def test_el_prompt_menciona_la_distancia_maxima_si_se_pide(self, cliente_mock, _sleep):
        generar = cliente_mock.return_value.models.generate_content
        generar.return_value = unittest.mock.Mock(
            text=leer_fixture("gemini_puntuacion_valida.json")
        )
        espec = self._espec().model_copy(update={"max_distancia_km": 1.5})

        EvaluadorIA().puntuar(candidatos(), {}, espec)

        prompt = generar.call_args.kwargs["contents"]
        self.assertIn("Distancia máxima: 1.5 km desde centro de la ciudad", prompt)

    def test_hospedaje_sin_id_lanza_value_error_en_analizar(self):
        hospedaje = Hospedaje(nombre="H", tipo="hotel", precio_noche=100, calificacion=4,
                             direccion="C", url_reserva="https://x", destino_id=1)
        # id es None por defecto
        with self.assertRaises(ValueError) as ctx:
            EvaluadorIA().analizar([hospedaje])
        self.assertIn("persistido", str(ctx.exception))

    def test_hospedaje_sin_id_lanza_value_error_en_puntuar(self):
        hospedaje = Hospedaje(nombre="H", tipo="hotel", precio_noche=100, calificacion=4,
                             direccion="C", url_reserva="https://x", destino_id=1)
        with self.assertRaises(ValueError) as ctx:
            EvaluadorIA().puntuar([hospedaje], {}, self._espec())
        self.assertIn("persistido", str(ctx.exception))



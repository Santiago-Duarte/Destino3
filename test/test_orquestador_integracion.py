import unittest
from unittest.mock import Mock, patch

from src.exceptions import PersistenciaError
from src.models.evaluacion import Evaluacion
from src.models.evaluacion_ia import LoteEvaluacionesIA
from src.models.evaluacion_ia import EvaluacionIAOutput
from src.models.hospedaje import Hospedaje
from src.orchestrator.orquestador_integracion import (
    IntegracionResultado,
    OrquestadorIntegracion,
)
from src.services.buscador_serpapi import buscar_hospedajes


def crear_hospedaje(nombre: str) -> Hospedaje:
    return Hospedaje(
        nombre=nombre,
        tipo="hotel",
        precio_noche=50,
        calificacion=4.5,
        direccion="Calle 1",
        url_reserva="https://hotel.example",
        destino_id=1,
    )


class TestOrquestadorIntegracion(unittest.TestCase):

    def setUp(self):
        self.buscar = Mock(return_value=[crear_hospedaje("Hotel A"), crear_hospedaje("Hotel B")])
        self.hospedajes_repo = Mock()
        self.hospedajes_repo.guardar_lote.return_value = [101, 102]
        self.evaluaciones_repo = Mock()
        self.evaluaciones_repo.guardar_lote.return_value = [201]
        self.evaluador = Mock()
        self.resultado_ia = (LoteEvaluacionesIA(evaluaciones=[]), {})
        self.evaluador.evaluar_lote.return_value = self.resultado_ia
        self.orquestador = OrquestadorIntegracion(
            buscar_hospedajes=self.buscar,
            hospedajes_repo=self.hospedajes_repo,
            evaluaciones_repo=self.evaluaciones_repo,
            evaluador=self.evaluador,
        )

    def test_busca_persiste_con_ids_reales_y_evalua_en_un_lote(self):
        resultado = self.orquestador.ejecutar("Medellin", "Colombia", 100, "cerca al parque")

        self.assertIsInstance(resultado, IntegracionResultado)
        self.assertEqual([h.id for h in resultado.hospedajes], [101, 102])
        self.assertIs(resultado.resultado_ia, self.resultado_ia)
        self.buscar.assert_called_once_with("Medellin", "Colombia", 100)
        self.hospedajes_repo.guardar_lote.assert_called_once_with(resultado.hospedajes)
        self.evaluador.evaluar_lote.assert_called_once_with(
            resultado.hospedajes, 100, "cerca al parque"
        )

    def test_persistir_evaluaciones_mapea_id_temporal_a_hospedaje_id_real(self):
        hospedaje = crear_hospedaje("Hotel evaluado")
        hospedaje.id = 101
        evaluacion_ia = EvaluacionIAOutput(
            id_temporal=1,
            resumen_ejecutivo="Bueno",
            puntos_fuertes="Ubicación",
            puntos_debiles="Precio",
            score_calidad_precio=8,
        )
        resultado = IntegracionResultado(
            hospedajes=[hospedaje],
            resultado_ia=(LoteEvaluacionesIA(evaluaciones=[evaluacion_ia]), {1: hospedaje}),
        )

        evaluaciones = self.orquestador.persistir_evaluaciones(resultado)

        self.assertEqual(len(evaluaciones), 1)
        self.assertIsInstance(evaluaciones[0], Evaluacion)
        self.assertEqual(evaluaciones[0].hospedaje_id, 101)
        self.assertEqual(evaluaciones[0].id, 201)
        self.evaluaciones_repo.guardar_lote.assert_called_once_with(evaluaciones)

    def test_fallo_ia_no_persiste_y_devuelve_lista_vacia(self):
        resultado = IntegracionResultado(hospedajes=[crear_hospedaje("Hotel")], resultado_ia=None)

        evaluaciones = self.orquestador.persistir_evaluaciones(resultado)

        self.assertEqual(evaluaciones, [])
        self.evaluaciones_repo.guardar_lote.assert_not_called()

    def test_id_temporal_huerfano_aborta_sin_persistir_parcialmente(self):
        hospedaje = crear_hospedaje("Hotel evaluado")
        hospedaje.id = 101
        evaluacion_ia = EvaluacionIAOutput(
            id_temporal=99,
            resumen_ejecutivo="Bueno",
            puntos_fuertes="Ubicación",
            puntos_debiles="Precio",
            score_calidad_precio=8,
        )
        resultado = IntegracionResultado(
            hospedajes=[hospedaje],
            resultado_ia=(LoteEvaluacionesIA(evaluaciones=[evaluacion_ia]), {1: hospedaje}),
        )

        with self.assertRaises(PersistenciaError):
            self.orquestador.persistir_evaluaciones(resultado)

        self.evaluaciones_repo.guardar_lote.assert_not_called()

    def test_sin_hospedajes_devuelve_lista_vacia_sin_persistir_ni_evaluar(self):
        buscar = Mock(return_value=[])
        hospedajes_repo = Mock()
        evaluador = Mock()
        orquestador = OrquestadorIntegracion(
            buscar_hospedajes=buscar,
            hospedajes_repo=hospedajes_repo,
            evaluador=evaluador,
        )

        resultado = orquestador.ejecutar("Medellin", "Colombia", 100, "")

        self.assertEqual(resultado, [])
        hospedajes_repo.guardar_lote.assert_not_called()
        evaluador.evaluar_lote.assert_not_called()

    @patch("src.services.buscador_serpapi.consultar_serpapi", return_value={"properties": []})
    def test_properties_vacias_no_persisten_ni_invocan_gemini(self, consultar_mock):
        hospedajes_repo = Mock()
        evaluador = Mock()
        orquestador = OrquestadorIntegracion(
            buscar_hospedajes=buscar_hospedajes,
            hospedajes_repo=hospedajes_repo,
            evaluador=evaluador,
        )

        resultado = orquestador.ejecutar("Medellin", "Colombia", 100, "")

        self.assertEqual(resultado, [])
        consultar_mock.assert_called_once_with("Medellin", "Colombia", 100)
        hospedajes_repo.guardar_lote.assert_not_called()
        evaluador.evaluar_lote.assert_not_called()


if __name__ == "__main__":
    unittest.main()

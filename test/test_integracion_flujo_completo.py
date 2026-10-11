import unittest
from unittest.mock import Mock

from src.models.evaluacion_ia import EvaluacionIAOutput, LoteEvaluacionesIA
from src.models.hospedaje import Hospedaje
from src.orchestrator.orquestador_integracion import OrquestadorIntegracion
from src.repositories.evaluacion_ia_repository import EvaluacionIARepository
from test.db_test_case import BaseDBTestCase


class TestIntegracionFlujoCompleto(BaseDBTestCase):

    def test_busqueda_persistencia_evaluacion_y_persistencia_final(self):
        destino_id = self.crear_destino()
        hospedajes = [
            Hospedaje(
                nombre="Hotel Simulado",
                tipo="hotel",
                precio_noche=80,
                calificacion=4.5,
                direccion="Calle 1",
                url_reserva="https://hotel.example",
                destino_id=destino_id,
            )
        ]
        buscador = Mock(return_value=hospedajes)
        hospedajes_repo = self.hospedaje_repo
        evaluador = Mock()
        respuesta_ia = LoteEvaluacionesIA(evaluaciones=[
            EvaluacionIAOutput(
                id_temporal=1,
                resumen_ejecutivo="Buena opción",
                puntos_fuertes="Ubicación",
                puntos_debiles="Precio",
                score_calidad_precio=8,
            )
        ])
        evaluador.evaluar_lote.return_value = respuesta_ia, {1: hospedajes[0]}
        orquestador = OrquestadorIntegracion(
            buscar_hospedajes=buscador,
            hospedajes_repo=hospedajes_repo,
            evaluador=evaluador,
            evaluaciones_repo=EvaluacionIARepository(),
        )

        resultado = orquestador.ejecutar("Medellin", "Colombia", 100, "")
        evaluaciones = orquestador.persistir_evaluaciones(resultado)

        evaluacion_persistida = EvaluacionIARepository().obtener_por_hospedaje(
            hospedajes[0].id
        )
        self.assertEqual(len(resultado.hospedajes), 1)
        self.assertIsInstance(hospedajes[0].id, int)
        self.assertEqual(evaluador.evaluar_lote.call_count, 1)
        self.assertEqual(len(evaluaciones), 1)
        self.assertIsNotNone(evaluacion_persistida)
        self.assertEqual(evaluacion_persistida.hospedaje_id, hospedajes[0].id)
        self.assertEqual(evaluacion_persistida.score_calidad_precio, 8)


if __name__ == "__main__":
    unittest.main()

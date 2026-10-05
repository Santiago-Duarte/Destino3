import unittest
from unittest.mock import patch

from src.models.evaluacion_ia import EvaluacionIAOutput, LoteEvaluacionesIA
from src.models.hospedaje import Hospedaje
from src.orchestrator.orquestador_evaluacion import OrquestadorEvaluacion


def crear_hospedaje(id, nombre):
    return Hospedaje(
        id=id,
        nombre=nombre,
        tipo="hotel",
        precio_noche=100,
        calificacion=4.5,
        direccion="Centro",
        url_reserva="https://hotel.example",
        destino_id=1,
    )


def crear_evaluacion_ia(id_temporal, score=8):
    return EvaluacionIAOutput(
        id_temporal=id_temporal,
        resumen_ejecutivo="Resumen.",
        puntos_fuertes="Fuertes.",
        puntos_debiles="Débiles.",
        score_calidad_precio=score,
    )


class TestOrquestadorEvaluacion(unittest.TestCase):

    def setUp(self):
        parche_evaluador = patch("src.orchestrator.orquestador_evaluacion.EvaluadorIA")
        parche_evaluaciones = patch("src.orchestrator.orquestador_evaluacion.EvaluacionIARepository")
        parche_recomendaciones = patch("src.orchestrator.orquestador_evaluacion.RecomendacionRepository")

        self.evaluador = parche_evaluador.start().return_value
        self.evaluaciones_repo = parche_evaluaciones.start().return_value
        self.recomendaciones_repo = parche_recomendaciones.start().return_value

        for parche in (parche_evaluador, parche_evaluaciones, parche_recomendaciones):
            self.addCleanup(parche.stop)

        self.orquestador = OrquestadorEvaluacion()

    def _ejecutar(self, hospedajes):
        return self.orquestador.evaluar_y_persistir(
            hospedajes,
            busqueda_id=7,
            presupuesto_max=100,
            preferencias="vista al mar",
        )

    def _recomendaciones_guardadas(self):
        return self.recomendaciones_repo.guardar_lote.call_args.args[0]

    def test_lote_de_ia_fallido_no_persiste_nada(self):
        self.evaluador.evaluar_lote.return_value = None

        evaluaciones = self._ejecutar([crear_hospedaje(10, "Hotel A")])

        self.assertEqual(evaluaciones, [])
        self.evaluaciones_repo.guardar_lote.assert_not_called()
        self.recomendaciones_repo.guardar_lote.assert_not_called()

    def test_persiste_evaluaciones_con_su_id_y_recomendaciones_ordenadas(self):
        hospedajes = [crear_hospedaje(10, "Hotel A"), crear_hospedaje(11, "Hotel B")]
        respuesta = LoteEvaluacionesIA(evaluaciones=[crear_evaluacion_ia(1), crear_evaluacion_ia(2, score=6)])
        self.evaluador.evaluar_lote.return_value = (respuesta, {1: hospedajes[0], 2: hospedajes[1]})
        self.evaluaciones_repo.guardar_lote.return_value = [101, 102]

        evaluaciones = self._ejecutar(hospedajes)

        self.assertEqual([e.id for e in evaluaciones], [101, 102])
        self.assertEqual([e.hospedaje_id for e in evaluaciones], [10, 11])
        self.assertEqual([e.score_calidad_precio for e in evaluaciones], [8, 6])
        self.evaluaciones_repo.guardar_lote.assert_called_once()
        self.assertEqual(
            [(r.busqueda_id, r.hospedaje_id, r.posicion) for r in self._recomendaciones_guardadas()],
            [(7, 10, 1), (7, 11, 2)],
        )

    def test_descarta_id_temporal_huerfano_sin_dejar_huecos_de_posicion(self):
        hotel = crear_hospedaje(10, "Hotel A")
        respuesta = LoteEvaluacionesIA(evaluaciones=[crear_evaluacion_ia(1), crear_evaluacion_ia(99)])
        self.evaluador.evaluar_lote.return_value = (respuesta, {1: hotel})
        self.evaluaciones_repo.guardar_lote.return_value = [101]

        evaluaciones = self._ejecutar([hotel])

        self.assertEqual([e.hospedaje_id for e in evaluaciones], [10])
        self.assertEqual([r.posicion for r in self._recomendaciones_guardadas()], [1])

    def test_respuesta_vacia_no_genera_recomendaciones(self):
        respuesta = LoteEvaluacionesIA(evaluaciones=[])
        self.evaluador.evaluar_lote.return_value = (respuesta, {})
        self.evaluaciones_repo.guardar_lote.return_value = []

        evaluaciones = self._ejecutar([crear_hospedaje(10, "Hotel A")])

        self.assertEqual(evaluaciones, [])
        self.recomendaciones_repo.guardar_lote.assert_not_called()


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import Mock

from src.models.evaluacion_ia import LoteEvaluacionesIA
from src.models.hospedaje import Hospedaje
from src.orchestrator.orquestador_integracion import (
    IntegracionResultado,
    OrquestadorIntegracion,
)


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
        self.evaluador = Mock()
        self.resultado_ia = (LoteEvaluacionesIA(evaluaciones=[]), {})
        self.evaluador.evaluar_lote.return_value = self.resultado_ia
        self.orquestador = OrquestadorIntegracion(
            buscar_hospedajes=self.buscar,
            hospedajes_repo=self.hospedajes_repo,
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


if __name__ == "__main__":
    unittest.main()

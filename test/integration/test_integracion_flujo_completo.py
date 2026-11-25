import uuid
from unittest.mock import Mock

from src.models.analisis_ia import (
    AnalisisIAOutput,
    LoteAnalisisIA,
    LotePuntuacionesIA,
    PuntuacionIAOutput,
)
from src.models.busqueda import EspecificacionBusqueda
from src.models.hospedaje import Hospedaje
from src.orchestrator.orquestador_integracion import OrquestadorIntegracion
from src.repositories.analisis_ia_repository import AnalisisIARepository
from test.caso_prueba_bd import BaseDBTestCase


class TestIntegracionFlujoCompleto(BaseDBTestCase):

    def setUp(self):
        super().setUp()
        self.destino_id = self.crear_destino(ciudad=f"Medellin_{uuid.uuid4().hex}")
        self.tokens = [f"ChIJ-{uuid.uuid4().hex}-A", f"ChIJ-{uuid.uuid4().hex}-B"]
        self.espec = EspecificacionBusqueda(
            ciudad="Medellin",
            pais="Colombia",
            presupuesto_max_noche=100,
            preferencias="cerca del metro",
        )

    def _hospedajes_nuevos(self):
        return [
            Hospedaje(
                nombre=f"Hotel Simulado {indice}",
                tipo="hotel",
                precio_noche=80,
                calificacion=4.5,
                direccion="Calle 1",
                url_reserva="https://hotel.example",
                destino_id=self.destino_id,
                google_place_id=token,
            )
            for indice, token in enumerate(self.tokens, start=1)
        ]

    def _evaluador(self):
        evaluador = Mock()
        evaluador.analizar.side_effect = lambda hospedajes: LoteAnalisisIA(
            analisis=[
                AnalisisIAOutput(
                    hospedaje_id=hospedaje.id,
                    resumen_ejecutivo=f"Análisis de {hospedaje.nombre}",
                    puntos_fuertes="Ubicación; desayuno",
                    puntos_debiles="Habitaciones pequeñas",
                )
                for hospedaje in hospedajes
            ]
        )
        evaluador.puntuar.side_effect = lambda hospedajes, _analisis, _espec: LotePuntuacionesIA(
            puntuaciones=[
                PuntuacionIAOutput(
                    hospedaje_id=hospedaje.id,
                    score_calidad=8,
                    score_cumplimiento=10 if indice == 1 else 4,
                    requisitos_cumplidos=(["presupuesto hasta 100 USD", "cerca del metro"]
                                          if indice == 1
                                          else ["presupuesto hasta 100 USD"]),
                    requisitos_faltantes=[] if indice == 1 else ["cerca del metro"],
                )
                for indice, hospedaje in enumerate(hospedajes, start=1)
            ]
        )
        return evaluador

    def _orquestador(self, evaluador):
        return OrquestadorIntegracion(
            buscar_hospedajes=Mock(side_effect=lambda *_argumentos: self._hospedajes_nuevos()),
            hospedajes_repo=self.hospedaje_repo,
            analisis_repo=AnalisisIARepository(),
            evaluador=evaluador,
        )

    def test_persiste_hospedajes_y_analisis_y_devuelve_el_top_ordenado(self):
        evaluador = self._evaluador()

        resultado = self._orquestador(evaluador).buscar(self.espec)

        persistidos = self.hospedaje_repo.obtener_por_destino(self.destino_id)
        self.assertEqual(len(persistidos), 2)

        guardados = AnalisisIARepository().obtener_por_hospedajes(
            [hospedaje.id for hospedaje in persistidos]
        )
        self.assertEqual(len(guardados), 2)

        self.assertEqual(len(resultado.mejores()), 2)
        self.assertEqual(resultado.candidatos[0].score_cumplimiento, 10)
        self.assertEqual(resultado.candidatos[1].score_cumplimiento, 4)
        self.assertIsNotNone(resultado.candidatos[0].analisis)
        self.assertEqual(
            resultado.candidatos[0].analisis.resumen_ejecutivo,
            f"Análisis de {resultado.candidatos[0].hospedaje.nombre}",
        )

    def test_repetir_la_busqueda_no_duplica_hospedajes_ni_vuelve_a_analizar(self):
        evaluador = self._evaluador()
        orquestador = self._orquestador(evaluador)

        primera = orquestador.buscar(self.espec)
        evaluador.analizar.reset_mock()
        segunda = orquestador.buscar(self.espec)

        self.assertEqual(
            sorted(candidato.hospedaje.id for candidato in segunda.candidatos),
            sorted(candidato.hospedaje.id for candidato in primera.candidatos),
        )
        self.assertEqual(len(self.hospedaje_repo.obtener_por_destino(self.destino_id)), 2)
        evaluador.analizar.assert_not_called()
        self.assertIsNotNone(segunda.candidatos[0].analisis)



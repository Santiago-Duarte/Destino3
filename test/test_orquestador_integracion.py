import unittest
from unittest.mock import Mock

from src.exceptions.LoteIAError import LoteIAError
from src.models.analisis import Analisis
from src.models.analisis_ia import (
    AnalisisIAOutput,
    LoteAnalisisIA,
    LotePuntuacionesIA,
    PuntuacionIAOutput,
)
from src.models.busqueda import EspecificacionBusqueda
from src.models.hospedaje import Hospedaje
from src.orchestrator.orquestador_integracion import OrquestadorIntegracion


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


def analisis_de(hospedaje_id: int, resumen: str = "Resumen") -> AnalisisIAOutput:
    return AnalisisIAOutput(
        hospedaje_id=hospedaje_id,
        resumen_ejecutivo=resumen,
        puntos_fuertes="Fuertes",
        puntos_debiles="Débiles",
    )


def puntuacion_de(
        hospedaje_id: int,
        calidad: int,
        cumplimiento: int,
        cumplidos=("presupuesto hasta 100 USD",),
        faltantes=(),
) -> PuntuacionIAOutput:
    return PuntuacionIAOutput(
        hospedaje_id=hospedaje_id,
        score_calidad=calidad,
        score_cumplimiento=cumplimiento,
        requisitos_cumplidos=list(cumplidos),
        requisitos_faltantes=list(faltantes),
    )


class TestBuscar(unittest.TestCase):

    def setUp(self):
        self.espec = EspecificacionBusqueda(
            ciudad="Medellin",
            pais="Colombia",
            presupuesto_max_noche=100,
            preferencias="cerca del metro",
        )
        self.buscar = Mock(return_value=[crear_hospedaje("Hotel A"), crear_hospedaje("Hotel B")])
        self.hospedajes_repo = Mock()
        self.hospedajes_repo.guardar_lote.return_value = [101, 102]
        self.analisis_repo = Mock()
        self.analisis_repo.obtener_por_hospedajes.return_value = {}
        self.analisis_repo.guardar_lote.return_value = [201, 202]
        self.evaluador = Mock()
        self.evaluador.analizar.return_value = LoteAnalisisIA(analisis=[
            analisis_de(101, "Análisis A"),
            analisis_de(102, "Análisis B"),
        ])
        self.evaluador.puntuar.return_value = LotePuntuacionesIA(puntuaciones=[
            puntuacion_de(101, calidad=8, cumplimiento=5,
                          faltantes=["cerca del metro"]),
            puntuacion_de(102, calidad=7, cumplimiento=9,
                          cumplidos=("presupuesto hasta 100 USD", "cerca del metro")),
        ])
        self.orquestador = OrquestadorIntegracion(
            buscar_hospedajes=self.buscar,
            hospedajes_repo=self.hospedajes_repo,
            analisis_repo=self.analisis_repo,
            evaluador=self.evaluador,
        )

    def test_busca_persiste_analiza_puntua_y_ordena(self):
        resultado = self.orquestador.buscar(self.espec)

        self.buscar.assert_called_once_with(self.espec)
        self.assertEqual(
            [candidato.hospedaje.id for candidato in resultado.candidatos],
            [102, 101],
        )
        self.assertEqual(
            [candidato.hospedaje.id for candidato in resultado.mejores()],
            [102, 101],
        )
        self.assertEqual(resultado.candidatos[0].analisis.resumen_ejecutivo, "Análisis B")

    def test_persiste_el_analisis_nuevo_de_cada_candidato(self):
        self.orquestador.buscar(self.espec)

        self.evaluador.analizar.assert_called_once()
        ids_analizados = [hospedaje.id for hospedaje in
                          self.evaluador.analizar.call_args.args[0]]
        self.assertEqual(ids_analizados, [101, 102])

        guardados = self.analisis_repo.guardar_lote.call_args.args[0]
        self.assertEqual([item.hospedaje_id for item in guardados], [101, 102])
        self.assertIsInstance(guardados[0], Analisis)

    def test_reutiliza_el_analisis_guardado_sin_volver_a_llamar_a_la_ia(self):
        self.analisis_repo.obtener_por_hospedajes.return_value = {
            101: Analisis("Análisis guardado A", "Fuertes", "Débiles", 101),
            102: Analisis("Análisis guardado B", "Fuertes", "Débiles", 102),
        }

        resultado = self.orquestador.buscar(self.espec)

        self.evaluador.analizar.assert_not_called()
        self.assertIsNone(self.analisis_repo.guardar_lote.call_args)
        self.assertEqual(
            [candidato.analisis.resumen_ejecutivo for candidato in resultado.candidatos],
            ["Análisis guardado B", "Análisis guardado A"],
        )

    def test_sin_hospedajes_no_persiste_ni_evalua(self):
        self.buscar.return_value = []

        resultado = self.orquestador.buscar(self.espec)

        self.assertEqual(resultado.candidatos, [])
        self.assertEqual(resultado.mejores(), [])
        self.hospedajes_repo.guardar_lote.assert_not_called()
        self.evaluador.analizar.assert_not_called()
        self.evaluador.puntuar.assert_not_called()

    def test_candidato_sin_puntaje_queda_al_final_del_ranking(self):
        self.evaluador.puntuar.return_value = LotePuntuacionesIA(
            puntuaciones=[puntuacion_de(101, calidad=8, cumplimiento=4)]
        )

        resultado = self.orquestador.buscar(self.espec)

        self.assertEqual(
            [candidato.hospedaje.id for candidato in resultado.candidatos],
            [101, 102],
        )
        self.assertIsNone(resultado.candidatos[1].score_cumplimiento)
        self.assertEqual(
            [candidato.hospedaje.id for candidato in resultado.mejores()],
            [101],
        )

    def test_los_que_no_cumplen_ningun_requisito_no_entran_al_top(self):
        self.evaluador.puntuar.return_value = LotePuntuacionesIA(puntuaciones=[
            puntuacion_de(101, calidad=9, cumplimiento=3,
                          cumplidos=(), faltantes=("cerca del metro",)),
            puntuacion_de(102, calidad=6, cumplimiento=8,
                          cumplidos=("cerca del metro",)),
        ])

        resultado = self.orquestador.buscar(self.espec)

        self.assertEqual(
            [candidato.hospedaje.id for candidato in resultado.candidatos],
            [102, 101],
        )
        self.assertEqual(
            [candidato.hospedaje.id for candidato in resultado.mejores()],
            [102],
        )

    def test_sin_requisitos_en_la_frase_entran_todos_los_puntuados(self):
        sin_requisitos = EspecificacionBusqueda(
            ciudad="Medellin", pais="Colombia"
        )
        self.evaluador.puntuar.return_value = LotePuntuacionesIA(puntuaciones=[
            puntuacion_de(101, calidad=9, cumplimiento=5, cumplidos=()),
            puntuacion_de(102, calidad=6, cumplimiento=4, cumplidos=()),
        ])

        resultado = self.orquestador.buscar(sin_requisitos)

        self.buscar.assert_called_once_with(sin_requisitos)
        self.assertEqual(len(resultado.mejores()), 2)

    def test_fallo_de_la_ia_al_analizar_no_interrumpe_la_busqueda(self):
        self.evaluador.analizar.side_effect = LoteIAError("analizar", "falló")

        resultado = self.orquestador.buscar(self.espec)

        self.assertEqual(len(resultado.candidatos), 2)
        self.assertIsNone(resultado.candidatos[0].analisis)
        self.evaluador.puntuar.assert_called_once()
        self.assertEqual(len(resultado.mejores()), 2)

    def test_fallo_de_la_ia_al_puntuar_conserva_los_candidatos_sin_puntaje(self):
        self.evaluador.puntuar.side_effect = LoteIAError("puntuar", "falló")

        resultado = self.orquestador.buscar(self.espec)

        self.assertEqual(
            [candidato.hospedaje.nombre for candidato in resultado.candidatos],
            ["Hotel A", "Hotel B"],
        )
        self.assertTrue(
            all(candidato.score_cumplimiento is None for candidato in resultado.candidatos)
        )
        self.assertEqual(resultado.mejores(), [])


if __name__ == "__main__":
    unittest.main()

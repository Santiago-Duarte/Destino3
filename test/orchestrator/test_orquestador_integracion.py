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
from src.models.destino import Destino
from src.models.hospedaje import Hospedaje
from src.orchestrator.orquestador_integracion import OrquestadorIntegracion


def crear_hospedaje(
        nombre: str,
        latitud: float | None = 6.2500,
        longitud: float | None = -75.5800,
) -> Hospedaje:
    return Hospedaje(
        nombre=nombre,
        tipo="hotel",
        precio_noche=50,
        calificacion=4.5,
        direccion="Calle 1",
        url_reserva="https://hotel.example",
        destino_id=1,
        latitud=latitud,
        longitud=longitud,
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
        self.destino_repo = Mock()
        self.destino_repo.obtener_por_ciudad_pais.return_value = Destino(
            id=1,
            ciudad="Medellin",
            pais="Colombia",
            latitud=6.2442,
            longitud=-75.5812,
        )
        self.geocodificar = Mock(return_value=(6.2442, -75.5812))
        self.orquestador = OrquestadorIntegracion(
            buscar_hospedajes=self.buscar,
            hospedajes_repo=self.hospedajes_repo,
            analisis_repo=self.analisis_repo,
            evaluador=self.evaluador,
            destino_repo=self.destino_repo,
            geocodificar=self.geocodificar,
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

    def test_preseleccion_vacia_no_lanza_error(self):
        """Hoteles encontrados pero todos fuera del presupuesto."""
        self.evaluador.puntuar.return_value = LotePuntuacionesIA(puntuaciones=[])

        # Presupuesto muy bajo: ninguno de los dos hoteles (50/60) pasa el filtro.
        espec_ajena = EspecificacionBusqueda(
            ciudad="Medellin", pais="Colombia", presupuesto_max_noche=10
        )
        resultado = self.orquestador.buscar(espec_ajena)

        self.assertEqual(resultado.candidatos, [])
        self.assertEqual(resultado.mejores(), [])

    def test_score_cumplimiento_igual_a_umbral_entra_al_top(self):
        """Score igual al mínimo (7) entra cuando no hay requisitos cumplidos."""
        self.evaluador.puntuar.return_value = LotePuntuacionesIA(puntuaciones=[
            puntuacion_de(101, calidad=5, cumplimiento=7, cumplidos=(), faltantes=()),
            puntuacion_de(102, calidad=4, cumplimiento=6, cumplidos=(), faltantes=()),
        ])

        resultado = self.orquestador.buscar(self.espec)

        # 101 cumple 7 >= SCORE_CUMPLIMIENTO_MINIMO → entra
        # 102 no (6 < 7) → fuera
        self.assertEqual(len(resultado.mejores()), 1)
        self.assertEqual(resultado.mejores()[0].hospedaje.id, 101)

    def test_top_resultados_corta_el_top(self):
        """TOP_RESULTADOS=3 limita el número de candidatos en mejores()."""
        # Cambiar el mock de búsqueda para devolver 5 hoteles
        hoteles = [crear_hospedaje(f"Hotel {i}") for i in range(1, 6)]
        for i, h in enumerate(hoteles, start=1):
            h.id = i
        self.buscar.return_value = hoteles
        self.hospedajes_repo.guardar_lote.return_value = list(range(1, 6))

        self.evaluador.puntuar.return_value = LotePuntuacionesIA(puntuaciones=[
            puntuacion_de(i, calidad=10, cumplimiento=10, cumplidos=("presupuesto",))
            for i in range(1, 6)
        ])

        resultado = self.orquestador.buscar(self.espec)

        self.assertEqual(len(resultado.candidatos), 5)
        self.assertEqual(len(resultado.mejores()), 3)
        # Verifica que están ordenados por cumplimiento desc, calidad desc
        # (orden estable: al empatar, preserva el orden original)
        ids = [c.hospedaje.id for c in resultado.mejores()]
        self.assertEqual(ids, [1, 2, 3])

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


class TestDistancias(unittest.TestCase):

    def setUp(self):
        self.espec = EspecificacionBusqueda(
            ciudad="Medellin",
            pais="Colombia",
            presupuesto_max_noche=100,
        )
        self.hotel_cerca = crear_hospedaje(
            "Hotel cerca", latitud=6.2442, longitud=-75.5812
        )
        self.hotel_lejos = crear_hospedaje(
            "Hotel lejos", latitud=6.3500, longitud=-75.5812
        )
        self.buscar = Mock(return_value=[self.hotel_cerca, self.hotel_lejos])
        self.hospedajes_repo = Mock()
        self.hospedajes_repo.guardar_lote.return_value = [101, 102]
        self.analisis_repo = Mock()
        self.analisis_repo.obtener_por_hospedajes.return_value = {}
        self.analisis_repo.guardar_lote.side_effect = (
            lambda analisis: list(range(201, 201 + len(analisis)))
        )
        self.evaluador = Mock()
        self.evaluador.analizar.return_value = LoteAnalisisIA(analisis=[
            analisis_de(101), analisis_de(102),
        ])
        self.evaluador.puntuar.return_value = LotePuntuacionesIA(puntuaciones=[
            puntuacion_de(101, calidad=8, cumplimiento=8),
            puntuacion_de(102, calidad=7, cumplimiento=8),
        ])
        self.destino_repo = Mock()
        self.destino_repo.obtener_por_ciudad_pais.return_value = Destino(
            id=1,
            ciudad="Medellin",
            pais="Colombia",
            latitud=6.2442,
            longitud=-75.5812,
        )
        self.geocodificar = Mock(return_value=(6.2442, -75.5812))

    def _orquestador(self) -> OrquestadorIntegracion:
        return OrquestadorIntegracion(
            buscar_hospedajes=self.buscar,
            hospedajes_repo=self.hospedajes_repo,
            analisis_repo=self.analisis_repo,
            evaluador=self.evaluador,
            destino_repo=self.destino_repo,
            geocodificar=self.geocodificar,
        )

    def test_calcula_distancia_y_tiempos_desde_el_centro(self):
        resultado = self._orquestador().buscar(self.espec)

        cercano = resultado.candidatos[0].hospedaje
        self.assertAlmostEqual(cercano.distancia_km, 0.0, places=2)
        self.assertEqual(cercano.tiempo_auto_min, 0)
        self.assertEqual(cercano.tiempo_transit_min, 0)
        self.assertEqual(cercano.tiempo_walking_min, 0)

        lejano = resultado.candidatos[1].hospedaje
        self.assertIsNotNone(lejano.distancia_km)
        self.assertGreater(lejano.distancia_km, 10)
        self.assertGreater(lejano.tiempo_auto_min, 0)
        self.assertGreater(lejano.tiempo_walking_min, lejano.tiempo_auto_min)

    def test_hotel_sin_coordenadas_queda_sin_distancia(self):
        self.buscar.return_value = [crear_hospedaje("Sin GPS", latitud=None, longitud=None)]
        self.hospedajes_repo.guardar_lote.return_value = [101]

        resultado = self._orquestador().buscar(self.espec)

        self.assertIsNone(resultado.candidatos[0].hospedaje.distancia_km)

    def test_filtro_de_distancia_excluye_hoteles_lejanos(self):
        espec = self.espec.model_copy(update={"max_distancia_km": 1.0})

        resultado = self._orquestador().buscar(espec)

        self.assertEqual(
            [candidato.hospedaje.nombre for candidato in resultado.candidatos],
            ["Hotel cerca"],
        )

    def test_filtro_de_distancia_sin_coordenadas_no_devuelve_nada(self):
        self.buscar.return_value = [crear_hospedaje("Sin GPS", latitud=None, longitud=None)]
        self.hospedajes_repo.guardar_lote.return_value = [101]
        espec = self.espec.model_copy(update={"max_distancia_km": 1.0})

        resultado = self._orquestador().buscar(espec)

        self.assertEqual(resultado.candidatos, [])

    def test_sin_coordenadas_del_destino_continua_sin_distancias(self):
        self.destino_repo.obtener_por_ciudad_pais.return_value = Destino(
            id=1, ciudad="Medellin", pais="Colombia"
        )
        self.geocodificar.return_value = None

        resultado = self._orquestador().buscar(self.espec)

        self.assertEqual(len(resultado.candidatos), 2)
        self.assertTrue(
            all(c.hospedaje.distancia_km is None for c in resultado.candidatos)
        )

    def test_geocodifica_y_guarda_cuando_el_destino_no_tiene_coordenadas(self):
        self.destino_repo.obtener_por_ciudad_pais.return_value = Destino(
            id=1, ciudad="Medellin", pais="Colombia"
        )

        self._orquestador().buscar(self.espec)

        self.geocodificar.assert_called_once_with("Medellin", "Colombia")
        self.destino_repo.actualizar_coordenadas.assert_called_once_with(
            1, 6.2442, -75.5812
        )

    def test_no_geocodifica_si_el_destino_ya_tiene_coordenadas(self):
        self._orquestador().buscar(self.espec)

        self.geocodificar.assert_not_called()
        self.destino_repo.actualizar_coordenadas.assert_not_called()

    def test_destino_inexistente_no_interrumpe_la_busqueda(self):
        self.destino_repo.obtener_por_ciudad_pais.return_value = None

        resultado = self._orquestador().buscar(self.espec)

        self.assertEqual(len(resultado.candidatos), 2)
        self.geocodificar.assert_not_called()

    def test_error_del_repositorio_de_destino_no_interrumpe_la_busqueda(self):
        self.destino_repo.obtener_por_ciudad_pais.side_effect = RuntimeError("BD caída")

        resultado = self._orquestador().buscar(self.espec)

        self.assertEqual(len(resultado.candidatos), 2)
        self.assertTrue(
            all(c.hospedaje.distancia_km is None for c in resultado.candidatos)
        )



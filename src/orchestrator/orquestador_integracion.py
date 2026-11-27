import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from src.config import settings
from src.exceptions.LoteIAError import LoteIAError
from src.models.analisis import Analisis
from src.models.busqueda import EspecificacionBusqueda
from src.models.destino import Destino
from src.models.hospedaje import Hospedaje
from src.repositories.analisis_ia_repository import AnalisisIARepository
from src.repositories.destino_repository import DestinoRepository
from src.repositories.hospedaje_repository import HospedajeRepository
from src.services.buscador_serpapi import buscar_hospedajes
from src.services.distancias import aplicar_distancias
from src.services.evaluador_ia import EvaluadorIA, preseleccionar_candidatos
from src.services.geocodificador import geocodificar, geocodificar_punto

logger = logging.getLogger(__name__)


@dataclass
class Candidato:
    hospedaje: Hospedaje
    analisis: Analisis | None = None
    score_calidad: int | None = None
    score_cumplimiento: int | None = None
    requisitos_cumplidos: list[str] = field(default_factory=list)
    requisitos_faltantes: list[str] = field(default_factory=list)


@dataclass
class ResultadoBusqueda:
    especificacion: EspecificacionBusqueda
    candidatos: list[Candidato]  # ya rankeados

    def mejores(self, cantidad: int | None = None) -> list[Candidato]:
        """Devuelve el top de candidatos puntuados.

        Con requisitos, un candidato entra si la IA reportó al menos un
        requisito cumplido o si su score es suficientemente alto. El score
        cubre el caso de una respuesta parcial sin listas de requisitos.
        """
        cantidad = settings.TOP_RESULTADOS if cantidad is None else cantidad
        puntuados = [
            candidato for candidato in self.candidatos
            if candidato.score_cumplimiento is not None
        ]
        if self.especificacion.tiene_requisitos():
            filtrados = []
            for candidato in puntuados:
                score = candidato.score_cumplimiento
                if candidato.requisitos_cumplidos or (
                        score is not None
                        and score >= settings.SCORE_CUMPLIMIENTO_MINIMO
                ):
                    filtrados.append(candidato)
            puntuados = filtrados
        return puntuados[:cantidad]


def _id_de(candidato: Candidato) -> int:
    """Los candidatos ya persistidos deben tener id para analizarse."""
    if candidato.hospedaje.id is None:
        raise ValueError("El hospedaje del candidato no está persistido")
    return candidato.hospedaje.id


def rankear_candidatos(candidatos: list[Candidato]) -> list[Candidato]:
    """Cumplimiento primero y después calidad; sin puntaje quedan al final."""
    return sorted(
        candidatos,
        key=lambda candidato: (
            candidato.score_cumplimiento is not None,
            candidato.score_cumplimiento or 0,
            candidato.score_calidad or 0,
        ),
        reverse=True,
    )


class OrquestadorIntegracion:

    def __init__(
            self,
            buscar_hospedajes: Callable[
                [EspecificacionBusqueda], list[Hospedaje]
            ] = buscar_hospedajes,
            hospedajes_repo: HospedajeRepository | None = None,
            analisis_repo: AnalisisIARepository | None = None,
            evaluador: EvaluadorIA | None = None,
            destino_repo: DestinoRepository | None = None,
            geocodificar: Callable[
                [str, str], tuple[float, float] | None
            ] = geocodificar,
            geocodificar_punto: Callable[
                [str, str, str], tuple[float, float] | None
            ] = geocodificar_punto,
    ) -> None:
        self._buscar_hospedajes = buscar_hospedajes
        self._hospedajes_repo = hospedajes_repo
        self._analisis_repo = analisis_repo
        self._evaluador = evaluador
        self._destino_repo = destino_repo
        self._geocodificar = geocodificar
        self._geocodificar_punto = geocodificar_punto

    def buscar(self, espec: EspecificacionBusqueda) -> ResultadoBusqueda:
        hospedajes = self._buscar_hospedajes(espec)
        if not hospedajes:
            return ResultadoBusqueda(espec, [])

        repositorio_hospedajes = self._hospedajes_repo or HospedajeRepository()
        for hospedaje, id_generado in zip(
                hospedajes,
                repositorio_hospedajes.guardar_lote(hospedajes),
                strict=True,
        ):
            hospedaje.id = id_generado

        self._calcular_distancias(hospedajes, espec)
        if espec.max_distancia_km is not None:
            hospedajes = [
                hospedaje for hospedaje in hospedajes
                if hospedaje.distancia_km is not None
                and hospedaje.distancia_km <= espec.max_distancia_km
            ]
            if not hospedajes:
                logger.warning(
                    "Ningún hotel quedó dentro de %s km del centro",
                    espec.max_distancia_km,
                )
                return ResultadoBusqueda(espec, [])

        candidatos = [
            Candidato(hospedaje=hospedaje)
            for hospedaje in preseleccionar_candidatos(
                hospedajes, espec.presupuesto_max_noche
            )
        ]
        if not candidatos:
            return ResultadoBusqueda(espec, [])

        self._completar_analisis(candidatos)
        self._puntuar(candidatos, espec)
        return ResultadoBusqueda(espec, rankear_candidatos(candidatos))

    def _calcular_distancias(
            self,
            hospedajes: list[Hospedaje],
            espec: EspecificacionBusqueda,
    ) -> None:
        """Completa distancia y tiempos desde el punto de referencia (o centro si no hay).

        Si la especificación tiene `punto_referencia`, se intenta geocodificar ese
        punto específico. Si falla o no se especifica, se usa el centro de la ciudad.
        La falta de coordenadas no rompe el flujo principal.
        """
        try:
            coordenadas_origen, punto_usado = self._coordenadas_origen(espec)
        except Exception as error:
            logger.warning(
                "No se pudieron resolver las coordenadas de origen: %s",
                type(error).__name__,
            )
            return

        if coordenadas_origen is None:
            return
        aplicar_distancias(hospedajes, coordenadas_origen)

        # Guardar en la especificación qué punto se usó para que el evaluador y CLI lo sepan
        espec.punto_referencia_usado = punto_usado

    def _coordenadas_origen(
            self,
            espec: EspecificacionBusqueda,
    ) -> tuple[tuple[float, float] | None, str | None]:
        """Devuelve ``(coordenadas, descripcion_punto_usado)``.

        Prioridad:
        1. Si espec.punto_referencia existe → geocodifica ese punto; guarda en BD.
        2. Si destino ya tiene referencia guardada y coincide → úsala.
        3. Si destino tiene centro guardado → úsalo.
        4. Geocodifica centro de la ciudad; guarda en BD.
        """
        repositorio = self._destino_repo or DestinoRepository()
        destino: Destino | None = repositorio.obtener_por_ciudad_pais(
            espec.ciudad, espec.pais
        )
        if destino is None:
            return (None, None)

        # 1. Usuario pidió un punto específico en esta búsqueda
        if espec.punto_referencia:
            # Si ya tenemos este punto guardado y coincide, úsalo
            if (destino.tiene_referencia()
                    and destino.punto_referencia_usado
                    and destino.punto_referencia_usado.lower() == espec.punto_referencia.lower()):
                ref = destino.coordenadas_referencia()
                if ref is not None:
                    return (ref, f"{espec.punto_referencia} (guardado)")

            # Geocodificar el punto específico
            coordenadas = self._geocodificar_punto(
                espec.punto_referencia, espec.ciudad, espec.pais
            )
            if coordenadas is not None and destino.id is not None:
                repositorio.actualizar_coordenadas_referencia(
                    destino.id, coordenadas[0], coordenadas[1], espec.punto_referencia
                )
            return (coordenadas, espec.punto_referencia)

        # 2. No hay punto específico: si ya hay referencia guardada de búsquedas previas, NO la usamos
        #    (el usuario no la pidió ahora). Usamos el centro.
        #    Esto evita mezclar distancias de "cerca del metro" con búsquedas genéricas.

        # 3. Centro de la ciudad ya guardado
        centro = destino.coordenadas()
        if centro is not None:
            return (centro, "centro de la ciudad")

        # 4. Geocodificar centro
        centro = self._geocodificar(espec.ciudad, espec.pais)
        if centro is not None and destino.id is not None:
            repositorio.actualizar_coordenadas(
                destino.id, centro[0], centro[1]
            )
        return (centro, "centro de la ciudad")

    def _completar_analisis(self, candidatos: list[Candidato]) -> None:
        repositorio = self._analisis_repo or AnalisisIARepository()
        guardados = repositorio.obtener_por_hospedajes(
            [_id_de(candidato) for candidato in candidatos]
        )
        for candidato in candidatos:
            candidato.analisis = guardados.get(_id_de(candidato))

        sin_analisis = [
            candidato for candidato in candidatos
            if candidato.analisis is None
        ]
        if not sin_analisis:
            return

        try:
            lote = self._obtener_evaluador().analizar(
                [candidato.hospedaje for candidato in sin_analisis]
            )
        except LoteIAError as error:
            # Sin análisis la búsqueda sigue: esos candidatos se puntúan con sus datos crudos.
            logger.warning("No se pudo analizar el lote de candidatos: %s", error)
            return

        esperados = {_id_de(candidato) for candidato in sin_analisis}
        por_hospedaje: dict[int, Analisis] = {}
        for item in lote.analisis:
            if item.hospedaje_id in esperados:
                # Si el modelo repite un id, gana la última respuesta válida.
                por_hospedaje[item.hospedaje_id] = Analisis.desde_ia(item)

        nuevos = list(por_hospedaje.values())
        if not nuevos:
            return

        ids_generados = repositorio.guardar_lote(nuevos)
        for analisis, id_generado in zip(nuevos, ids_generados, strict=True):
            analisis.id = id_generado

        guardados.update(por_hospedaje)
        for candidato in sin_analisis:
            candidato.analisis = guardados.get(_id_de(candidato))

    def _puntuar(self, candidatos: list[Candidato], espec: EspecificacionBusqueda) -> None:
        try:
            lote = self._obtener_evaluador().puntuar(
                [candidato.hospedaje for candidato in candidatos],
                {_id_de(candidato): candidato.analisis
                 for candidato in candidatos if candidato.analisis is not None},
                espec,
            )
        except LoteIAError as error:
            # Sin puntaje la búsqueda sigue: queda el orden local por calificación.
            logger.warning("No se pudo puntuar el lote de candidatos: %s", error)
            return

        puntuaciones = {puntuacion.hospedaje_id: puntuacion
                        for puntuacion in lote.puntuaciones}

        for candidato in candidatos:
            puntuacion = puntuaciones.get(_id_de(candidato))
            if puntuacion is None:
                logger.warning(
                    "Sin puntaje para %s; queda al final del ranking",
                    candidato.hospedaje.nombre,
                )
                continue
            candidato.score_calidad = puntuacion.score_calidad
            candidato.score_cumplimiento = puntuacion.score_cumplimiento
            candidato.requisitos_cumplidos = puntuacion.requisitos_cumplidos
            candidato.requisitos_faltantes = puntuacion.requisitos_faltantes

    def _obtener_evaluador(self) -> EvaluadorIA:
        if self._evaluador is None:
            self._evaluador = EvaluadorIA()
        return self._evaluador

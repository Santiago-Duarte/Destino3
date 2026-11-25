import argparse
import logging

from src.cli.prompts import (
    completar_especificacion,
    confirmar,
    formatear_ocupacion,
    formatear_presupuesto,
    pedir_frase,
)
from src.exceptions import Destino3Error

logger = logging.getLogger(__name__)


def crear_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        description="Busca hoteles con una frase y devuelve los 3 mejores candidatos",
    )


def _nombre_destino(espec) -> str:
    return f"{espec.ciudad}, {espec.pais}"


def _fechas(espec) -> str:
    if espec.fecha_entrada is None or espec.fecha_salida is None:
        return "fechas sin definir"
    return (
        f"{espec.fecha_entrada:%d/%m} → {espec.fecha_salida:%d/%m}"
        f" ({espec.noches()} noches)"
    )


def _precio_noche(hospedaje) -> str:
    if hospedaje.precio_noche is None:
        return "precio no disponible"
    return f"USD ${float(hospedaje.precio_noche):g}/noche"


def _calificacion(hospedaje) -> str:
    if hospedaje.calificacion is None:
        return "sin calificación"
    return f"{float(hospedaje.calificacion):g}"


def _imprimir(resultado) -> None:
    espec = resultado.especificacion
    print(f"\nBúsqueda: {_nombre_destino(espec)} | {_fechas(espec)} | {formatear_ocupacion(espec)}")
    print(f"Presupuesto: {formatear_presupuesto(espec)}")
    print(f"Preferencias: {espec.preferencias or 'ninguna'}")

    if not resultado.candidatos:
        print("\nNo se encontraron hoteles con esa búsqueda.")
        return

    mejores = resultado.mejores()
    if mejores:
        print(f"\nTOP {len(mejores)} de {len(resultado.candidatos)} candidatos\n")
        lista = mejores
    elif all(candidato.score_cumplimiento is None for candidato in resultado.candidatos):
        print("\nLa IA no pudo puntuar esta búsqueda. Candidatos por calificación:\n")
        lista = resultado.candidatos
    else:
        print("\nNingún hotel cumple con lo que pediste. Te muestro los candidatos ordenados")
        print("por cumplimiento con sus requisitos pendientes:\n")
        lista = resultado.candidatos

    for posicion, candidato in enumerate(lista, start=1):
        hospedaje = candidato.hospedaje
        print(f"{posicion}. {hospedaje.nombre} — {_precio_noche(hospedaje)}"
              f" — calificación {_calificacion(hospedaje)}")
        if candidato.score_cumplimiento is None:
            print("   Sin puntaje (la IA no respondió para este hotel)")
        else:
            print(f"   Cumplimiento {candidato.score_cumplimiento}/10 | "
                  f"calidad {candidato.score_calidad}/10")
            print(f"   Cumple: {', '.join(candidato.requisitos_cumplidos) or '—'}")
            print(f"   Falta: {', '.join(candidato.requisitos_faltantes) or '—'}")
        if candidato.analisis is not None:
            print(f"   {candidato.analisis.resumen_ejecutivo}")
            print(f"   Fuertes: {candidato.analisis.puntos_fuertes}")
            print(f"   Débiles: {candidato.analisis.puntos_debiles}")
        if hospedaje.url_reserva:
            print(f"   Reserva: {hospedaje.url_reserva}")
        print()


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    crear_parser().parse_args(argv)

    frase = pedir_frase()
    if frase is None:
        return 1

    from src.orchestrator.orquestador_integracion import OrquestadorIntegracion
    from src.services.interpretador_ia import InterpretadorIA

    try:
        espec = InterpretadorIA().interpretar(frase)

        inferidos = completar_especificacion(espec)
        if inferidos is None:
            return 1

        if inferidos:
            confirmado = confirmar(espec)
            if confirmado is None:
                return 1
            if not confirmado:
                print("Búsqueda cancelada.")
                return 0

        resultado = OrquestadorIntegracion().buscar(espec)
    except (ValueError, Destino3Error) as error:
        logger.error("%s", error)
        return 1
    except Exception as error:
        logger.error(
            "Falló la búsqueda: %s: %s",
            type(error).__name__,
            error,
        )
        logger.debug("Detalle inesperado", exc_info=True)
        return 1

    _imprimir(resultado)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

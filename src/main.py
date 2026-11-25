import argparse
import logging

from src.exceptions import Destino3Error

logger = logging.getLogger(__name__)


PREGUNTA_FRASE = (
    '¿Qué hoteles buscas? '
    '(ej. "hoteles en Medellin hasta 100 USD cerca del metro"): '
)


def crear_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        description="Busca hoteles con una frase y devuelve los 3 mejores candidatos",
    )


def _pedir_frase() -> str | None:
    """Pide la frase por consola hasta recibir una no vacía."""
    while True:
        try:
            frase = input(PREGUNTA_FRASE).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nNo se recibió ninguna frase.")
            return None

        if frase:
            return frase

        print("La frase no puede estar vacía. Inténtalo de nuevo.")


def _nombre_destino(espec) -> str:
    return f"{espec.ciudad}, {espec.pais}"


def _presupuesto(espec) -> str:
    if espec.presupuesto_max_noche is None:
        return "sin límite"
    return f"hasta USD ${espec.presupuesto_max_noche:g}/noche"


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
    print(f"\nBúsqueda: {_nombre_destino(espec)} | presupuesto: {_presupuesto(espec)}")
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

    frase = _pedir_frase()
    if frase is None:
        return 1

    from src.orchestrator.orquestador_integracion import OrquestadorIntegracion

    try:
        resultado = OrquestadorIntegracion().buscar_desde_frase(frase)
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

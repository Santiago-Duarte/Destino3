import argparse
import logging

logger = logging.getLogger(__name__)


def crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Busca hoteles con una frase y devuelve los 3 mejores candidatos",
    )
    parser.add_argument(
        "frase",
        help='Ej: "quiero hoteles en Medellin, Colombia hasta 100 USD cerca del metro"',
    )
    return parser


def _nombre_destino(espec) -> str:
    return f"{espec.ciudad}, {espec.pais}"


def _presupuesto(espec) -> str:
    if espec.presupuesto_max_noche is None:
        return "sin límite"
    return f"hasta USD ${espec.presupuesto_max_noche}/noche"


def _imprimir(resultado) -> None:
    espec = resultado.especificacion
    print(f"\nBúsqueda: {_nombre_destino(espec)} | presupuesto: {_presupuesto(espec)}")
    print(f"Preferencias: {espec.preferencias or 'ninguna'}")

    if not resultado.candidatos:
        print("\nNo se encontraron hoteles con esa búsqueda.")
        return

    mejores = resultado.mejores()
    if not mejores:
        print("\nNingún hotel cumple con lo que pediste. Te muestro los candidatos ordenados")
        print("por cumplimiento con sus requisitos pendientes:\n")
        lista = resultado.candidatos
    else:
        print(f"\nTOP {len(mejores)} de {len(resultado.candidatos)} candidatos\n")
        lista = mejores

    for posicion, candidato in enumerate(lista, start=1):
        hospedaje = candidato.hospedaje
        print(f"{posicion}. {hospedaje.nombre} — USD ${hospedaje.precio_noche}/noche"
              f" — calificación {hospedaje.calificacion}")
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
    argumentos = crear_parser().parse_args(argv)

    from src.orchestrator.orquestador_integracion import OrquestadorIntegracion

    try:
        resultado = OrquestadorIntegracion().buscar_desde_frase(argumentos.frase)
    except ValueError as error:
        logger.error(str(error))
        return 1
    except Exception as error:
        logger.error("Falló la búsqueda: tipo=%s", type(error).__name__)
        return 1

    _imprimir(resultado)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

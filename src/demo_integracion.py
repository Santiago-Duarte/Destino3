"""Smoke test manual del flujo real de búsqueda, IA y persistencia."""

import argparse
import logging
import os


logger = logging.getLogger(__name__)


def crear_parser() -> argparse.ArgumentParser:
    """Crea el parser de parámetros del demo manual."""
    parser = argparse.ArgumentParser(description="Ejecuta la integración real de Destino3")
    parser.add_argument("--ciudad", default="Medellin", help="Ciudad a buscar")
    parser.add_argument("--pais", default="Colombia", help="País de la ciudad")
    parser.add_argument(
        "--presupuesto-max",
        type=float,
        default=100.0,
        help="Presupuesto máximo por noche en USD",
    )
    parser.add_argument(
        "--preferencias",
        default="",
        help="Preferencias adicionales para la evaluación IA",
    )
    return parser


def ejecutar_demo(argumentos: argparse.Namespace) -> int:
    """Ejecuta el flujo real y registra hospedajes y evaluaciones persistidos."""
    if os.getenv("ENVIRONMENT") != "demo":
        logger.error("El demo de integración requiere ENVIRONMENT=demo.")
        return 1

    from src.config import settings
    from src.orchestrator.orquestador_integracion import OrquestadorIntegracion

    if not settings.SERPAPI_KEY or not settings.GEMINI_API_KEY:
        logger.warning(
            "Faltan credenciales de proveedores; configure las variables de entorno requeridas."
        )
        return 0

    try:
        orquestador = OrquestadorIntegracion()
        resultado = orquestador.ejecutar(
            argumentos.ciudad,
            argumentos.pais,
            argumentos.presupuesto_max,
            argumentos.preferencias,
        )
        if resultado == []:
            logger.info("La búsqueda no devolvió hospedajes.")
            return 0

        evaluaciones = orquestador.persistir_evaluaciones(resultado)
        logger.info("Hospedajes persistidos: %s", len(resultado.hospedajes))
        for hospedaje in resultado.hospedajes:
            logger.info(
                "Hospedaje id=%s nombre=%s precio_noche=%s",
                hospedaje.id,
                hospedaje.nombre,
                hospedaje.precio_noche,
            )

        logger.info("Evaluaciones persistidas: %s", len(evaluaciones))
        for evaluacion in evaluaciones:
            logger.info(
                "Evaluación id=%s hospedaje_id=%s score=%s",
                evaluacion.id,
                evaluacion.hospedaje_id,
                evaluacion.score_calidad_precio,
            )
        return 0
    except Exception as error:
        logger.error("Falló la ejecución del demo de integración: tipo=%s", type(error).__name__)
        return 1


def main() -> int:
    """Configura el logging y ejecuta el demo con argumentos de línea de comandos."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return ejecutar_demo(crear_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())

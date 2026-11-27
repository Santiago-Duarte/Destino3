"""Interacción por consola para completar la búsqueda."""

from datetime import date, timedelta

from src.cli.fechas import (
    error_de_fechas,
    formatear_fecha,
    parsear_fecha,
    proximo_fin_de_semana,
    validar_entrada,
    validar_estancia,
)
from src.models.busqueda import EspecificacionBusqueda
from src.models.hospedaje import Hospedaje

PREGUNTA_FRASE = (
    '¿Qué hoteles buscas? '
    '(ej. "hoteles en Medellin hasta 100 USD cerca del metro"): '
)

ADULTOS_POR_DEFECTO = 2
NINOS_POR_DEFECTO = 0
MAX_ADULTOS = 20
MAX_NINOS = 20
NOCHES_POR_DEFECTO = 2


def pedir_frase() -> str | None:
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


def formatear_presupuesto(espec: EspecificacionBusqueda) -> str:
    if espec.presupuesto_max_noche is None:
        return "sin límite"
    return f"hasta USD ${espec.presupuesto_max_noche:g}/noche"


def formatear_ocupacion(espec: EspecificacionBusqueda) -> str:
    adultos = espec.adultos if espec.adultos is not None else "?"
    ninos = espec.ninos if espec.ninos is not None else "?"
    texto = (
        f"{adultos} {'adulto' if adultos == 1 else 'adultos'}, "
        f"{ninos} {'niño' if ninos == 1 else 'niños'}"
    )
    if espec.mascotas is None:
        return texto + ", mascotas no especificadas"
    return texto + (", con mascotas" if espec.mascotas else ", sin mascotas")


def formatear_distancia(hospedaje: Hospedaje, punto_referencia: str = "centro") -> str | None:
    """Resumen legible de la distancia y los tiempos de un hospedaje."""
    if hospedaje.distancia_km is None:
        return None

    partes = [f"{hospedaje.distancia_km:.2f} km de {punto_referencia}"]
    if hospedaje.tiempo_auto_min is not None:
        partes.append(f"auto {hospedaje.tiempo_auto_min} min")
    if hospedaje.tiempo_transit_min is not None:
        partes.append(f"bus {hospedaje.tiempo_transit_min} min")
    if hospedaje.tiempo_walking_min is not None:
        partes.append(f"a pie {hospedaje.tiempo_walking_min} min")
    return " | ".join(partes)


def resumen(espec: EspecificacionBusqueda) -> str:
    noches = espec.noches()
    fechas = "fechas sin definir"
    if espec.fecha_entrada is not None and espec.fecha_salida is not None:
        fechas = (
            f"{formatear_fecha(espec.fecha_entrada)} → "
            f"{formatear_fecha(espec.fecha_salida)} ({noches} noches)"
        )

    lineas = [
        f"Destino: {espec.ciudad}, {espec.pais}",
        f"Fechas: {fechas}",
        f"Ocupación: {formatear_ocupacion(espec)}",
        f"Presupuesto: {formatear_presupuesto(espec)}",
    ]
    if espec.max_distancia_km is not None:
        punto = espec.punto_referencia_usado or "centro de la ciudad"
        lineas.append(f"Distancia máxima desde {punto}: {espec.max_distancia_km:g} km")
    if espec.preferencias:
        lineas.append(f"Preferencias: {espec.preferencias}")
    return "\n".join(lineas)


def completar_especificacion(
        espec: EspecificacionBusqueda,
        hoy: date | None = None,
) -> bool | None:
    """Pide lo que falte y devuelve si hubo datos inferidos.

    ``None`` significa que la persona interrumpió la entrada y no hay nada
    que buscar.
    """
    hoy = hoy or date.today()
    inferidos = False

    error_fechas = error_de_fechas(espec, hoy)
    if error_fechas is not None:
        if espec.fecha_entrada is not None and espec.fecha_salida is not None:
            print(error_fechas)
        print("Necesito las fechas de entrada y salida.")
        if not _pedir_fechas(espec, hoy):
            return None
        inferidos = True

    if espec.adultos is None:
        adultos = _pedir_entero("Adultos", ADULTOS_POR_DEFECTO, 1, MAX_ADULTOS)
        if adultos is None:
            return None
        espec.adultos = adultos
        inferidos = True

    if espec.ninos is None:
        ninos = _pedir_entero("Niños", NINOS_POR_DEFECTO, 0, MAX_NINOS)
        if ninos is None:
            return None
        espec.ninos = ninos
        inferidos = True

    if espec.mascotas is None:
        mascotas = _pedir_si_no("¿Viajan con mascotas? (s/n)", False)
        if mascotas is None:
            return None
        espec.mascotas = mascotas
        inferidos = True

    return inferidos


def confirmar(espec: EspecificacionBusqueda) -> bool | None:
    """Muestra el resumen y pide confirmación. ``None`` si se interrumpió."""
    print()
    print(resumen(espec))
    while True:
        try:
            respuesta = input("¿Buscar con estos datos? [S/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nNo se recibió confirmación.")
            return None

        if respuesta in ("", "s", "si", "sí"):
            return True
        if respuesta in ("n", "no"):
            return False
        print("Responde 's' o 'n'.")


def _pedir_fechas(espec: EspecificacionBusqueda, hoy: date) -> bool:
    """Pide entrada y salida hasta que la estancia sea válida."""
    viernes, _ = proximo_fin_de_semana(hoy)
    entrada_inicial = espec.fecha_entrada
    salida_inicial = espec.fecha_salida

    defecto_entrada = (
        entrada_inicial
        if entrada_inicial is not None and validar_entrada(entrada_inicial, hoy) is None
        else viernes
    )
    defecto_salida = (
        salida_inicial
        if salida_inicial is not None and salida_inicial > defecto_entrada
        else defecto_entrada + timedelta(days=NOCHES_POR_DEFECTO)
    )

    while True:
        entrada = _pedir_fecha("Entrada", defecto_entrada, hoy)
        if entrada is None:
            return False

        error = validar_entrada(entrada, hoy)
        if error is not None:
            print(error)
            continue

        if defecto_salida <= entrada:
            defecto_salida = entrada + timedelta(days=NOCHES_POR_DEFECTO)

        while True:
            salida = _pedir_fecha("Salida", defecto_salida, hoy)
            if salida is None:
                return False

            error = validar_estancia(entrada, salida)
            if error is None:
                espec.fecha_entrada = entrada
                espec.fecha_salida = salida
                return True
            print(error)


def _pedir_fecha(etiqueta: str, defecto: date, hoy: date) -> date | None:
    while True:
        try:
            texto = input(f"{etiqueta} [dd/mm] ({formatear_fecha(defecto)}): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nNo se recibieron las fechas.")
            return None

        if not texto:
            return defecto

        fecha = parsear_fecha(texto, hoy)
        if fecha is None:
            print("Fecha no válida: usa dd/mm o dd/mm/aaaa.")
            continue
        return fecha


def _pedir_entero(pregunta: str, defecto: int, minimo: int, maximo: int) -> int | None:
    while True:
        try:
            texto = input(f"{pregunta} [{defecto}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nNo se recibió la ocupación.")
            return None

        if not texto:
            return defecto

        try:
            valor = int(texto)
        except ValueError:
            print("Escribe un número entero.")
            continue

        if not minimo <= valor <= maximo:
            print(f"Debe estar entre {minimo} y {maximo}.")
            continue
        return valor


def _pedir_si_no(pregunta: str, defecto: bool) -> bool | None:
    defecto_texto = "s" if defecto else "n"
    while True:
        try:
            texto = input(f"{pregunta} [{defecto_texto}]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nNo se recibió la ocupación.")
            return None

        if not texto:
            return defecto
        if texto in ("s", "si", "sí"):
            return True
        if texto in ("n", "no"):
            return False
        print("Responde 's' o 'n'.")

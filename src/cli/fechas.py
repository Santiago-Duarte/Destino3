"""Reglas de fechas del CLI: parseo, valores por defecto y validación."""

from datetime import date, datetime, timedelta

from src.models.busqueda import EspecificacionBusqueda

MAX_NOCHES = 30
MAX_DIAS_ANTELACION = 365

_DIAS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")
_FORMATOS_COMPLETOS = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y")


def proximo_fin_de_semana(hoy: date) -> tuple[date, date]:
    """Viernes y domingo siguientes; si hoy es viernes, el de la semana entrante."""
    dias_hasta_viernes = (4 - hoy.weekday()) % 7
    if dias_hasta_viernes == 0:
        dias_hasta_viernes = 7
    entrada = hoy + timedelta(days=dias_hasta_viernes)
    return entrada, entrada + timedelta(days=2)


def formatear_fecha(fecha: date) -> str:
    return f"{_DIAS[fecha.weekday()]} {fecha:%d/%m}"


def parsear_fecha(texto: str, hoy: date) -> date | None:
    """Acepta dd/mm/aaaa, aaaa-mm-dd y dd/mm (infiere el año futuro más cercano)."""
    texto = texto.strip()
    if not texto:
        return None

    for formato in _FORMATOS_COMPLETOS:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue

    try:
        dia, mes = (int(parte) for parte in texto.split("/"))
        date(2000, mes, dia)  # año bisiesto: valida día y mes
    except ValueError:
        return None

    for anio in range(hoy.year, hoy.year + 5):
        try:
            candidata = date(anio, mes, dia)
        except ValueError:
            continue
        if candidata >= hoy:
            return candidata
    return None


def validar_entrada(entrada: date, hoy: date) -> str | None:
    if entrada < hoy:
        return "La entrada no puede ser anterior a hoy."
    if (entrada - hoy).days > MAX_DIAS_ANTELACION:
        return "La entrada no puede estar a más de un año."
    return None


def validar_estancia(entrada: date, salida: date) -> str | None:
    if salida <= entrada:
        return "La salida debe ser posterior a la entrada."
    if (salida - entrada).days > MAX_NOCHES:
        return f"La estancia no puede superar {MAX_NOCHES} noches."
    return None


def error_de_fechas(espec: EspecificacionBusqueda, hoy: date) -> str | None:
    """Primer problema de fechas, o ``None`` si la estancia es utilizable."""
    if espec.fecha_entrada is None or espec.fecha_salida is None:
        return "Faltan las fechas de entrada y salida."
    return (
        validar_entrada(espec.fecha_entrada, hoy)
        or validar_estancia(espec.fecha_entrada, espec.fecha_salida)
    )

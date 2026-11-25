from datetime import date

from pydantic import BaseModel


class EspecificacionBusqueda(BaseModel):
    """Lo que la persona pidió; el interpretador la extrae y el CLI la completa."""

    ciudad: str = ""
    pais: str = ""
    fecha_entrada: date | None = None
    fecha_salida: date | None = None
    adultos: int | None = None
    ninos: int | None = None
    mascotas: bool | None = None
    presupuesto_max_noche: float | None = None
    preferencias: str = ""

    def tiene_requisitos(self) -> bool:
        return self.presupuesto_max_noche is not None or bool(self.preferencias.strip())

    def noches(self) -> int | None:
        if self.fecha_entrada is None or self.fecha_salida is None:
            return None
        return (self.fecha_salida - self.fecha_entrada).days

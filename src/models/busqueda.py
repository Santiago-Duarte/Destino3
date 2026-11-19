from pydantic import BaseModel


class EspecificacionBusqueda(BaseModel):
    """Lo que la persona pidió en su frase; el interpretador la extrae y la valida."""

    ciudad: str = ""
    pais: str = ""
    presupuesto_max_noche: float | None = None
    preferencias: str = ""

    def tiene_requisitos(self) -> bool:
        return self.presupuesto_max_noche is not None or bool(self.preferencias.strip())

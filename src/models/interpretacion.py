from pydantic import BaseModel


class InterpretacionFrase(BaseModel):
    """Salida del modelo al leer la frase; las fechas llegan como texto ISO.

    Se separa de ``EspecificacionBusqueda`` para no exponer ``datetime.date``
    en el esquema que se envía a Gemini.
    """

    ciudad: str = ""
    pais: str = ""
    fecha_entrada: str | None = None
    fecha_salida: str | None = None
    adultos: int | None = None
    ninos: int | None = None
    mascotas: bool | None = None
    presupuesto_max_noche: float | None = None
    preferencias: str = ""

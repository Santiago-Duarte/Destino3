from pydantic import BaseModel, Field, field_validator


class AnalisisIAOutput(BaseModel):
    """Descripción intrínseca de un hotel; no depende de quién busca."""

    hospedaje_id: int
    resumen_ejecutivo: str
    puntos_fuertes: str
    puntos_debiles: str


class LoteAnalisisIA(BaseModel):
    analisis: list[AnalisisIAOutput]

    def hospedaje_ids(self) -> set[int]:
        return {analisis.hospedaje_id for analisis in self.analisis}

    def __len__(self) -> int:
        return len(self.analisis)


class PuntuacionIAOutput(BaseModel):
    """Qué tan bien le va este hotel a esta persona; se calcula por búsqueda y no se guarda."""

    hospedaje_id: int
    score_calidad: int = Field(ge=1, le=10)
    score_cumplimiento: int = Field(ge=1, le=10)
    requisitos_cumplidos: list[str] = Field(default_factory=list)
    requisitos_faltantes: list[str] = Field(default_factory=list)

    @field_validator("score_calidad", "score_cumplimiento", mode="before")
    @classmethod
    def _entero_sin_strings(cls, valor):
        """Acepta 8.0 pero rechaza "8", booleanos y decimales no enteros."""
        if isinstance(valor, bool):
            raise ValueError("El score debe ser un entero")
        if isinstance(valor, float):
            if not valor.is_integer():
                raise ValueError("El score debe ser un entero")
            return int(valor)
        if not isinstance(valor, int):
            raise ValueError("El score debe ser un entero")
        return valor


class LotePuntuacionesIA(BaseModel):
    puntuaciones: list[PuntuacionIAOutput]

    def hospedaje_ids(self) -> set[int]:
        return {puntuacion.hospedaje_id for puntuacion in self.puntuaciones}

    def __len__(self) -> int:
        return len(self.puntuaciones)

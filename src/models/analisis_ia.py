from pydantic import BaseModel, Field


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
    score_calidad: int = Field(ge=1, le=10, strict=True)
    score_cumplimiento: int = Field(ge=1, le=10, strict=True)
    requisitos_cumplidos: list[str] = []
    requisitos_faltantes: list[str] = []


class LotePuntuacionesIA(BaseModel):
    puntuaciones: list[PuntuacionIAOutput]

    def hospedaje_ids(self) -> set[int]:
        return {puntuacion.hospedaje_id for puntuacion in self.puntuaciones}

    def __len__(self) -> int:
        return len(self.puntuaciones)

## Estado

ACEPTADA

## Contexto

Destino3 necesita procesar automáticamente la respuesta de Gemini.

Una respuesta de texto libre obligaría a interpretar manualmente la salida.

## Decisión

Gemini debe devolver una respuesta JSON estructurada y validada mediante Pydantic.

La salida contiene la evaluación completa.

Ejemplo conceptual:

```json
{
  "id_temporal": 1,
  "resumen_ejecutivo": "...",
  "puntos_fuertes": "...",
  "puntos_debiles": "...",
  "score_calidad_precio": 8
}
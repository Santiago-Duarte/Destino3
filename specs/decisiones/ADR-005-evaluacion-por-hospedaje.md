## Estado

ACEPTADA

## Contexto

Destino3 necesita determinar el alcance de una evaluación de IA:

- ¿Una evaluación pertenece únicamente a un hospedaje?
- ¿O pertenece a un hospedaje dentro del contexto de una búsqueda?

## Decisión

Una evaluación pertenece **únicamente al hospedaje**.

### Justificación

1. **Evaluación vs Recomendación (ADR-003):** La evaluación representa "qué tan bueno es" un hospedaje (cualidades intrínsecas). La recomendación representa "qué posición ocupa" en una búsqueda (depende del contexto).

2. **Eficiencia:** Evita llamadas repetidas a Gemini para el mismo hospedaje en distintas búsquedas.

3. **Simplicidad:** Un hospedaje tiene una única evaluación persistente.

## Consecuencias

- El schema `evaluaciones_ia` mantiene la restricción `UNIQUE` en `hospedaje_id`.
- No se permite `busqueda_id` en la tabla de evaluaciones.
- Si un hospedaje cambia significativamente, la evaluación debe actualizarse explícitamente.

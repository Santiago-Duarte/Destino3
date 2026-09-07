# ADR-002 — Mapeo de IDs temporales

## Estado

ACEPTADA

## Contexto

Gemini necesita identificar los hospedajes recibidos en el prompt.

Los IDs reales de PostgreSQL no deben convertirse en una preocupación del proveedor externo.

## Decisión

Durante el procesamiento se utilizará un `id_temporal`.

El flujo será:

```text
Hospedaje
→ id_temporal
→ Gemini
→ respuesta
→ id_temporal
→ hospedaje real
→ hospedaje_id PostgreSQL
# Plan — Spec 005: MVP Planificador de Viaje

El plan está dividido en documentos cortos para revisarlos por separado. La **spec 005 sigue siendo la autoridad de los 12 RF**; los incrementos implementan el corte **V0** y citan los RF sin redefinirlos.

## Documentos base

1. [01. Arquitectura de módulos y modelo de datos](01-arquitectura-y-modelo-datos.md)
   - Componentes, capas y fronteras.
   - Entidades, relaciones y persistencia.
   - Decisiones técnicas del v1 completo.

2. [02. Estrategia de integración y pruebas](02-integracion-y-pruebas.md)
   - Integración con SerpAPI, Gemini y Places.
   - Degradación, CLI y errores del v1 completo.
   - Pirámide de tests y matriz RF → componente.

> **Alcance V0:** `01` y `02` describen el v1 completo. La implementación actual aplica los cortes de este documento: sin caché, sin Routes, sin evaluación ni itinerario con Gemini, y con una sola base de pruebas. Lo diferido se añade en V1 sin rehacer el núcleo.

## Ejecución por incrementos

3. [Tasks · índice general](tasks.md)
   - 59 tareas atómicas de ≤60 min con IDs locales.
   - Ocho gates de incremento y fase.
   - Criterios de aceptación V0.

| Incremento | Spec | Tasks | Fases | Gates | Esfuerzo |
|---|---|---|---|---|---|
| I1 · Fundaciones | [spec](incrementos/01-fundaciones/spec.md) | [21](incrementos/01-fundaciones/tasks.md) | 0–1 | `I1-011`, `I1-021` | 11,9 h |
| I2 · Primera frase | [spec](incrementos/02-primera-frase/spec.md) | [21](incrementos/02-primera-frase/tasks.md) | 2–4 | `I2-008`, `I2-021` | 14,4 h |
| I3 · Decisión | [spec](incrementos/03-decision/spec.md) | [8](incrementos/03-decision/tasks.md) | 5–6 | `I3-005`, `I3-008` | 5,3 h |
| I4 · Plan completo | [spec](incrementos/04-plan-completo/spec.md) | [10](incrementos/04-plan-completo/tasks.md) | 7–8 | `I4-005`, `I4-010` | 7,8 h |
| **Total** | | **60** | | | **39,4 h** |

## Qué se difiere a V1

- Caché `cache_api`/`lugares`, TTL y respaldo vencido.
- Google Routes, tiempo real a pie y tiempo en auto.
- Evaluación de hoteles con Gemini, citas y `evaluaciones_ia`.
- Itinerario con Gemini y validador de citas.
- Matriz de degradación de 14 filas.
- Entornos `demo`/`production`, roles y migración aditiva.
- Códigos de salida `2`/`3`/`130` y detección de TTY.

## Estado

**V0 listo para ejecución desde I1.** Cada incremento se aprueba al cerrar su gate. La 005 no se modifica: los incrementos solo citan sus RF y declaran qué parte queda diferida.

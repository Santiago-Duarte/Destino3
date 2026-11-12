# Plan — Spec 005: MVP Planificador de Viaje

El plan quedó dividido en dos documentos para que cada uno sea revisable por separado:

1. [01. Arquitectura de módulos y modelo de datos](01-arquitectura-y-modelo-datos.md)
   - Componentes, capas, fronteras.
   - Entidades, relaciones y persistencia.
   - Decisiones técnicas con alternativa descartada y trade-off.

2. [02. Estrategia de integración y pruebas](02-integracion-y-pruebas.md)
   - Integración con SerpAPI, Gemini, Places y Routes.
   - Caché, degradación, CLI y errores.
   - Pirámide de tests, matriz RF → componente y secuencia de implementación.

3. [Tasks](tasks.md)
   - 114 tareas atómicas de ≤60 min en orden de dependencia.
   - Cada tarea declara su RF y un criterio «Hecho cuando» verificable.
   - Nueve gates de fase; la Fase 0 deja la suite en verde.

**Estado:** el documento 01 está listo para revisión. El documento 02 queda como propuesta separada para el visto bueno de integración y pruebas. El desglose de tareas está listo para ejecución desde la Fase 0.

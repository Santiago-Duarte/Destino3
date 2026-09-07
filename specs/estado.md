# Estado Actual — Destino3

## Resumen

Destino3 se encuentra actualmente trabajando en la integración de la Fase 3.

Las funcionalidades principales de persistencia, búsqueda externa y evaluación IA existen de forma separada, pero todavía no están conectadas en un flujo completo.

---

## Fases

| Fase | Estado |
|---|---|
| Fase 1 | COMPLETADA |
| Fase 2 | COMPLETADA |
| Fase 3 | PARCIALMENTE COMPLETADA |
| Fase 4 | PENDIENTE |
| Fase 5 | NO INICIADA |
| Fase 6 | NO INICIADA |
| Fase 7 | NO INICIADA |

---

## Base de datos

Estado: COMPLETADO.

Existe un esquema PostgreSQL con las entidades necesarias para el roadmap actual.

---

## Modelos

Estado: PARCIAL.

Existen modelos Python para parte de las entidades.

Faltan modelos propios para entidades que actualmente todavía dependen de estructuras de Services.

---

## Repositories

Estado: PARCIAL.

Existen repositories para varias entidades.

Pendientes principales:

- completar operaciones necesarias de búsqueda;
- eliminar dependencias hacia Services;
- completar repositories de entidades que todavía no tienen uno.

---

## SerpAPI

Estado: COMPLETADO.

La integración permite obtener hospedajes y transformarlos a modelos de dominio.

Existe una responsabilidad adicional relacionada con archivos de prueba que deberá eliminarse.

---

## Gemini

Estado: COMPLETADO.

Gemini recibe candidatos y devuelve una respuesta estructurada validada con Pydantic.

La respuesta utiliza `id_temporal` para conservar la relación entre candidato y evaluación.

---

## Integración

Estado: EN PROGRESO.

Todavía no existe un flujo único:

```text
búsqueda
→ evaluación
→ persistencia
→ recomendación
→ respuesta
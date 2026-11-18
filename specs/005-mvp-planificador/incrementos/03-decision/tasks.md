# Tasks — I3 · Decisión (V0)

Objetivo del incremento: filtrar por cercanía y presupuesto, y elegir un top 3 con reseñas reales sin evaluación IA.

- Spec del incremento: [`spec.md`](spec.md)
- Requisitos: [`../../spec.md`](../../spec.md) (los RF se citan, no se redefinen)
- Plan técnico: [`../../01-arquitectura-y-modelo-datos.md`](../../01-arquitectura-y-modelo-datos.md) y [`../../02-integracion-y-pruebas.md`](../../02-integracion-y-pruebas.md)
- Índice general: [`../../tasks.md`](../../tasks.md)

## Convenciones

- IDs locales del incremento (`I3-NNN`); las dependencias de incrementos anteriores se citan con su ID completo.
- Cada tarea dura **≤ 60 minutos**, declara su **RF** y tiene un **Hecho cuando** binario y verificable.
- `Depende` lista solo la dependencia técnica que bloquea, no todas las anteriores.
- Prohibido marcar tests como `skip` para pasar o tocar `production` desde la suite.

## Resumen

| Fase | Tasks | Min |
|---|---|---|
| 5. Distancias y presupuesto | 5 | 200 |
| 6. Reseñas y top 3 | 3 | 120 |
| **Total** | **8** | **320** |

**Gates del incremento:** `I3-005`, `I3-008`

---

## Fase 5 — Distancias y presupuesto (I3)

- [ ] **I3-001 · `calculador_distancias` con haversine** — 45 min · RF-6 · Depende: I1-013
  - **Hecho cuando:** `python3 -m pytest test/test_calculador_distancias.py -q` devuelve `0 failed`; 1 km se convierte en 13 minutos a 80 m/min; cada `Distancia` queda marcada como estimación y no se llama a ninguna API de rutas.

- [ ] **I3-002 · `reglas_cercania` con escalera 10/20/30/45/60** — 45 min · RF-6 · Depende: I3-001
  - **Hecho cuando:** `python3 -c "from src.orchestrator.reglas_cercania import ampliar_nivel; print(ampliar_nivel(20), ampliar_nivel(60))"` imprime `30 None` y `python3 -m pytest test/test_reglas_cercania.py -q` devuelve `0 failed` con los 5 niveles, ampliación con aviso, 3 más cercanos en el tope y descarte de hoteles sin distancia.

- [ ] **I3-003 · `reglas_presupuesto`** — 45 min · RF-7 · Depende: I1-013
  - **Hecho cuando:** `python3 -c "from src.orchestrator.reglas_presupuesto import cabe; print(cabe(2000000, 2000000), cabe(2000001, 2000000))"` imprime `True False` y `python3 -m pytest test/test_reglas_presupuesto.py -q` devuelve `0 failed` con total antes de impuestos, solo precio por noche, empate exacto, ninguno cabe (3 más baratos + excedente) y moneda distinta.

- [ ] **I3-004 · `ranking` determinista** — 35 min · RF-8 · Depende: I1-013
  - **Hecho cuando:** `python3 -c "from src.orchestrator.ranking import ordenar; print(ordenar([{'calificacion':4.2,'precio_total':300,'minutos':5},{'calificacion':4.8,'precio_total':400,'minutos':9}])[0]['calificacion'])"` imprime `4.8` y `python3 -m pytest test/test_ranking.py -q` devuelve `0 failed` con calificación desc, precio asc y distancia asc.

- [ ] **I3-005 · Gate Fase 5: cercanía y presupuesto integrados** — 30 min · RF-6, RF-7 · Depende: I3-001–I3-004
  - **Hecho cuando:** `python3 -m pytest test/test_flujo_cercania_presupuesto.py -q` devuelve `0 failed` con un hotel fuera de minutos descartado y uno que excede el presupuesto fuera del top 3.

---

## Fase 6 — Reseñas y top 3 (I3)

- [ ] **I3-006 · `buscador_resenas` sin autor** — 45 min · RF-8 · Depende: I2-003, I2-005
  - **Hecho cuando:** `python3 -m pytest test/test_buscador_resenas.py -q` devuelve `0 failed` y una reseña mapeada no contiene `autor`; cubre hotel sin `property_token`, hotel sin reseñas y fallo del proveedor.

- [ ] **I3-007 · Finalistas y top 3 con reseñas crudas** — 45 min · RF-8 · Depende: I3-004, I3-006
  - **Hecho cuando:** `python3 -m pytest test/test_top3.py -q` devuelve `0 failed`; se toman hasta 5 finalistas, el top 3 sale ordenado por el ranking determinista, cada hotel muestra sus reseñas reales o «no verificado» y no se llama a Gemini.

- [ ] **I3-008 · Gate Fase 6: top 3 con evidencia real** — 30 min · RF-8 · Depende: I3-006–I3-007
  - **Hecho cuando:** `python3 -m pytest test/test_flujo_top3.py -q` devuelve `0 failed`; el top 3 tiene reseñas o «no verificado» y no existe tabla ni escritura de `evaluaciones_ia`.

---

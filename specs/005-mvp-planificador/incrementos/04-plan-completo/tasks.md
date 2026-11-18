# Tasks — I4 · Plan completo (V0)

Objetivo del incremento: armar el itinerario, presentar el plan completo y manejar fallos sin inventar datos.

- Spec del incremento: [`spec.md`](spec.md)
- Requisitos: [`../../spec.md`](../../spec.md) (los RF se citan, no se redefinen)
- Plan técnico: [`../../01-arquitectura-y-modelo-datos.md`](../../01-arquitectura-y-modelo-datos.md) y [`../../02-integracion-y-pruebas.md`](../../02-integracion-y-pruebas.md)
- Índice general: [`../../tasks.md`](../../tasks.md)

## Convenciones

- IDs locales del incremento (`I4-NNN`); las dependencias de incrementos anteriores se citan con su ID completo.
- Cada tarea dura **≤ 60 minutos**, declara su **RF** y tiene un **Hecho cuando** binario y verificable.
- `Depende` lista solo la dependencia técnica que bloquea, no todas las anteriores.
- Prohibido marcar tests como `skip` para pasar o tocar `production` desde la suite.

## Resumen

| Fase | Tasks | Min |
|---|---|---|
| 7. Lugares e itinerario | 5 | 250 |
| 8. Cierre | 5 | 215 |
| **Total** | **10** | **465** |

**Gates del incremento:** `I4-005`, `I4-010`

---

## Fase 7 — Lugares e itinerario (I4)

- [ ] **I4-001 · `buscador_lugares` con Nearby Search y umbrales** — 55 min · RF-9 · Depende: I1-013, I2-016
  - **Hecho cuando:** `python3 -m pytest test/test_buscador_lugares.py -q` devuelve `0 failed` con radio de 1.600 m, `rankPreference=DISTANCE`, ampliación a 2.400 m, exclusión de cerrados, sin nombre, sin coordenadas, alojamientos y agencias, y detección de restaurantes.

- [ ] **I4-002 · `planificador_itinerario` determinista** — 50 min · RF-10 · Depende: I3-002
  - **Hecho cuando:** `python3 -m pytest test/test_planificador_itinerario.py -q` devuelve `0 failed` con bloques de mañana, tarde y noche; día de llegada sin mañana; día de salida solo con mañana; sin repetir lugares; restaurante en la noche.

- [ ] **I4-003 · `orchestrator/planificador` con el pipeline completo** — 60 min · RF-11 · Depende: I2-021, I3-008, I4-001
  - **Hecho cuando:** `python3 -m pytest test/test_pipeline_completo.py -q` devuelve `0 failed` con una frase completa y produce top 3, itinerario, links y comparación de presupuesto.

- [ ] **I4-004 · `cli/presentador` completo** — 50 min · RF-11 · Depende: I4-003
  - **Hecho cuando:** `python3 -m pytest test/test_presentador.py -q` devuelve `0 failed` y la salida contiene top 3, itinerario, links, mapa, presupuesto en COP y la atribución «Google Maps».

- [ ] **I4-005 · Gate Fase 7: presentador y plan parcial** — 35 min · RF-11 · Depende: I4-004
  - **Hecho cuando:** `python3 -m pytest test/test_presentador.py -q` cubre plan completo, sin itinerario (parcial con razón), link faltante y moneda distinta, con `0 failed`.

---

## Fase 8 — Cierre (I4)

- [ ] **I4-006 · Manejo de errores por etapa** — 45 min · RF-12 · Depende: I4-003
  - **Hecho cuando:** `python3 -m pytest test/test_errores_etapas.py -q` devuelve `0 failed`; el fallo de cada proveedor agrega una advertencia visible; sin hoteles se aborta con mensaje; sin Places el plan es parcial; sin Gemini se usa el normalizador o se pregunta; ningún caso inventa datos.

- [ ] **I4-007 · `main.py` con flujo completo y códigos 0/1** — 45 min · RF-11, RF-12 · Depende: I4-003, I4-006
  - **Hecho cuando:** `python3 -m pytest test/test_main_flujo.py -q` devuelve `0 failed` con código `0` para plan completo o parcial y `1` para entrada o configuración inválida.

- [ ] **I4-008 · Smoke manual en la base de pruebas** — 60 min · RF-11 · Depende: I4-007
  - **Hecho cuando:** una ejecución real con 2 adultos, 2 niños, 3 días y 2 noches termina con código `0`, muestra top 3 con reseñas, itinerario, links, distancias con aviso de estimación y presupuesto, y la evidencia queda anotada en `specs/005-mvp-planificador/smoke.md`.

- [ ] **I4-009 · README con alcance, atribuciones y credenciales** — 35 min · RF-11 · Depende: I4-007
  - **Hecho cuando:** `grep -c "Google Maps\|términos\|privacidad\|GOOGLE_MAPS_API_KEY\|ENVIRONMENT" README.md` devuelve al menos `5` y no aparece ninguna clave real.

- [ ] **I4-010 · Gate final: suite y criterios V0** — 30 min · RF-1–RF-12 · Depende: I1-021, I2-021, I3-008, I4-005
  - **Hecho cuando:** `python3 -m pytest test/ -q` devuelve `0 failed, 0 errors`, los criterios V0 de `tasks.md` quedan marcados y `plan.md` refleja el estado final.

---

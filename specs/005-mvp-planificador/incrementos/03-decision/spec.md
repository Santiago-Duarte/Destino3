# Spec — I3 · Decisión (V0)

- **Incremento:** I3
- **Fases:** 5 (distancias y presupuesto) y 6 (reseñas y top 3)
- **Tasks:** 8 (`I3-001`–`I3-008`)
- **Esfuerzo:** 320 min ≈ 5,3 h
- **Depende de:** I2 cerrado (`I2-021`)
- **RF que cubre en V0:** RF-6 (parcial, sin tiempo en auto), RF-7, RF-8 (parcial, sin evaluación IA), RF-12 (parcial)
- **Spec madre:** [`../../spec.md`](../../spec.md) — los RF se citan, no se redefinen.
- **Diferido a V1:** Routes real, tiempo en auto, evaluación Gemini con citas, validador de citas e `evaluaciones_ia`.

## 1. Objetivo

Convertir una lista de hoteles en una decisión: top 3 que cumplen los minutos caminando, caben en el presupuesto y muestran reseñas reales.

## 2. Alcance

- Distancia en línea recta (haversine) convertida a minutos a pie a 80 m/min, con aviso de estimación.
- Escalera 10/20/30/45/60, ampliación con aviso y 3 más cercanos en el tope.
- Comparación contra el total antes de impuestos, empate exacto y 3 más baratos con excedente.
- Reseñas de SerpAPI sin autor, mostradas tal cual.
- Ranking determinista: calificación desc, precio asc, distancia asc.

## 3. Demo al cerrar

```text
Top 3 · Santa Marta
1. Hotel A — $1.850.000 COP · 12 min a pie (estimación)
   «...» — reseña real
2. Hotel B — $1.920.000 COP · 18 min a pie (estimación)
3. Hotel C — no verificado (sin reseñas)
Presupuesto: $2.000.000 · cabe, sobran $150.000
```

## 4. Criterios de aceptación

- [ ] `I3-005`: un hotel fuera de minutos se descarta y uno que excede el presupuesto sale del top 3.
- [ ] `I3-008`: el top 3 muestra reseñas reales o «no verificado» sin evaluación IA.
- [ ] Todo tiempo a pie lleva la advertencia de estimación.
- [ ] No se llama a Routes ni a Gemini en este incremento.
- [ ] Sin evaluación IA, el ranking es calificación desc, precio asc, distancia asc.

## 5. Fuera de alcance (V1)

- Rutas reales y tiempo en auto.
- Evaluación de hoteles con Gemini.
- Validación de citas textuales e `id_temporal`.
- Búsqueda de lugares e itinerario.

## 6. Riesgos

| Riesgo | Mitigación |
|---|---|
| Haversine subestima el camino real | 80 m/min y aviso de estimación en cada tiempo |
| Sin reseñas o sin `property_token` | El hotel se marca «no verificado» |
| Ningún hotel cabe | 3 más baratos del conjunto con distancia y excedente |
| Moneda distinta de COP | Se muestra y no se compara con el presupuesto |

## 7. Trazabilidad

| RF | Tasks |
|---|---|
| RF-6 | `I3-001`, `I3-002` |
| RF-7 | `I3-003` |
| RF-8 | `I3-004`, `I3-006`, `I3-007` |
| RF-12 | `I3-005`, `I3-008` |

## 8. Definición de terminado

El incremento termina cuando `I3-008` está marcado: top 3 filtrado por distancia y presupuesto, con reseñas reales y sin evaluación IA.

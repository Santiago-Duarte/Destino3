# Spec — I4 · Plan completo (V0)

- **Incremento:** I4
- **Fases:** 7 (lugares e itinerario) y 8 (cierre)
- **Tasks:** 10 (`I4-001`–`I4-010`)
- **Esfuerzo:** 465 min ≈ 7,8 h
- **Depende de:** I3 cerrado (`I3-008`)
- **RF que cubre en V0:** RF-9, RF-10 (parcial, determinista), RF-11, RF-12 (parcial)
- **Spec madre:** [`../../spec.md`](../../spec.md) — los RF se citan, no se redefinen.
- **Diferido a V1:** itinerario con Gemini, matriz de degradación, caché, códigos `2`/`3`/`130` y smoke en `demo_db`.

## 1. Objetivo

Entregar el plan completo: lugares y restaurantes cerca del hotel, itinerario día a día y presentación final, con degradación simple y sin inventar datos.

## 2. Alcance

- Places Nearby Search con umbral de 20 minutos (1.600 m) y ampliación a 30 (2.400 m).
- Planificador de itinerario determinista sobre la lista cerrada de lugares.
- Pipeline completo, presentador final y códigos de salida `0`/`1`.
- Manejo de errores por etapa con advertencias visibles.
- Smoke manual en la base de pruebas y cierre documental.

## 3. Demo al cerrar

```text
Plan completo · Santa Marta · 3 días / 2 noches
Hotel recomendado: Hotel A — $1.850.000 COP
Itinerario
  Día 1 · llegada: tarde — Parque de los Novios · noche — Restaurante X
  Día 2: mañana — Playa Blanca · tarde — Museo Y · noche — Restaurante Z
  Día 3 · salida: mañana — Café W
Presupuesto: cabe, sobran $150.000
Avisos: impuestos no incluidos · distancias estimadas · Google Maps
```

## 4. Criterios de aceptación

- [ ] `I4-005`: plan completo, plan parcial sin itinerario y moneda distinta se presentan correctamente.
- [ ] `I4-010`: suite en verde y criterios V0 marcados.
- [ ] Ningún lugar del itinerario existe fuera de la lista consultada.
- [ ] Cada fallo de proveedor agrega una advertencia y no inventa datos.
- [ ] El smoke real en la base de pruebas termina con código `0` y evidencia anotada.

## 5. Fuera de alcance (V1)

- Itinerario generado por Gemini.
- Matriz de degradación de 14 filas y respaldo de caché vencida.
- Códigos de salida `2`, `3` y `130`, y detección de TTY.
- Smoke en `demo_db` y `production`.

## 6. Riesgos

| Riesgo | Mitigación |
|---|---|
| Places cambia sus campos | Servicio encapsulado, campos mínimos y fixtures |
| Muchas llamadas a Places | Un radio, `maxResultCount=20` y sin caché en V0 |
| Itinerario con lugares lejanos | Solo se usan lugares de la lista consultada |
| Clave de Google filtrada | `.env` gitignored, redacción en logs y restricción por API |

## 7. Trazabilidad

| RF | Tasks |
|---|---|
| RF-9 | `I4-001` |
| RF-10 | `I4-002` |
| RF-11 | `I4-003`–`I4-005`, `I4-008`, `I4-009` |
| RF-12 | `I4-006`, `I4-007`, `I4-010` |

## 8. Definición de terminado

El incremento termina cuando `I4-010` está marcado: plan completo o parcial presentado, errores por etapa avisados y smoke real documentado.

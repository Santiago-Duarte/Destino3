# Tasks — Spec 005: MVP Planificador de Viaje (V0)

Índice de ejecución del corte V0. Los requisitos completos viven en [`spec.md`](spec.md); el plan técnico de referencia en [`01`](01-arquitectura-y-modelo-datos.md) y [`02`](02-integracion-y-pruebas.md). Cada incremento tiene su propio spec y su lista de tareas con IDs locales.

> **Alcance V0:** una frase → hoteles reales en COP → top 3 por cercanía y presupuesto → lugares e itinerario → presentación en terminal. Sin caché, sin Routes, sin evaluación ni itinerario con Gemini, y con una sola base de pruebas. Lo diferido está en la tabla de V1.

## Incrementos

| Incremento | Fases | Tasks | Min | Gates | Demo al cerrar |
|---|---|---|---|---|---|
| [I1 · Fundaciones](incrementos/01-fundaciones/spec.md) | 0–1 | [21](incrementos/01-fundaciones/tasks.md) | 715 | `I1-011`, `I1-021` | Suite verde, base de pruebas con 2 tablas y repositorios con `upsert` |
| [I2 · Primera frase](incrementos/02-primera-frase/spec.md) | 2–4 | [21](incrementos/02-primera-frase/tasks.md) | 865 | `I2-008`, `I2-021` | Frase → solicitud validada → hoteles reales en COP |
| [I3 · Decisión](incrementos/03-decision/spec.md) | 5–6 | [8](incrementos/03-decision/tasks.md) | 320 | `I3-005`, `I3-008` | Top 3 por cercanía, presupuesto y reseñas crudas |
| [I4 · Plan completo](incrementos/04-plan-completo/spec.md) | 7–8 | [10](incrementos/04-plan-completo/tasks.md) | 465 | `I4-005`, `I4-010` | Itinerario, presentación final y errores avisados |
| **Total** | | **60** | **2.365 min ≈ 39,4 h** | | |

## Qué se difiere a V1

| Diferido | Por qué no entra en V0 |
|---|---|
| Caché `cache_api`/`lugares`, TTL y respaldo vencido | No cambia lo que el usuario ve en una ejecución |
| Google Routes y tiempo en auto | Haversine + 80 m/min basta para validar cercanía |
| Evaluación de hoteles con Gemini y `evaluaciones_ia` | El ranking determinista y las reseñas crudas ya deciden |
| Itinerario con Gemini y validador de citas | El planificador determinista usa la misma lista cerrada |
| Matriz de degradación de 14 filas | `try/except` por etapa + advertencia cubre el MVP |
| Entornos `demo`/`production`, roles y migración aditiva | Una base de pruebas es suficiente para V0 |
| Códigos `2`/`3`/`130` y detección de TTY | `0`/`1` alcanza para el flujo lineal |

## Cómo se encadenan

```text
I1-001 … I1-021  (gate I1-021)
    → I2-001 … I2-021  (gate I2-021)
    → I3-001 … I3-008  (gate I3-008)
    → I4-001 … I4-010  (gate I4-010)
```

Cada gate exige el incremento anterior cerrado. Un incremento no empieza con el gate anterior en rojo.

## Convenciones

- **IDs:** locales por incremento (`I1-NNN`). Las dependencias de incrementos anteriores se citan con su ID completo.
- **Duración:** cada tarea dura **≤ 60 minutos**.
- **RF:** toda tarea declara el RF que cubre; los de soporte se marcan `RF-12 (soporte)`.
- **Hecho cuando:** siempre es un comando, un conteo o una consulta con resultado esperado.
- **Gates:** `I1-011`, `I1-021`, `I2-008`, `I2-021`, `I3-005`, `I3-008`, `I4-005`, `I4-010`. No se saltan.
- **Prohibido:** marcar tests como `skip` para pasar, borrar aserciones válidas o tocar `production` desde la suite.
- **BD:** PostgreSQL escucha en `localhost:5433`; los tests usan `destino3_test_db` y deben quedar sin `skipped` de `BaseDBTestCase`.

## Criterios de aceptación V0

- [ ] Frase completa produce plan con top 3, itinerario, links y presupuesto sin preguntas extra.
- [ ] Frase incompleta pregunta solo lo faltante y no consulta proveedores antes de completar.
- [ ] Fechas y presupuestos inválidos se rechazan y se repreguntan.
- [ ] Todo hotel mostrado cumple los minutos o el plan declara la ampliación o los 3 más cercanos.
- [ ] Cada reseña mostrada es real o el hotel se marca «no verificado».
- [ ] Ningún lugar del itinerario carece de correspondencia en la lista consultada.
- [ ] Ante el fallo de un proveedor, el plan agrega una advertencia y no inventa datos.
- [ ] La suite queda en verde y no aparecen credenciales en salida ni registros.

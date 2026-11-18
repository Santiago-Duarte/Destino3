# Spec — I1 · Fundaciones (V0)

- **Incremento:** I1
- **Fases:** 0 (puesta a cero) y 1 (dominio y datos)
- **Tasks:** 21 (`I1-001`–`I1-021`)
- **Esfuerzo:** 715 min ≈ 11,9 h
- **Depende de:** spec 004 (esquema base)
- **RF que cubre en V0:** RF-1, RF-3, RF-5, RF-7 (parcial), RF-12 (soporte)
- **Spec madre:** [`../../spec.md`](../../spec.md) — los RF se citan, no se redefinen.
- **Diferido a V1:** caché (`cache_api`, `lugares`), evaluación IA persistida, migración aditiva y entornos `demo`/`production`.

## 1. Objetivo

Dejar el repositorio en verde, una única base de pruebas con el esquema mínimo y el dominio necesario para buscar y persistir hoteles.

## 2. Alcance

- Reparar la suite y el harness de base de datos.
- Alinear `.env` y `.env.example` con PostgreSQL en `localhost:5433` y `ENVIRONMENT=testing`.
- Crear `destino3_test_db` y su rol con `operacion/bootstrap_bd.py`.
- Modelos mínimos: fechas, solicitud, destino, hospedaje, reseña, lugar, distancia, itinerario y plan.
- Esquema con dos tablas: `destinos` y `hospedajes`.
- Repositorios con `upsert` para destinos y hospedajes.
- Retirar los módulos y tests de evaluación IA, atracciones y búsqueda antigua que no forman parte de V0.

## 3. Demo al cerrar

```bash
python3 -m pytest test/ -q
set -a; source .env; set +a
psql -h localhost -p 5433 -U "$DB_ADMIN_USER" -d destino3_test_db -c "\dt"
```

Debe mostrar la suite en verde, sin tests saltados, y las tablas `destinos` y `hospedajes` en la base de pruebas.

## 4. Criterios de aceptación

- [ ] `I1-011`: suite con `0 failed, 0 errors, 0 skipped`.
- [ ] `I1-021`: la base de pruebas solo tiene `destinos` y `hospedajes` y la suite queda en verde.
- [ ] No existen `cache_api`, `lugares`, `evaluaciones_ia` ni `atracciones`.
- [ ] Dos guardados del mismo hotel dejan una sola fila.
- [ ] Ningún módulo fuera de `src/repositories/` ejecuta SQL.

## 5. Fuera de alcance (V1)

- Caché con TTL y respaldo vencido.
- Evaluación IA y tabla `evaluaciones_ia`.
- Rutas reales y tiempos en auto.
- Migración aditiva y entornos `demo`/`production`.

## 6. Riesgos

| Riesgo | Mitigación |
|---|---|
| PostgreSQL no escucha en 5433 | `I1-005` valida la conexión antes de seguir |
| `operacion/` no existe en el repo | `I1-004` la crea como primer artefacto operacional |
| Credenciales de prueba inconsistentes | El bootstrap lee `DB_TEST_USER` y `DB_TEST_PASSWORD` de `.env` |
| Esquema con tablas heredadas | `I1-017` verifica que solo existan las dos tablas V0 |
| Código y tests de evaluación fuera de V0 | `I1-020` los retira y deja la colección sin errores |

## 7. Trazabilidad

| RF | Tasks |
|---|---|
| RF-1 | `I1-012`, `I1-013`, `I1-018` |
| RF-3 | `I1-012` |
| RF-5, RF-7 | `I1-013`, `I1-015`, `I1-019` |
| RF-12 | `I1-001`–`I1-011`, `I1-015`–`I1-021` |

## 8. Definición de terminado

El incremento termina cuando `I1-021` está marcado: suite en verde, base de pruebas con dos tablas, repositorios con `upsert` probados y módulos fuera de V0 retirados.

# Tasks — I1 · Fundaciones (V0)

Objetivo del incremento: dejar el repositorio en verde, una base de pruebas con el esquema mínimo y los repositorios de destinos y hospedajes.

- Spec del incremento: [`spec.md`](spec.md)
- Requisitos: [`../../spec.md`](../../spec.md) (los RF se citan, no se redefinen)
- Plan técnico: [`../../01-arquitectura-y-modelo-datos.md`](../../01-arquitectura-y-modelo-datos.md) y [`../../02-integracion-y-pruebas.md`](../../02-integracion-y-pruebas.md)
- Índice general: [`../../tasks.md`](../../tasks.md)

## Convenciones

- IDs locales del incremento (`I1-NNN`); las dependencias de incrementos anteriores se citan con su ID completo.
- Cada tarea dura **≤ 60 minutos**, declara su **RF** y tiene un **Hecho cuando** binario y verificable.
- `Depende` lista solo la dependencia técnica que bloquea, no todas las anteriores.
- Prohibido marcar tests como `skip` para pasar o tocar `production` desde la suite.
- Los comandos con `psql` asumen `set -a; source .env; set +a` y `DB_ADMIN_USER` definido.

## Resumen

| Fase | Tasks | Min |
|---|---|---|
| 0. Puesta a cero | 11 | 290 |
| 1. Dominio y datos | 10 | 425 |
| **Total** | **21** | **715** |

**Gates del incremento:** `I1-011`, `I1-021`

---

## Fase 0 — Puesta a cero (I1)

- [ ] **I1-001 · Reparar el harness de base de datos** — 40 min · RF-12 (soporte) · Depende: —
  - **Hecho cuando:** `python3 -m pytest test/ -q --continue-on-collection-errors` reporta `0 errors` en la colección y `grep -c "usuarios\|busqueda\|recomendacion" test/db_test_case.py` devuelve `0`.

- [ ] **I1-002 · Dejar `src/` compilando** — 20 min · RF-12 (soporte) · Depende: I1-001
  - **Hecho cuando:** `python3 -m compileall -q src` termina con código `0` y `grep -rn "compressor_names" src/` no devuelve resultados.

- [ ] **I1-003 · Alinear `.env` y `.env.example` con testing y 5433** — 25 min · RF-12 (soporte) · Depende: I1-002
  - **Hecho cuando:** `grep -c '^DB_PORT=5433$' .env .env.example` devuelve `1` para cada archivo; `grep -E '^ENVIRONMENT=testing$' .env .env.example` devuelve 2 líneas; `grep -c '^DB_ADMIN_USER=' .env .env.example` devuelve `1` para cada archivo; `grep -c '^GOOGLE_MAPS_API_KEY=' .env .env.example` devuelve `1` para cada archivo.

- [ ] **I1-004 · `operacion/bootstrap_bd.py` para una sola base** — 45 min · RF-12 (soporte) · Depende: I1-003
  - **Hecho cuando:** `python3 operacion/bootstrap_bd.py` devuelve `0` ejecutado dos veces seguidas; `psql -h localhost -p 5433 -U "$DB_ADMIN_USER" -d postgres -tAc "select count(*) from pg_database where datname='destino3_test_db'"` devuelve `1`; `psql -h localhost -p 5433 -U "$DB_ADMIN_USER" -d postgres -tAc "select count(*) from pg_roles where rolname='destino3_testing'"` devuelve `1`.
  - **Nota:** el script lee `DB_TEST_USER`, `DB_TEST_PASSWORD` y `DB_ADMIN_USER` de `.env`; crea el rol y la base solo si faltan y no aplica el esquema.

- [ ] **I1-005 · Verificar conexión real a testing** — 15 min · RF-12 (soporte) · Depende: I1-004
  - **Hecho cuando:** `ENVIRONMENT=testing python3 -c "from src.config.database import obtener_conexion as o; print(o() is not None)"` imprime `True` y `python3 -m pytest test/ -q -rs` no muestra ningún `skipped` de `BaseDBTestCase`.

- [ ] **I1-006 · Eliminar borrados masivos del harness** — 10 min · RF-12 (soporte) · Depende: I1-001
  - **Hecho cuando:** `grep -rn "TRUNCATE\|DELETE FROM\|DROP TABLE" test/` no devuelve resultados fuera de comentarios.

- [ ] **I1-007 · `settings.py` con Places, Gemini y radios** — 30 min · RF-12 (soporte) · Depende: I1-003
  - **Hecho cuando:** `python3 -c "from src.config import settings as s; print(s.PLACES_TIMEOUT, s.GEMINI_MODEL, s.MAX_FINALISTAS, s.MAX_HOTELES, s.RADIO_20_MIN_M, s.RADIO_30_MIN_M)"` imprime `15.0 gemini-3.8-flash 5 20 1600 2400` y no existen constantes de TTL ni `ROUTES_TIMEOUT`.

- [ ] **I1-008 · Probar los settings nuevos** — 25 min · RF-12 (soporte) · Depende: I1-007
  - **Hecho cuando:** `python3 -m pytest test/test_config_settings.py -q` devuelve `0 failed` y el archivo contiene al menos 3 tests nuevos sobre radios, modelo y topes.

- [ ] **I1-009 · `main.py` mínimo con validación de entorno** — 30 min · RF-12 (soporte) · Depende: I1-007
  - **Hecho cuando:** `ENVIRONMENT=development python3 -m src.main; echo $?` imprime el mensaje de entorno inválido y devuelve `1`; `ENVIRONMENT=testing python3 -m src.main; echo $?` devuelve `1` con el aviso de flujo no implementado.

- [ ] **I1-010 · Probar el arranque de `main.py`** — 20 min · RF-12 (soporte) · Depende: I1-009
  - **Hecho cuando:** `python3 -m pytest test/test_main.py -q` devuelve `2 passed` y cubre entorno inválido y entorno válido sin TTY.

- [ ] **I1-011 · Gate Fase 0: suite en verde** — 30 min · RF-12 (soporte) · Depende: I1-001–I1-010
  - **Hecho cuando:** `python3 -m pytest test/ -q` devuelve `0 failed, 0 errors, 0 skipped` y `python3 -m pytest test/ -q -rs` confirma que no queda ningún test de base de datos saltado.

---

## Fase 1 — Dominio y datos (I1)

- [ ] **I1-012 · Modelos `FechasViaje` y `SolicitudViaje`** — 55 min · RF-1, RF-3 · Depende: I1-011
  - **Hecho cuando:** `python3 -c "from src.models.fechas_viaje import FechasViaje as F; from src.models.solicitud_viaje import SolicitudViaje as S; print(F(entrada='2027-01-10', salida='2027-01-13', zona_horaria='America/Bogota').noches, S(parcial=True).campos_faltantes())"` imprime `3 ['destino', 'fechas', 'adultos', 'presupuesto', 'ancla', 'minutos_maximos']` y `python3 -m pytest test/test_fechas_viaje.py test/test_solicitud_viaje.py -q` devuelve `0 failed`.

- [ ] **I1-013 · Modelos de proveedor** — 60 min · RF-5, RF-6, RF-7, RF-8, RF-9 · Depende: I1-012
  - **Hecho cuando:** `python3 -m pytest test/test_modelos_proveedor.py -q` devuelve `0 failed`; `python3 -c "from src.models.resena import Resena; print('autor' in Resena.__annotations__)"` imprime `False`; `python3 -c "from src.models.hospedaje import Hospedaje as H; h=H(nombre='X', precio_noche=100000, noches=2, moneda='COP'); print(h.precio_total, h.comparable)"` imprime `200000.0 True`.
  - **Nota:** `Destino`, `Hospedaje`, `Resena`, `Lugar` y `Distancia` usan clases simples con valores por defecto; solo la salida de Gemini usa Pydantic.

- [ ] **I1-014 · Modelos de plan** — 45 min · RF-10, RF-11 · Depende: I1-013
  - **Hecho cuando:** `python3 -m pytest test/test_modelos_plan.py -q` devuelve `0 failed`; `python3 -c "from src.models.itinerario import Bloque; from src.models.plan_viaje import PlanViaje as P; print([b.value for b in Bloque], P(top3=[], itinerario=None, advertencias=[]).es_completo)"` imprime `['manana', 'tarde', 'noche'] False`.

- [ ] **I1-015 · `sql/schema.sql` V0 con dos tablas** — 40 min · RF-5, RF-12 · Depende: I1-013
  - **Hecho cuando:** `grep -E "CREATE TABLE" sql/schema.sql` lista solo `destinos` y `hospedajes`; `grep -E "cache_api|lugares|evaluaciones_ia|atracciones" sql/schema.sql` no devuelve resultados; `hospedajes` incluye `precio_total`, `moneda`, `noches`, `latitud`, `longitud`, `admite_mascotas` y `serpapi_property_token`.

- [ ] **I1-016 · Aplicar el esquema a la base de pruebas** — 20 min · RF-12 · Depende: I1-015
  - **Hecho cuando:** `set -a; source .env; set +a; psql -h localhost -p 5433 -U "$DB_ADMIN_USER" -d destino3_test_db -f sql/schema.sql` termina sin error y `psql -h localhost -p 5433 -U "$DB_ADMIN_USER" -d destino3_test_db -c "\dt"` lista `destinos` y `hospedajes`.

- [ ] **I1-017 · Tests de esquema y tablas prohibidas** — 30 min · RF-12 · Depende: I1-016
  - **Hecho cuando:** `python3 -m pytest test/test_esquema.py -q` devuelve `0 failed` y verifica que solo existen `destinos` y `hospedajes`, que no hay `cache_api`, `lugares`, `evaluaciones_ia` ni `atracciones`, y que existen las unicidades de `google_place_id` y `serpapi_property_token`.

- [ ] **I1-018 · `DestinoRepository` con `upsert`** — 45 min · RF-1 · Depende: I1-016
  - **Hecho cuando:** `python3 -m pytest test/test_destino_repository.py -q` devuelve `0 failed` y guardar dos veces la misma ciudad devuelve el mismo `id`.

- [ ] **I1-019 · `HospedajeRepository` con `upsert`** — 55 min · RF-5 · Depende: I1-016
  - **Hecho cuando:** `python3 -m pytest test/test_hospedaje_repository.py -q` devuelve `0 failed` y dos guardados del mismo `serpapi_property_token` dejan una sola fila, con `precio_total`, moneda, coordenadas y FK a destino.

- [ ] **I1-020 · Retirar módulos y tests fuera de V0** — 45 min · RF-12 (soporte) · Depende: I1-019
  - **Hecho cuando:** `ls src/services/evaluador_ia.py src/services/buscador_serpapi.py src/orchestrator/orquestador_evaluacion.py src/orchestrator/orquestador_integracion.py src/repositories/evaluacion_ia_repository.py src/models/evaluacion.py src/models/evaluacion_ia.py src/models/atracciones.py src/demo_integracion.py 2>/dev/null | wc -l` devuelve `0`; `ls test/test_evaluador_ia.py test/test_orquestador_evaluacion.py test/test_orquestador_integracion.py test/test_evaluacion_ia.py test/test_evaluacion_ia_repository.py test/test_demo_integracion.py test/test_integracion_flujo_completo.py test/test_buscador_serpapi.py 2>/dev/null | wc -l` devuelve `0`; `python3 -m pytest test/ -q --continue-on-collection-errors` devuelve `0 errors`.
  - **Nota:** conserva las fixtures de SerpAPI que reutilizará `buscador_hoteles` y actualiza los `__init__.py` que importen módulos retirados.

- [ ] **I1-021 · Gate Fase 1: esquema, repositorios y suite limpia** — 30 min · RF-5, RF-12 · Depende: I1-012–I1-020
  - **Hecho cuando:** `python3 -m pytest test/ -q` devuelve `0 failed, 0 errors`; `psql -h localhost -p 5433 -U "$DB_ADMIN_USER" -d destino3_test_db -c "\dt"` lista solo `destinos` y `hospedajes`; `python3 -m pytest test/test_destino_repository.py test/test_hospedaje_repository.py -q` devuelve `0 failed`.

---

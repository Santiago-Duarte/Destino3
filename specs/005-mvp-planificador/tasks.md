# Tasks — Spec 005: MVP Planificador de Viaje

Desglose ejecutable del plan [`01`](01-arquitectura-y-modelo-datos.md) y [`02`](02-integracion-y-pruebas.md).
Cada tarea dura **≤ 60 minutos**, declara el **RF** que satisface y tiene un **Hecho cuando** binario y verificable.

## Convenciones

- **Orden:** las tareas son secuenciales; `Depende` solo lista la dependencia técnica que bloquea, no todas las anteriores.
- **Estimación:** minutos de esfuerzo de una persona con el contexto del plan ya leído.
- **RF:** todo task mapea a un RF de [`spec.md`](spec.md); los de soporte se marcan `RF-12 (soporte)`.
- **Hecho cuando:** siempre es un comando, un conteo o una consulta con resultado esperado. Nada de «queda funcionando».
- **Gates:** las tareas `T-009`, `T-045`, `T-054`, `T-065`, `T-076`, `T-086`, `T-095`, `T-105`, `T-114` cierran fase y no se saltan.
- **Prohibido:** marcar tests como `skip` para pasar, borrar aserciones válidas o tocar `production` desde la suite.
- **BD:** los tasks con PostgreSQL exigen motor encendido; sin motor, el criterio es `0 failed` y los `skipped` deben ser solo de `BaseDBTestCase` (comprobado con `-rs`).

## Resumen

| Fase | Tasks | Min | RF cubiertos |
|---|---|---|---|
| 0. Puesta a cero | T-001–T-009 | 290 | RF-12 |
| 1. Dominio y datos | T-010–T-045 | 1.280 | RF-1, 3, 5, 6, 7, 8, 9, 10, 11, 12 |
| 2. Infraestructura | T-046–T-054 | 340 | RF-4, 5, 6, 8, 9, 10, 12 |
| 3. Interpretación y CLI | T-055–T-065 | 510 | RF-1, 2, 3, 11 |
| 4. Destino, ancla y hoteles | T-066–T-076 | 530 | RF-1, 4, 5, 7 |
| 5. Distancias y presupuesto | T-077–T-086 | 465 | RF-6, 7, 8 |
| 6. Reseñas y evaluación IA | T-087–T-095 | 415 | RF-8, 10, 12 |
| 7. Lugares e itinerario | T-096–T-105 | 540 | RF-9, 10, 11, 12 |
| 8. Degradación y cierre | T-106–T-114 | 440 | RF-11, 12 |
| **Total** | **114 tasks** | **4.810 min ≈ 80 h** | **RF-1 a RF-12** |

---

## Fase 0 — Puesta a cero

- [ ] **T-001 · Reparar el harness de base de datos** — 40 min · RF-12 (soporte) · Depende: —
  - **Hecho cuando:** `python3 -m pytest test/ -q --continue-on-collection-errors` reporta `0 errors` en la colección y `grep -c "usuarios\|busqueda\|recomendacion" test/db_test_case.py` devuelve `0`.

- [ ] **T-002 · Dejar `src/` compilando** — 25 min · RF-12 (soporte) · Depende: T-001
  - **Hecho cuando:** `python3 -m compileall -q src` termina con código `0` y `grep -rn "compressor_names" src/` no devuelve resultados.

- [ ] **T-003 · Alinear `.env.example` con `database.py`** — 15 min · RF-12 (soporte) · Depende: —
  - **Hecho cuando:** `grep -E '^ENVIRONMENT=(testing|demo|production)$' .env.example` devuelve una línea y `grep -c '^GOOGLE_MAPS_API_KEY=' .env.example` devuelve `1`.

- [ ] **T-004 · Eliminar borrados masivos del harness** — 15 min · RF-12 (soporte) · Depende: T-001
  - **Hecho cuando:** `grep -rn "TRUNCATE\|DELETE FROM\|DROP TABLE" test/` no devuelve resultados fuera de comentarios.

- [ ] **T-005 · Ampliar `settings.py` con Places, Routes, Gemini y TTL** — 45 min · RF-12 (soporte) · Depende: T-003
  - **Hecho cuando:** `python3 -c "from src.config import settings as s; print(s.PLACES_TIMEOUT, s.ROUTES_TIMEOUT, s.GEMINI_MODEL, s.TTL_HOTELES_HORAS, s.TTL_RESENAS_DIAS, s.TTL_LUGARES_DIAS, s.MAX_FINALISTAS, s.MAX_HOTELES_RUTAS)"` imprime `15.0 15.0 gemini-3.8-flash 12 7 30 5 20`.

- [ ] **T-006 · Probar settings nuevos y recarga de entorno** — 35 min · RF-12 (soporte) · Depende: T-005
  - **Hecho cuando:** `python3 -m pytest test/test_config_settings.py -q` devuelve `0 failed` y el archivo contiene al menos 3 tests nuevos sobre TTL y modelo.

- [ ] **T-007 · `main.py` mínimo con validación de entorno** — 40 min · RF-12 (soporte) · Depende: T-005
  - **Hecho cuando:** `ENVIRONMENT=development python3 -m src.main; echo $?` imprime el mensaje de entorno inválido y devuelve `1`, y `ENVIRONMENT=testing python3 -m src.main; echo $?` devuelve `1` con el aviso de flujo no implementado.

- [ ] **T-008 · Probar el arranque de `main.py`** — 25 min · RF-12 (soporte) · Depende: T-007
  - **Hecho cuando:** `python3 -m pytest test/test_main.py -q` devuelve `2 passed` y cubre entorno inválido y entorno válido sin TTY.

- [ ] **T-009 · Gate Fase 0: suite en verde** — 50 min · RF-12 (soporte) · Depende: T-001–T-008
  - **Hecho cuando:** `python3 -m pytest test/ -q` devuelve `0 failed, 0 errors` y `python3 -m pytest test/ -q -rs` muestra que todos los `skipped` provienen de `BaseDBTestCase`.

---

## Fase 1 — Dominio y datos

- [ ] **T-010 · Modelo `FechasViaje`** — 45 min · RF-3 · Depende: T-009
  - **Hecho cuando:** `python3 -c "from src.models.fechas_viaje import FechasViaje as F; print(F(entrada='2027-01-10', salida='2027-01-13', zona_horaria='America/Bogota').noches)"` imprime `3` y rechaza salida anterior con `ValueError`.

- [ ] **T-011 · Tests de fechas límite** — 55 min · RF-3 · Depende: T-010
  - **Hecho cuando:** `python3 -m pytest test/test_fechas_viaje.py -q` devuelve `0 failed` con casos de fecha pasada, salida igual, 31 noches, año omitido, conflicto duración/salida, 1 noche y 30 noches.

- [ ] **T-012 · Modelo `SolicitudViaje` y campos faltantes** — 45 min · RF-1, RF-2 · Depende: T-010
  - **Hecho cuando:** `python3 -c "from src.models.solicitud_viaje import SolicitudViaje as S; print(S(parcial=True).campos_faltantes())"` imprime `['destino', 'fechas', 'adultos', 'presupuesto', 'ancla', 'minutos_maximos']`.

- [ ] **T-013 · Tests de solicitud y faltantes** — 40 min · RF-2 · Depende: T-012
  - **Hecho cuando:** `python3 -m pytest test/test_solicitud_viaje.py -q` devuelve `0 failed` y cubre cada campo faltante por separado más el caso completo sin faltantes.

- [ ] **T-014 · Extender modelo `Destino`** — 25 min · RF-1 · Depende: T-009
  - **Hecho cuando:** `python3 -c "from src.models.destino import Destino; print(Destino(ciudad='Santa Marta', pais='Colombia', latitud=11.24, longitud=-74.19, zona_horaria='America/Bogota').google_place_id)"` imprime `None`.

- [ ] **T-015 · Tests del modelo `Destino`** — 20 min · RF-1 · Depende: T-014
  - **Hecho cuando:** `python3 -m pytest test/test_destino_model.py -q` devuelve `0 failed` con coordenadas, zona horaria y `google_place_id`.

- [ ] **T-016 · Extender modelo `Hospedaje`** — 45 min · RF-5, RF-7 · Depende: T-014
  - **Hecho cuando:** `python3 -c "from src.models.hospedaje import Hospedaje as H; h=H(nombre='X', precio_noche=100000, noches=2, moneda='COP'); print(h.precio_total, h.comparable)"` imprime `200000.0 True`.

- [ ] **T-017 · Tests del modelo `Hospedaje`** — 35 min · RF-5, RF-7 · Depende: T-016
  - **Hecho cuando:** `python3 -m pytest test/test_hospedaje_model.py -q` devuelve `0 failed` con `total_antes_impuestos`, moneda distinta (`comparable=False`), coordenadas y `admite_mascotas=None`.

- [ ] **T-018 · Modelo `Resena` sin autor** — 20 min · RF-8 · Depende: T-016
  - **Hecho cuando:** `python3 -c "from src.models.resena import Resena; print('autor' in Resena.model_fields)"` imprime `False`.

- [ ] **T-019 · Tests del modelo `Resena`** — 20 min · RF-8 · Depende: T-018
  - **Hecho cuando:** `python3 -m pytest test/test_resena_model.py -q` devuelve `0 failed` y verifica que un dict con `autor` no lo persiste.

- [ ] **T-020 · Actualizar `EvaluacionIA` con cita y modelo** — 30 min · RF-8 · Depende: T-018
  - **Hecho cuando:** `python3 -c "from src.models.evaluacion_ia import EvaluacionIA; print(sorted(EvaluacionIA.model_fields))"` incluye `cita_textual`, `basada_en_resenas` y `modelo`.

- [ ] **T-021 · Tests de `EvaluacionIA`** — 25 min · RF-8 · Depende: T-020
  - **Hecho cuando:** `python3 -m pytest test/test_evaluacion_ia.py -q` devuelve `0 failed` con `basada_en_resenas=True/False` y `score_calidad_precio` entre 1 y 10.

- [ ] **T-022 · Modelo `Lugar`** — 30 min · RF-9 · Depende: T-009
  - **Hecho cuando:** `python3 -c "from src.models.lugar import Lugar; print(sorted(Lugar.model_fields))"` incluye `place_id`, `nombre`, `tipo`, `latitud`, `longitud`, `horario` y `google_maps_uri`.

- [ ] **T-023 · Tests del modelo `Lugar`** — 20 min · RF-9 · Depende: T-022
  - **Hecho cuando:** `python3 -m pytest test/test_lugar_model.py -q` devuelve `0 failed` con horario presente, ausente y lugar cerrado.

- [ ] **T-024 · Modelo `Distancia`** — 20 min · RF-6 · Depende: T-022
  - **Hecho cuando:** `python3 -c "from src.models.distancia import Distancia; print(Distancia(minutos_caminando=12, minutos_auto=4, verificada=True).es_estimacion_beta)"` imprime `True`.

- [ ] **T-025 · Tests del modelo `Distancia`** — 15 min · RF-6 · Depende: T-024
  - **Hecho cuando:** `python3 -m pytest test/test_distancia_model.py -q` devuelve `0 failed` con distancia verificada y no verificada.

- [ ] **T-026 · Modelo `Itinerario` con bloques** — 35 min · RF-10 · Depende: T-022
  - **Hecho cuando:** `python3 -c "from src.models.itinerario import Itinerario, Bloque; print([b.value for b in Bloque])"` imprime `['manana', 'tarde', 'noche']`.

- [ ] **T-027 · Tests del modelo `Itinerario`** — 30 min · RF-10 · Depende: T-026
  - **Hecho cuando:** `python3 -m pytest test/test_itinerario_model.py -q` devuelve `0 failed` con día de llegada sin mañana y día de salida solo con mañana.

- [ ] **T-028 · Modelo `PlanViaje`** — 35 min · RF-11 · Depende: T-020, T-026
  - **Hecho cuando:** `python3 -c "from src.models.plan_viaje import PlanViaje as P; print(P(top3=[], itinerario=None, advertencias=[]).es_completo)"` imprime `False`.

- [ ] **T-029 · Tests del modelo `PlanViaje`** — 25 min · RF-11 · Depende: T-028
  - **Hecho cuando:** `python3 -m pytest test/test_plan_viaje_model.py -q` devuelve `0 failed` con plan completo, parcial sin itinerario y parcial por moneda distinta.

- [ ] **T-030 · `sql/schema.sql` canónico** — 55 min · RF-5, RF-9, RF-12 · Depende: T-016, T-022
  - **Hecho cuando:** `psql -d destino3_test_db -f sql/schema.sql` termina sin error y `psql -d destino3_test_db -c "\dt"` lista `cache_api, destinos, evaluaciones_ia, hospedajes, lugares` sin `atracciones`.

- [ ] **T-031 · Migración aditiva `003_mvp_planificador.sql`** — 50 min · RF-12 · Depende: T-030
  - **Hecho cuando:** aplicar `sql/migrations/003_mvp_planificador.sql` sobre una BD con el esquema anterior termina sin error, se puede ejecutar dos veces seguidas y no borra filas de `hospedajes`.

- [ ] **T-032 · Tests de esquema y columnas prohibidas** — 45 min · RF-12 · Depende: T-031
  - **Hecho cuando:** `python3 -m pytest test/test_esquema.py -q` devuelve `0 failed` y verifica que `lugares` no tiene `nombre`, `rating` ni `horario`, y que existen las unicidades de `clave_hash` y `hospedaje_id`.

- [ ] **T-033 · `DestinoRepository` con `upsert`** — 35 min · RF-1 · Depende: T-030
  - **Hecho cuando:** `python3 -m pytest test/test_destino_repository.py -q` devuelve `0 failed` y guardar dos veces la misma ciudad devuelve el mismo `id`.

- [ ] **T-034 · Tests del repositorio de destinos** — 30 min · RF-1 · Depende: T-033
  - **Hecho cuando:** `python3 -m pytest test/test_destino_repository.py -q` cubre inserción, actualización por `google_place_id` y lectura por ciudad/país, con `0 failed`.

- [ ] **T-035 · `HospedajeRepository` con `upsert` y campos nuevos** — 50 min · RF-5 · Depende: T-030
  - **Hecho cuando:** `python3 -m pytest test/test_hospedaje_repository.py -q` devuelve `0 failed` y dos guardados del mismo `property_token` dejan una sola fila.

- [ ] **T-036 · Tests del repositorio de hospedajes** — 45 min · RF-5 · Depende: T-035
  - **Hecho cuando:** `python3 -m pytest test/test_hospedaje_repository.py -q` cubre `precio_total`, `moneda`, coordenadas, FK a destino y deduplicación por `google_place_id`, con `0 failed`.

- [ ] **T-037 · `EvaluacionIARepository` con `upsert` por hospedaje** — 30 min · RF-8 · Depende: T-035
  - **Hecho cuando:** `python3 -m pytest test/test_evaluacion_ia_repository.py -q` devuelve `0 failed` y una segunda evaluación del mismo hotel actualiza la fila existente.

- [ ] **T-038 · Tests del repositorio de evaluaciones** — 30 min · RF-8 · Depende: T-037
  - **Hecho cuando:** `python3 -m pytest test/test_evaluacion_ia_repository.py -q` cubre cita, `basada_en_resenas`, modelo y borrado en cascada, con `0 failed`.

- [ ] **T-039 · `LugarRepository` de solo `place_id` y coordenadas** — 30 min · RF-9 · Depende: T-030
  - **Hecho cuando:** `python3 -c "from src.repositories.lugar_repository import LugarRepository; print(sorted(LugarRepository.COLUMNAS))"` imprime `['expira_en', 'google_place_id', 'latitud', 'longitud']`.

- [ ] **T-040 · Tests del repositorio de lugares** — 30 min · RF-9 · Depende: T-039
  - **Hecho cuando:** `python3 -m pytest test/test_lugar_repository.py -q` devuelve `0 failed` y verifica que no se puede insertar nombre ni horario.

- [ ] **T-041 · `CacheRepository` con TTL y `upsert`** — 55 min · RF-12 · Depende: T-030
  - **Hecho cuando:** `python3 -m pytest test/test_cache_repository.py -q` devuelve `0 failed` con lectura vigente, lectura vencida devolviendo `None` y `clave_hash` único.

- [ ] **T-042 · Tests del repositorio de caché** — 50 min · RF-12 · Depende: T-041
  - **Hecho cuando:** `python3 -m pytest test/test_cache_repository.py -q` cubre guardar, leer, sobrescribir, entrada corrupta tratada como inexistente y `version_esquema`.

- [ ] **T-043 · `politica_cache`: clave canónica, TTL y respaldo** — 40 min · RF-12 · Depende: T-041
  - **Hecho cuando:** `python3 -c "from src.orchestrator.politica_cache import clave_cache; print(clave_cache('serpapi','hoteles',{'q':'x','b':2}) == clave_cache('serpapi','hoteles',{'b':2,'q':'x'}))"` imprime `True`.

- [ ] **T-044 · Tests de `politica_cache`** — 45 min · RF-12 · Depende: T-043
  - **Hecho cuando:** `python3 -m pytest test/test_politica_cache.py -q` devuelve `0 failed` con TTL por tipo de dato, respaldo ≤7 días y rechazo de respaldo >7 días.

- [ ] **T-045 · Gate Fase 1: migración y repositorios en las tres bases** — 45 min · RF-12 · Depende: T-030–T-044
  - **Hecho cuando:** `psql -d destino3_test_db -c "\dt"`, `psql -d demo_db -c "\dt"` y `psql -d destino3_db -c "\dt"` listan las mismas 5 tablas y `python3 -m pytest test/ -q` devuelve `0 failed, 0 errors`.

---

## Fase 2 — Infraestructura

- [ ] **T-046 · Jerarquía de errores tipados** — 45 min · RF-12 · Depende: T-009
  - **Hecho cuando:** `python3 -c "from src.exceptions import ErrorProveedor; e=ErrorProveedor(proveedor='serpapi', operacion='hoteles', reintentable=True, mensaje_usuario='x'); print(sorted(e.a_dict().keys()))"` incluye `proveedor`, `operacion`, `reintentable`, `mensaje_usuario` y `detalle_tecnico`.

- [ ] **T-047 · Tests de errores sin secretos** — 30 min · RF-12 · Depende: T-046
  - **Hecho cuando:** `python3 -m pytest test/test_errores_tipados.py -q` devuelve `0 failed` y verifica que un mensaje con `api_key=ABC` sale redactado.

- [ ] **T-048 · `cliente_http` con reintentos, backoff y redacción** — 60 min · RF-12 · Depende: T-046
  - **Hecho cuando:** `python3 -m pytest test/test_cliente_http.py -q` devuelve `0 failed` con 3 intentos ante 429/5xx, 1 intento ante 400, respeto de `Retry-After` y `api_key` redactada.

- [ ] **T-049 · Tests del cliente HTTP con transporte falso** — 55 min · RF-12 · Depende: T-048
  - **Hecho cuando:** `python3 -m pytest test/test_cliente_http.py -q` cubre éxito, 429, 500, timeout, error de conexión y 4xx no reintentable, con `0 failed` y sin red real.

- [ ] **T-050 · Fixtures de hoteles** — 30 min · RF-5 · Depende: T-009
  - **Hecho cuando:** existen `test/fixtures/serpapi_hoteles_cop.json`, `serpapi_hoteles_sin_precio.json` y `serpapi_hoteles_otra_moneda.json`, y `python3 -c "import json; [json.load(open(f'test/fixtures/{n}')) for n in ('serpapi_hoteles_cop.json','serpapi_hoteles_sin_precio.json','serpapi_hoteles_otra_moneda.json')]"` termina sin error.

- [ ] **T-051 · Fixtures de Places y Routes** — 35 min · RF-4, RF-6, RF-9 · Depende: T-009
  - **Hecho cuando:** existen `places_destino.json`, `places_ancla.json`, `places_ancla_fuera.json`, `places_nearby.json`, `places_nearby_pocos.json`, `routes_walk.json` y `routes_drive.json`, y todos cargan con `json.load`.

- [ ] **T-052 · Fixtures de Gemini y caché** — 30 min · RF-8, RF-10, RF-12 · Depende: T-009
  - **Hecho cuando:** existen `gemini_solicitud.json`, `gemini_solicitud_invalida.json`, `gemini_evaluacion.json`, `gemini_evaluacion_cita_falsa.json`, `gemini_itinerario.json`, `gemini_itinerario_id_inventado.json`, `serpapi_resenas.json`, `serpapi_sin_resenas.json` y `cache_vencida.json`, y todos cargan con `json.load`.

- [ ] **T-053 · Cargador de fixtures y transporte falso reutilizable** — 35 min · RF-12 · Depende: T-050–T-052
  - **Hecho cuando:** `python3 -m pytest test/test_fixtures_loader.py -q` devuelve `0 failed` y `python3 -c "from test.fixtures.loader import cargar, transporte_falso; print(len(cargar('serpapi_hoteles_cop.json')['properties']))"` imprime un entero mayor que 0.

- [ ] **T-054 · Gate Fase 2: infraestructura aislada y suite estable** — 20 min · RF-12 · Depende: T-046–T-053
  - **Hecho cuando:** `python3 -m pytest test/ -q` devuelve `0 failed, 0 errors` y `grep -rn "requests\.\|http" src/services/cliente_http.py | grep -v "^.*#"` confirma que solo ese módulo hace HTTP directo.

---

## Fase 3 — Interpretación y CLI

- [ ] **T-055 · Normalizador de fechas** — 50 min · RF-3 · Depende: T-010
  - **Hecho cuando:** `python3 -c "from src.orchestrator.normalizador import normalizar_fechas; print(normalizar_fechas('10/01/2027 al 13/01/2027', zona='America/Bogota').noches)"` imprime `3`.

- [ ] **T-056 · Normalizador de montos y ocupación** — 45 min · RF-3 · Depende: T-055
  - **Hecho cuando:** `python3 -c "from src.orchestrator.normalizador import normalizar_presupuesto, normalizar_ocupacion; print(normalizar_presupuesto('2 millones'), normalizar_ocupacion('2 adultos y 2 niños'))"` imprime `2000000 2 2`.

- [ ] **T-057 · Tests del normalizador** — 55 min · RF-3 · Depende: T-055, T-056
  - **Hecho cuando:** `python3 -m pytest test/test_normalizador.py -q` devuelve `0 failed` con `YYYY-MM-DD`, `DD/MM/YYYY`, «2 millones», «$2.000.000», año omitido y ocupación sin edades.

- [ ] **T-058 · `interpretador_solicitud` con Gemini y Pydantic** — 60 min · RF-1 · Depende: T-012, T-048, T-052
  - **Hecho cuando:** `python3 -m pytest test/test_interpretador_solicitud.py -q` devuelve `0 failed` con la fixture válida y produce un `SolicitudViaje` sin campos inventados.

- [ ] **T-059 · Tests del interpretador y su respaldo** — 50 min · RF-1 · Depende: T-058
  - **Hecho cuando:** `python3 -m pytest test/test_interpretador_solicitud.py -q` cubre respuesta inválida de Gemini, fallo del proveedor y respaldo por normalizador, con `0 failed`.

- [ ] **T-060 · Detector de ambigüedad y de menciones fuera de alcance** — 40 min · RF-1, RF-2 · Depende: T-058
  - **Hecho cuando:** `python3 -c "from src.orchestrator.interpretador_solicitud import clasificar_mencion; print(clasificar_mencion('quiero ir a Monserrate'))"` imprime `fuera_de_alcance`.

- [ ] **T-061 · Tests de ambigüedad y fuera de alcance** — 35 min · RF-1 · Depende: T-060
  - **Hecho cuando:** `python3 -m pytest test/test_ambiguedad_destino.py -q` devuelve `0 failed` con ciudad homónima, Monserrate, Buritacá, Muralla China y Disneyland, y confirma que no se llama a proveedores.

- [ ] **T-062 · `cli/lector` de datos faltantes** — 55 min · RF-2 · Depende: T-012, T-055, T-056
  - **Hecho cuando:** `python3 -m pytest test/test_lector.py -q` devuelve `0 failed` con preguntas solo por campos faltantes, `YYYY-MM-DD`, `DD/MM/YYYY`, montos con separadores y «sin preferencia».

- [ ] **T-063 · Tests del lector y terminal no interactiva** — 50 min · RF-2 · Depende: T-062
  - **Hecho cuando:** `python3 -m pytest test/test_lector.py -q` cubre `isatty()=False` terminando con error, respuesta inválida repreguntada y fecha pasada rechazada, con `0 failed`.

- [ ] **T-064 · `cli/presentador` inicial** — 40 min · RF-11 · Depende: T-028
  - **Hecho cuando:** `python3 -c "from src.cli.presentador import formatear_solicitud; print(formatear_solicitud.__doc__ is not None)"` imprime `True` y el texto incluye destino, fechas, ocupación y presupuesto.

- [ ] **T-065 · Tests del presentador inicial** — 30 min · RF-11 · Depende: T-064
  - **Hecho cuando:** `python3 -m pytest test/test_presentador_inicial.py -q` devuelve `0 failed` y verifica que un presupuesto se muestra en COP con separadores.

---

## Fase 4 — Destino, ancla y hoteles

- [ ] **T-066 · `PlacesClient` con Text Search** — 55 min · RF-1, RF-4 · Depende: T-048, T-051
  - **Hecho cuando:** `python3 -m pytest test/test_places_cliente.py -q` devuelve `0 failed` con `places_destino.json` y `places_ancla.json`, y la petición incluye `languageCode=es` y `pageSize=5`.

- [ ] **T-067 · Tests de contrato de Places** — 45 min · RF-4 · Depende: T-066
  - **Hecho cuando:** `python3 -m pytest test/test_places_cliente.py -q` cubre respuesta vacía, error 500 y campo faltante, con `0 failed` y sin red.

- [ ] **T-068 · `resolutor_destino` con persistencia** — 45 min · RF-1 · Depende: T-066, T-033
  - **Hecho cuando:** `python3 -m pytest test/test_resolutor_destino.py -q` devuelve `0 failed` y un destino resuelto queda con `google_place_id`, coordenadas y zona horaria guardados.

- [ ] **T-069 · Tests del resolutor de destino** — 40 min · RF-1 · Depende: T-068
  - **Hecho cuando:** `python3 -m pytest test/test_resolutor_destino.py -q` cubre resultado único, varios candidatos y sin resultados, con `0 failed`.

- [ ] **T-070 · `resolutor_ancla` con validación de tipo y distancia** — 55 min · RF-4 · Depende: T-066, T-024
  - **Hecho cuando:** `python3 -m pytest test/test_resolutor_ancla.py -q` devuelve `0 failed` con playa, ciudad amurallada, estadio, centro y «sin preferencia».

- [ ] **T-071 · Tests del resolutor de ancla** — 55 min · RF-4 · Depende: T-070
  - **Hecho cuando:** `python3 -m pytest test/test_resolutor_ancla.py -q` cubre varios candidatos (usa el primero y lo declara), fuera del destino, tipo incorrecto y fallo de Places, con `0 failed`.

- [ ] **T-072 · `buscador_hoteles`: mapeo COP y precios** — 60 min · RF-5, RF-7 · Depende: T-016, T-048, T-050
  - **Hecho cuando:** `python3 -m pytest test/test_buscador_hoteles.py -q` devuelve `0 failed` con `precio_total` desde `before_taxes_fees`, respaldo por noches y `comparable=False` en otra moneda.

- [ ] **T-073 · Tests del mapeo de hoteles** — 55 min · RF-5, RF-7 · Depende: T-072
  - **Hecho cuando:** `python3 -m pytest test/test_buscador_hoteles.py -q` cubre sin precio (descarta), sin coordenadas (descarta), sin link (conserva con advertencia) y grupo que excede una habitación, con `0 failed`.

- [ ] **T-074 · Deduplicación y segunda página condicional** — 40 min · RF-5 · Depende: T-072
  - **Hecho cuando:** `python3 -m pytest test/test_buscador_hoteles.py -q` devuelve `0 failed` con duplicados por `google_place_id`, por `property_token` y por nombre+dirección, y confirma que la segunda página solo se pide con menos de 3 resultados.

- [ ] **T-075 · Tests de deduplicación y paginación** — 40 min · RF-5 · Depende: T-074
  - **Hecho cuando:** `python3 -m pytest test/test_buscador_hoteles.py -q` verifica que una sola página basta con ≥3 hoteles y que nunca se piden más de 2 páginas.

- [ ] **T-076 · Gate Fase 4: hoteles persistidos con IDs reales** — 40 min · RF-5 · Depende: T-068–T-075
  - **Hecho cuando:** `python3 -m pytest test/test_flujo_hoteles.py -q` devuelve `0 failed` y tras el flujo `psql -d destino3_test_db -tAc "SELECT COUNT(*) FROM hospedajes"` devuelve un número mayor que 0.

---

## Fase 5 — Distancias y presupuesto

- [ ] **T-077 · `RoutesClient` con `computeRoutes`** — 50 min · RF-6 · Depende: T-048, T-051
  - **Hecho cuando:** `python3 -m pytest test/test_routes_cliente.py -q` devuelve `0 failed` y un `duration` de 721 s se convierte en 13 minutos.

- [ ] **T-078 · Tests de contrato de Routes** — 40 min · RF-6 · Depende: T-077
  - **Hecho cuando:** `python3 -m pytest test/test_routes_cliente.py -q` cubre `WALK`, `DRIVE`, respuesta sin ruta y error 500, con `0 failed`.

- [ ] **T-079 · `calculador_distancias` con prefiltro haversine** — 55 min · RF-6 · Depende: T-077, T-024
  - **Hecho cuando:** `python3 -m pytest test/test_calculador_distancias.py -q` devuelve `0 failed` y confirma que no se llama a Routes para hoteles fuera del radio ni más de 20 veces.

- [ ] **T-080 · Tests del calculador de distancias** — 50 min · RF-6 · Depende: T-079
  - **Hecho cuando:** `python3 -m pytest test/test_calculador_distancias.py -q` cubre fallo puntual (descarta hotel), fallo total (marca no verificada) y `DRIVE` solo para los mostrados, con `0 failed`.

- [ ] **T-081 · `reglas_cercania` con escalera 10/20/30/45/60** — 50 min · RF-6 · Depende: T-024
  - **Hecho cuando:** `python3 -c "from src.orchestrator.reglas_cercania import ampliar_nivel; print(ampliar_nivel(20))"` imprime `30` y `ampliar_nivel(60)` imprime `None`.

- [ ] **T-082 · Tests de cercanía** — 55 min · RF-6 · Depende: T-081
  - **Hecho cuando:** `python3 -m pytest test/test_reglas_cercania.py -q` devuelve `0 failed` con los 5 niveles, ampliación con aviso, 3 más cercanos en el tope y descarte de hoteles sin distancia.

- [ ] **T-083 · `reglas_presupuesto`** — 45 min · RF-7 · Depende: T-016
  - **Hecho cuando:** `python3 -c "from src.orchestrator.reglas_presupuesto import cabe; print(cabe(2000000, 2000000), cabe(2000001, 2000000))"` imprime `True False`.

- [ ] **T-084 · Tests de presupuesto** — 50 min · RF-7 · Depende: T-083
  - **Hecho cuando:** `python3 -m pytest test/test_reglas_presupuesto.py -q` devuelve `0 failed` con total antes de impuestos, solo precio por noche, empate exacto, ninguno cabe (3 más baratos + excedente) y moneda distinta.

- [ ] **T-085 · `ranking` determinista base** — 35 min · RF-8, RF-12 · Depende: T-016
  - **Hecho cuando:** `python3 -c "from src.orchestrator.ranking import ordenar; print(ordenar([{'calificacion':4.2,'precio_total':300,'minutos':5},{'calificacion':4.8,'precio_total':400,'minutos':9}])[0]['calificacion'])"` imprime `4.8`.

- [ ] **T-086 · Gate Fase 5: cercanía y presupuesto integrados** — 35 min · RF-6, RF-7 · Depende: T-079–T-085
  - **Hecho cuando:** `python3 -m pytest test/test_flujo_cercania_presupuesto.py -q` devuelve `0 failed` con un hotel fuera de minutos descartado y uno que excede el presupuesto fuera del top 3.

---

## Fase 6 — Reseñas y evaluación IA

- [ ] **T-087 · `buscador_resenas`** — 50 min · RF-8 · Depende: T-018, T-048, T-052
  - **Hecho cuando:** `python3 -m pytest test/test_buscador_resenas.py -q` devuelve `0 failed` y una reseña mapeada no contiene `autor`.

- [ ] **T-088 · Tests de reseñas** — 50 min · RF-8 · Depende: T-087
  - **Hecho cuando:** `python3 -m pytest test/test_buscador_resenas.py -q` cubre hotel sin `property_token`, hotel sin reseñas, fallo del proveedor y caché de 7 días, con `0 failed`.

- [ ] **T-089 · `evaluador_hoteles_ia` con salida Pydantic** — 60 min · RF-8 · Depende: T-020, T-058, T-087
  - **Hecho cuando:** `python3 -m pytest test/test_evaluador_hoteles_ia.py -q` devuelve `0 failed` con `gemini_evaluacion.json` y produce evaluación para cada uno de los 5 finalistas.

- [ ] **T-090 · Tests del evaluador IA** — 50 min · RF-8 · Depende: T-089
  - **Hecho cuando:** `python3 -m pytest test/test_evaluador_hoteles_ia.py -q` cubre 5 finalistas, hotel sin reseñas marcado «no verificado», mascotas con dato/`False`/sin dato y fallo de Gemini, con `0 failed`.

- [ ] **T-091 · `validador_ia` de citas e IDs** — 45 min · RF-8, RF-10 · Depende: T-089
  - **Hecho cuando:** `python3 -m pytest test/test_validador_ia.py -q` devuelve `0 failed` y una cita que no es substring se descarta mientras el resto de la evaluación se conserva.

- [ ] **T-092 · Tests del validador IA** — 45 min · RF-8, RF-10 · Depende: T-091
  - **Hecho cuando:** `python3 -m pytest test/test_validador_ia.py -q` cubre cita falsa, `id_temporal` inexistente y evaluación completamente inválida, con `0 failed`.

- [ ] **T-093 · Ranking final con evaluación IA y fallback** — 45 min · RF-8, RF-12 · Depende: T-085, T-091
  - **Hecho cuando:** `python3 -m pytest test/test_ranking_final.py -q` devuelve `0 failed` y, sin evaluación IA, el orden es calificación desc, precio asc, distancia asc.

- [ ] **T-094 · Tests del ranking final** — 40 min · RF-8 · Depende: T-093
  - **Hecho cuando:** `python3 -m pytest test/test_ranking_final.py -q` cubre top 3 con evaluación válida, con evaluación parcial y con fallback total, con `0 failed`.

- [ ] **T-095 · Gate Fase 6: evaluación persistida** — 30 min · RF-8 · Depende: T-089–T-094
  - **Hecho cuando:** `python3 -m pytest test/test_flujo_evaluacion.py -q` devuelve `0 failed` y `psql -d destino3_test_db -tAc "SELECT COUNT(*) FROM evaluaciones_ia"` es mayor que 0 sin filas duplicadas por `hospedaje_id`.

---

## Fase 7 — Lugares e itinerario

- [ ] **T-096 · `buscador_lugares` con Nearby Search y umbrales** — 60 min · RF-9 · Depende: T-022, T-066
  - **Hecho cuando:** `python3 -m pytest test/test_buscador_lugares.py -q` devuelve `0 failed` con radio de 2.000 m, `rankPreference=DISTANCE` y ampliación a 3.000 m.

- [ ] **T-097 · Tests de lugares cercanos** — 55 min · RF-9 · Depende: T-096
  - **Hecho cuando:** `python3 -m pytest test/test_buscador_lugares.py -q` cubre ≥5 lugares y ≥2 restaurantes, menos de 5, menos de 2, cero lugares y lugar cerrado permanentemente, con `0 failed`.

- [ ] **T-098 · `generador_itinerario_ia`** — 60 min · RF-10 · Depende: T-026, T-058, T-096
  - **Hecho cuando:** `python3 -m pytest test/test_generador_itinerario.py -q` devuelve `0 failed` con `gemini_itinerario.json` y todos los `lugar_id` existen en la lista enviada.

- [ ] **T-099 · Tests del itinerario IA** — 55 min · RF-10 · Depende: T-098
  - **Hecho cuando:** `python3 -m pytest test/test_generador_itinerario.py -q` cubre ID inventado descartado, lugar cerrado en el bloque, lugar sin horario, día de llegada y día de salida, con `0 failed`.

- [ ] **T-100 · `planificador_itinerario` determinista** — 50 min · RF-10, RF-12 · Depende: T-081
  - **Hecho cuando:** `python3 -m pytest test/test_planificador_itinerario.py -q` devuelve `0 failed` y con la misma lista produce bloques completos sin repetir lugares.

- [ ] **T-101 · Tests del itinerario determinista** — 40 min · RF-10 · Depende: T-100
  - **Hecho cuando:** `python3 -m pytest test/test_planificador_itinerario.py -q` cubre fallback total de Gemini, lista con 3 lugares y restaurante asignado a comida, con `0 failed`.

- [ ] **T-102 · `orchestrator/planificador` con el pipeline completo** — 60 min · RF-11 · Depende: T-068–T-100
  - **Hecho cuando:** `python3 -c "from src.orchestrator.planificador import Planificador; print([m for m in dir(Planificador) if not m.startswith('_')])"` incluye `ejecutar` y el orden de etapas está en el docstring.

- [ ] **T-103 · Test end-to-end con proveedores mockeados** — 60 min · RF-11 · Depende: T-102
  - **Hecho cuando:** `python3 -m pytest test/test_pipeline_completo.py -q` devuelve `0 failed` con una frase completa y produce top 3, itinerario, links y comparación de presupuesto.

- [ ] **T-104 · `cli/presentador` completo** — 55 min · RF-11 · Depende: T-028, T-103
  - **Hecho cuando:** `python3 -m pytest test/test_presentador.py -q` devuelve `0 failed` y la salida contiene top 3, itinerario, links, mapa, presupuesto en COP y la atribución «Google Maps».

- [ ] **T-105 · Gate Fase 7: presentador y plan parcial** — 45 min · RF-11 · Depende: T-104
  - **Hecho cuando:** `python3 -m pytest test/test_presentador.py -q` cubre plan completo, sin itinerario (parcial con razón), link faltante y moneda distinta, con `0 failed`.

---

## Fase 8 — Degradación y cierre

- [ ] **T-106 · `degradacion` con la matriz de fallos** — 50 min · RF-12 · Depende: T-102
  - **Hecho cuando:** `python3 -c "from src.orchestrator.degradacion import MATRIZ; print(sorted(MATRIZ))"` incluye `hoteles`, `resenas`, `places`, `routes`, `gemini` y `postgres`.

- [ ] **T-107 · Tests de degradación por proveedor** — 60 min · RF-12 · Depende: T-106
  - **Hecho cuando:** `python3 -m pytest test/test_degradacion.py -q` devuelve `0 failed` con una prueba por fila de la matriz y ninguna inventa datos.

- [ ] **T-108 · Caché vencida, corrupta y fallo de persistencia** — 45 min · RF-12 · Depende: T-043, T-106
  - **Hecho cuando:** `python3 -m pytest test/test_degradacion_cache.py -q` devuelve `0 failed` con respaldo ≤7 días, respaldo >7 días rechazado, entrada corrupta ignorada y plan en memoria si falla PostgreSQL.

- [ ] **T-109 · Tests de caché y persistencia degradadas** — 50 min · RF-12 · Depende: T-108
  - **Hecho cuando:** `python3 -m pytest test/test_degradacion_cache.py -q` verifica que cada caso agrega una advertencia visible y que Places nunca usa contenido vencido, con `0 failed`.

- [ ] **T-110 · `main.py` con flujo completo y códigos de salida** — 55 min · RF-11, RF-12 · Depende: T-103, T-106
  - **Hecho cuando:** `python3 -m pytest test/test_main_flujo.py -q` devuelve `0 failed` con códigos `0` (completo), `3` (parcial), `1` (entrada/config) y `2` (fatal).

- [ ] **T-111 · Tests de códigos de salida y Ctrl+C** — 35 min · RF-12 · Depende: T-110
  - **Hecho cuando:** `python3 -m pytest test/test_main_flujo.py -q` cubre `KeyboardInterrupt` devolviendo `130` y ausencia de credenciales en la salida, con `0 failed`.

- [ ] **T-112 · Smoke manual en `demo_db`** — 60 min · RF-11 · Depende: T-110
  - **Hecho cuando:** una ejecución real con 2 adultos, 2 niños, 3 días y 2 noches termina con código `0`, muestra top 3 con reseñas, itinerario, links, distancias con aviso beta y presupuesto, y la evidencia queda anotada en `specs/005-mvp-planificador/smoke.md`.

- [ ] **T-113 · README con alcance, atribuciones y credenciales** — 40 min · RF-11 · Depende: T-110
  - **Hecho cuando:** `grep -c "Google Maps\|términos\|privacidad\|GOOGLE_MAPS_API_KEY\|ENVIRONMENT" README.md` devuelve al menos `5` y no aparece ninguna clave real.

- [ ] **T-114 · Gate final: suite, criterios §8 y estado documentado** — 45 min · RF-1–RF-12 · Depende: T-001–T-113
  - **Hecho cuando:** `python3 -m pytest test/ -q` devuelve `0 failed, 0 errors`, los 8 criterios de aceptación de `spec.md` §8 quedan marcados en `tasks.md` y `plan.md` refleja el estado final.

---

## Criterios de aceptación (spec §8)

- [ ] Frase completa produce plan con top 3, itinerario, links y presupuesto sin preguntas extra.
- [ ] Frase incompleta pregunta solo lo faltante y no consulta proveedores antes de completar.
- [ ] Fechas y presupuestos inválidos se rechazan y se repreguntan.
- [ ] Todo hotel mostrado cumple los minutos o el plan declara la ampliación o los 3 más cercanos.
- [ ] Cada afirmación de la evaluación se apoya en una reseña real o se marca «no verificado».
- [ ] Ningún lugar del itinerario carece de correspondencia en la lista consultada.
- [ ] Ante el fallo simulado de cada proveedor, el plan degrada según RF-12 sin datos inventados.
- [ ] La suite queda en verde, sin credenciales en salida ni registros, y el rendimiento se mide según el RNF.

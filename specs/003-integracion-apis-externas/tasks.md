# Tareas — Spec 003: Integración de APIs Externas (SerpAPI + Gemini) y Persistencia

**Reglas:** cada tarea <30 min · ordenadas por dependencia · una sola línea `Hecho cuando:` verificable · al terminar cada tarea: `python3 -m pytest test/ -q` en verde.
**Nombres de módulos:** se mantienen los actuales (`api_searcher.py`, `ai_evaluator.py`, `evaluaciones_repository.py`); `plan.md` se corrige en H4.

## Bloque A — Configuración (base de todo)

- [x] **A1. Crear `src/config/settings.py`** (~20 min)
  - **RF:** RF-9, RF-10
  - **Depende de:** —
  - **Hecho cuando:** `SERPAPI_MAX_PAGES=2 python3 -c "from src.config import settings; print(settings.SERPAPI_MAX_PAGES)"` imprime `2` y expone timeout, reintentos, backoff, `max_results`, `rate_limit_rps` y claves sin hardcodear en servicios.

## Bloque B — Modelos Pydantic

- [x] **B1. Crear `src/models/evaluacion_ia.py`** con `EvaluacionIAOutput` (`id_temporal`, `resumen_ejecutivo`, `puntos_fuertes`, `puntos_debiles`, `score_calidad_precio` 1-10) y `LoteEvaluacionesIA` (~20 min)
  - **RF:** RF-6
  - **Depende de:** —
  - **Hecho cuando:** `LoteEvaluacionesIA.model_validate_json(json_inválido)` lanza `ValidationError` y uno válido parsea sin error.
- [x] **B2. Migrar `ai_evaluator.py` y `evaluacion_orchestrator.py` a los modelos de `models/`** (eliminar `Top3Evaluaciones` local, campo `top_3` → `evaluaciones`) (~20 min)
  - **RF:** RF-5, RF-6
  - **Depende de:** B1
  - **Hecho cuando:** `grep -rn "Top3Evaluaciones" src/` no da resultados y la suite actual queda verde (el prompt no se modifica: fuera de alcance).

## Bloque C — Repositories

- [ ] **C1. `HospedajeRepository.guardar_varios()` con transacción única** (~25 min)
  - **RF:** RF-4
  - **Depende de:** —
  - **Hecho cuando:** guardar 3 hospedajes devuelve 3 IDs `int` y, al forzar error en el 3º, la tabla queda sin filas (rollback).
- [ ] **C2. `EvaluacionesRepository.guardar_varias()`** con `hospedaje_id` real, solo campos de negocio, sin `id_temporal` (~25 min)
  - **RF:** RF-7, RF-8
  - **Depende de:** C1
  - **Hecho cuando:** `grep -rn "id_temporal" src/repositories/` no da resultados y un error a mitad de lote revierte toda la inserción (sin filas parciales).

## Bloque D — Cliente SerpAPI (`src/services/api_searcher.py`)

- [ ] **D1. Parámetros operativos desde `settings` + `logging`** (quitar `print`, propagar errores) (~20 min)
  - **RF:** RF-1, RF-10
  - **Depende de:** A1
  - **Hecho cuando:** `grep -n "print(" src/services/api_searcher.py` no da resultados y `requests.get` recibe `timeout=settings.SERPAPI_TIMEOUT`.
- [ ] **D2. Paginación con `max_pages` / `max_results`** que corta y conserva acumulados (~25 min)
  - **RF:** RF-3
  - **Depende de:** D1
  - **Hecho cuando:** con mock de 3 páginas y `SERPAPI_MAX_PAGES=2` se hacen 2 llamadas y el resultado contiene solo las páginas 1-2.
- [ ] **D3. Rate limiting (token bucket con `threading.Lock`) + HTTP 429/`Retry-After` + reintentos con backoff** (~30 min)
  - **RF:** RF-2, RF-9
  - **Depende de:** D2
  - **Hecho cuando:** mock que devuelve 429 en todos los intentos → el cliente agota reintentos y devuelve los resultados acumulados, y con `SERPAPI_RATE_LIMIT_RPS` configurado no se exceden las llamadas/s en dos hilos.
- [ ] **D4. Eliminar la escritura de `respuesta_prueba.json` de `api_searcher.py`** (pendiente 7 de `proximas-tareas.md`) (~15 min)
  - **RF:** RF-1 (refactor, sin cambio de comportamiento)
  - **Depende de:** D1
  - **Hecho cuando:** `grep -rn "respuesta_prueba.json\|escribir_ciudad_pais" src/` no da resultados y `python3 -m pytest test/ -q` queda verde tras adaptar `test_api_searcher.py`.

## Bloque E — Evaluador Gemini (`src/services/ai_evaluator.py`)

- [ ] **E1. Reintentos con backoff exponencial** (timeout, error temporal, 5xx, respuesta inválida) con intentos desde `settings` (~25 min)
  - **RF:** RF-7, RF-9, RF-10
  - **Depende de:** A1, B2
  - **Hecho cuando:** mock que falla 2 veces y luego responde válido → se retornó el lote tras 3 llamadas; con respuesta siempre inválida se agotan los intentos.
- [ ] **E2. Fallo de lote explícito** (`logging`, propagar a la capa superior, sin `print`, sin evaluaciones parciales) (~15 min)
  - **RF:** RF-7
  - **Depende de:** E1
  - **Hecho cuando:** `grep -n "print(" src/services/ai_evaluator.py` no da resultados y un lote fallido lanza excepción que el orquestador puede detectar antes de persistir.

## Bloque F — Orquestador de integración

- [ ] **F1. `src/orchestrator/integracion_orchestrator.py`: búsqueda → persistir hospedajes → evaluación en lote** (~30 min)
  - **RF:** RF-1, RF-4, RF-5
  - **Depende de:** C1, D3, B2
  - **Hecho cuando:** con mocks de SerpAPI y Gemini, el flujo deja N filas en `hospedajes` con ID real y hace exactamente 1 llamada a Gemini.
- [ ] **F2. Persistir evaluaciones con mapeo `id_temporal` → `hospedaje_id`** y abortar si el lote falló (~20 min)
  - **RF:** RF-7, RF-8
  - **Depende de:** F1, C2
  - **Hecho cuando:** cada fila de `evaluaciones_ia` tiene `hospedaje_id` FK correcta y 0 filas cuando el lote de IA falla.
- [ ] **F3. Caso límite: sin resultados** (~10 min)
  - **RF:** RF-1
  - **Depende de:** F1
  - **Hecho cuando:** mock con `properties: []` → el orquestador retorna `[]`, con 0 llamadas a Gemini y 0 filas nuevas.

## Bloque G — Fixtures y tests (uno por nivel/archivo)

- [ ] **G1. Fixtures SerpAPI en `test/fixtures/`** (`hospedaje_completo`, `hospedaje_sin_resenas`, `serpapi_rate_limit_429`, `serpapi_paginacion_multiple`, `busqueda_sin_resultados`) (~25 min)
  - **RF:** RF-11
  - **Depende de:** D3
  - **Hecho cuando:** los 5 JSON cargan con `json.load` y contienen las claves que consumen `api_searcher`.
- [ ] **G2. Fixtures Gemini** (`gemini_respuesta_valida`, `gemini_respuesta_invalida`) (~15 min)
  - **RF:** RF-11
  - **Depende de:** B2
  - **Hecho cuando:** la válida pasa `LoteEvaluacionesIA.model_validate_json` y la inválida lanza `ValidationError`.
- [ ] **G3. `test/test_config_settings.py`** (~10 min)
  - **RF:** RF-10
  - **Depende de:** A1
  - **Hecho cuando:** cambiar una variable de entorno en la prueba cambia el valor leído sin tocar código.
- [ ] **G4. `test/test_api_searcher.py` — búsqueda y límites** (~25 min)
  - **RF:** RF-1, RF-3
  - **Depende de:** D2, G1
  - **Hecho cuando:** cubre resultados válidos, ausencia de resultados, corte por `max_pages` y por `max_results`, y `python3 -m pytest test/test_api_searcher.py -q` está verde.
- [ ] **G5. `test/test_api_searcher.py` — rate limit y reintentos** (~25 min)
  - **RF:** RF-2, RF-9
  - **Depende de:** D3, G1
  - **Hecho cuando:** cubre 429 con recuperación, 429 con agotamiento conservando acumulados y límite de RPS, y el archivo está verde.
- [ ] **G6. `test/test_ai_evaluator.py` — lote y validación** (~25 min)
  - **RF:** RF-5, RF-6
  - **Depende de:** B2, E1, G2
  - **Hecho cuando:** cubre 1 llamada por lote, respuesta válida, respuesta inválida y hospedaje sin reseñas, con el archivo en verde.
- [ ] **G7. `test/test_ai_evaluator.py` — reintentos y fallo de lote** (~20 min)
  - **RF:** RF-7
  - **Depende de:** E2, G2
  - **Hecho cuando:** cubre agotamiento de reintentos y la no creación de evaluaciones parciales, con el archivo en verde.
- [ ] **G8. `test/test_hospedaje_repository.py` + `test/test_evaluacion_ia_repository.py`** (BD de pruebas) (~30 min)
  - **RF:** RF-4, RF-8
  - **Depende de:** C1, C2
  - **Hecho cuando:** `python3 -m pytest test/test_hospedaje_repository.py test/test_evaluacion_ia_repository.py -q` verde contra `destino3_test_db`, con IDs reales y FK correcta.
- [ ] **G9. `test/test_integracion_flujo_completo.py`** (mocks + BD de pruebas) (~30 min)
  - **RF:** RF-1 a RF-8, RF-11
  - **Depende de:** F3, G4, G5, G6, G7, G8
  - **Hecho cuando:** búsqueda simulada → hospedajes persistidos → evaluación simulada en lote → evaluaciones persistidas corre en verde sin tocar APIs reales.
- [ ] **G10. Checklist de criterios de finalización** (~15 min)
  - **RF:** RF-11 (cobertura completa)
  - **Depende de:** G9
  - **Hecho cuando:** los 8 casos mínimos de la spec (completo, sin reseñas, IA válida, IA inválida, 429, agotamiento de reintentos, sin resultados, límite de paginación) tienen al menos una prueba que falla si se elimina.

## Bloque H — Cierre de Fase 3.4

- [ ] **H1. Barrido de `print()` → `logging` y sin exponer claves** en `src/` (~20 min)
  - **RF:** RF-9 (NFR Seguridad/Observabilidad)
  - **Depende de:** D4, E2, F2
  - **Hecho cuando:** `grep -rn "print(" src/` no da resultados y ningún log muestra `SERPAPI_KEY`/`GEMINI_API_KEY`.
- [ ] **H2. Suite completa en verde** (~15 min)
  - **RF:** todos
  - **Depende de:** H1, G10
  - **Hecho cuando:** `python3 -m pytest test/` termina sin errores y sin skips por BD inaccesible.
- [ ] **H3. Script `src/demo_integracion.py` + ejecución manual** (~25 min)
  - **RF:** criterio de finalización
  - **Depende de:** H2
  - **Hecho cuando:** `python3 -m src.demo_integracion` imprime hospedajes persistidos y sus evaluaciones contra APIs reales (o avisa explícitamente que faltan credenciales).
- [ ] **H4. Actualizar documentación** (`plan.md` tabla de módulos, `spec.md` §Estado actual, `fases/fase-3.md` tarea 3.4) (~20 min)
  - **RF:** — (documentación viva, constitución #11)
  - **Depende de:** H3
  - **Hecho cuando:** `grep -n "3.4" fases/fase-3.md` aparece marcada como completada y la tabla de módulos de `plan.md` coincide con los archivos reales de `src/`.

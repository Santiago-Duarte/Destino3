# Plan de Implementación — Spec 003: Integración de APIs Externas (SerpAPI + Gemini) y Persistencia

---

## 1. Módulos y Arquitectura

### 1.1 Capas involucradas (según AGENTS.md)
```
modelos → repositories → services → orchestration → config → entry point
```

### 1.2 Módulos nuevos / a modificar

| Módulo | Ruta | Responsabilidad | RFs cubiertos |
|--------|------|-----------------|---------------|
| **Configuración** | `src/config/settings.py` | Carga centralizada de parámetros operativos (timeouts, reintentos, límites de tasa, paginación, claves API) desde variables de entorno | RF-9, RF-10 |
| **Modelo de evaluación IA** | `src/models/evaluacion_ia.py` | Esquema Pydantic `EvaluacionIAOutput` + `LoteEvaluacionesIA` para validar respuesta de Gemini | RF-6 |
| **Cliente SerpAPI** | `src/services/serpapi_client.py` | Búsqueda de hospedajes con paginación, rate limiting, reintentos, manejo HTTP 429 | RF-1, RF-2, RF-3, RF-9 |
| **Evaluador Gemini** | `src/services/gemini_evaluator.py` | Evaluación en lote (batch), validación Pydantic, reintentos con backoff exponencial | RF-5, RF-6, RF-7, RF-9 |
| **Repositorio Hospedajes** | `src/repositories/hospedaje_repository.py` | Persistencia de hospedajes con IDs reales (FK a destinos), transacción única | RF-4 |
| **Repositorio Evaluaciones IA** | `src/repositories/evaluacion_ia_repository.py` | Persistencia de evaluaciones vinculadas a hospedaje_id (solo campos de negocio) | RF-8 |
| **Orquestador de Integración** | `src/orchestrator/integracion_orchestrator.py` | Flujo completo: búsqueda → persistencia hospedajes → evaluación IA batch → persistencia evaluaciones | RF-1 a RF-8, RF-9 |
| **Fixtures de prueba** | `test/fixtures/` | JSONs para: hospedaje completo, sin reseñas, respuesta IA válida/inválida, rate limit 429, paginación | RF-11 |

---

## 2. Modelo de Datos

### 2.1 Tablas existentes (Fase 1) — no se modifican
- `destinos` (id, ciudad, pais, ...)
- `hospedajes` (id, destino_id, nombre, tipo, precio_noche, calificacion, direccion, url_reserva, ...)
- `evaluaciones_ia` (id, hospedaje_id, resumen_ejecutivo, puntos_fuertes, puntos_debiles, score_calidad_precio, ...)
- `atracciones` (id, hospedaje_id, ...)

### 2.2 Modelos de dominio (Pydantic / clases)

| Modelo | Campos | Origen | Persistencia |
|--------|--------|--------|--------------|
| `EvaluacionIAOutput` | `id_temporal: int`, `resumen_ejecutivo: str`, `puntos_fuertes: str`, `puntos_debiles: str`, `score_calidad_precio: int (1-10)` | Respuesta Gemini (validada) | No (solo en memoria) |
| `LoteEvaluacionesIA` | `evaluaciones: List[EvaluacionIAOutput]` | Respuesta Gemini (validada) | No (solo en memoria) |
| `Hospedaje` | `id: int`, `destino_id: int`, `nombre: str`, `tipo: str`, `precio_noche: float`, `calificacion: float`, `direccion: str`, `url_reserva: str` | SerpAPI → BD | `hospedajes` |
| `EvaluacionIA` | `id: int`, `hospedaje_id: int`, `resumen_ejecutivo: str`, `puntos_fuertes: str`, `puntos_debiles: str`, `score_calidad_precio: int` | `EvaluacionIAOutput` + `hospedaje_id` real | `evaluaciones_ia` |

> **Nota**: `id_temporal` es efímero (solo para correlacionar request/response Gemini). Nunca se persiste (AGENTS.md #7).

---

## 3. Decisiones Justificadas

| Decisión | Alternativa descartada | Justificación |
|----------|------------------------|---------------|
| **Batch evaluation (una llamada Gemini para N candidatos)** | Evaluación secuencial (1 llamada por hospedaje) | Reduce latencia total y consumo de tokens; especificado en RF-5 y Estado actual. |
| **Persistencia hospedajes ANTES de evaluación IA** | Evaluar primero, persistir todo al final | Garantiza IDs reales (FK) para `evaluaciones_ia`; evita IDs temporales en BD; consistente con Estado actual y RF-3/RF-4. |
| **Campos de `evaluaciones_ia` solo de negocio** | Incluir tokens, latencia, model_version, metadata técnica | Decisión explícita en Fuera de alcance; simplifica esquema y migraciones. |
| **Prompt y modelo IA hardcoded en esta fase** | Externalizar a config / plantillas | Decisión explícita en Fuera de alcance; reduce alcance y riesgo. |
| **Rate limiting con token bucket simple + headers 429** | Circuit breaker completo / librería externa (tenacity, etc.) | RF-9 pide "límites operativos configurados", no infraestructura compleja; token bucket es ligero y suficiente. |
| **Reintentos con backoff exponencial (base configurable, max 3)** | Reintentos fijos / sin reintentos | RF-2, RF-7, NFR Resiliencia exigen "espera progresiva" y "política limitada". |
| **Validación Pydantic estricta en respuesta Gemini** | Validación manual / sin validación | AGENTS.md #6: "Gemini: entrada/salida estructurada + validación". |
| **Repositorios con SQL crudo (psycopg2)** | ORM (SQLAlchemy, etc.) | AGENTS.md #3: "Repository Pattern: repositories usan SQL crudo". |
| **Tests con unittest + mocks + BD real de pruebas** | pytest fixtures / mocks de BD / solo unit tests | AGENTS.md #9: "unittest + mocks de APIs externas; BD de pruebas para integración". |

---

## 4. Estrategia de Tests

### 4.1 Niveles de prueba

| Nivel | Herramienta | Qué prueba | RFs |
|-------|-------------|------------|-----|
| **Unitario — Servicios** | `unittest.mock` (patch `requests`, `google.genai`) | `SerpAPIClient`: paginación, 429, límites, timeouts, reintentos; `GeminiEvaluator`: batch, validación schema, reintentos, fallo lote | RF-1, RF-2, RF-3, RF-5, RF-6, RF-7, RF-9 |
| **Unitario — Repositorios** | `unittest` + BD real (`destino3_test_db`) | `HospedajeRepository.guardar_varios()` transacción; `EvaluacionIARepository.guardar_varias()` FK correcta | RF-4, RF-8 |
| **Integración** | `unittest` + BD real + mocks servicios | Flujo completo: búsqueda mock → persistencia hospedajes → evaluación mock → persistencia evaluaciones | RF-1 a RF-8, RF-11 |
| **Manual (smoke)** | Script `python3 -m src.demo_integracion` | Contra APIs reales (opcional, con credenciales) | Criterio de finalización |

### 4.2 Fixtures JSON (mínimos requeridos por spec)

| Fixture | Descripción | Usado en |
|---------|-------------|----------|
| `hospedaje_completo.json` | Propiedad SerpAPI con todos los campos (rating, precio, reseñas, amenities) | Unitario SerpAPI, Integración |
| `hospedaje_sin_resenas.json` | Propiedad sin `reviews` ni `overall_rating` | Unitario Gemini, Integración |
| `gemini_respuesta_valida.json` | `LoteEvaluacionesIA` con 3 items válidos | Unitario Gemini, Integración |
| `gemini_respuesta_invalida.json` | JSON sin `score_calidad_precio` o con tipo incorrecto | Unitario Gemini (validación) |
| `serpapi_rate_limit_429.json` | Respuesta HTTP 429 con headers `Retry-After` | Unitario SerpAPI (rate limit) |
| `serpapi_paginacion_multiple.json` | Respuesta con `next_page_token` / múltiples páginas | Unitario SerpAPI (paginación) |
| `busqueda_sin_resultados.json` | `"properties": []` | Unitario SerpAPI, Integración |

### 4.3 Cobertura mínima por RF

| RF | Tipo prueba | Casos clave |
|----|-------------|-------------|
| RF-1 | Unitario + Integración | Parámetros válidos → lista resultados; sin resultados → lista vacía |
| RF-2 | Unitario | 429 → reintentos → éxito / agotamiento → conserva acumulados |
| RF-3 | Unitario | `max_pages=2` → detiene en página 2; `max_results=5` → trunca a 5 |
| RF-4 | Unitario (repo) + Integración | Múltiples hospedajes → todos con `id` real; FK `destino_id` correcta |
| RF-5 | Unitario | Lote de 5 candidatos → 1 llamada Gemini; estructura request correcta |
| RF-6 | Unitario | Respuesta válida → parse OK; inválida → `ValidationError` |
| RF-7 | Unitario | Timeout/5xx → reintentos (max 3) → fallo registrado, sin evaluaciones parciales |
| RF-8 | Unitario (repo) + Integración | Evaluación válida → fila en `evaluaciones_ia` con `hospedaje_id` correcto |
| RF-9 | Unitario | Token bucket respeta `rate_limit_rps`; headers 429 honrados |
| RF-10 | Unitario | Cambio config (timeout, reintentos, max_pages) → comportamiento cambia sin tocar código |
| RF-11 | Integración | Mock SerpAPI + Mock Gemini + BD test → flujo verde |

---

## 5. Secuencia de Implementación Sugerida

| Orden | Tarea | Módulo | Comentario |
|-------|-------|--------|------------|
| 1 | Configuración centralizada | `src/config/settings.py` | Base para todos los servicios |
| 2 | Modelos Pydantic evaluación IA | `src/models/evaluacion_ia.py` | Contrato de validación |
| 3 | Repositorio Hospedajes (persistencia batch) | `src/repositories/hospedaje_repository.py` | RF-4 |
| 4 | Repositorio Evaluaciones IA | `src/repositories/evaluacion_ia_repository.py` | RF-8 |
| 5 | Cliente SerpAPI (paginación, rate limit, reintentos) | `src/services/serpapi_client.py` | RF-1, RF-2, RF-3, RF-9 |
| 6 | Evaluador Gemini (batch, validación, reintentos) | `src/services/gemini_evaluator.py` | RF-5, RF-6, RF-7, RF-9 |
| 7 | Orquestador de Integración | `src/orchestrator/integracion_orchestrator.py` | Une todo el flujo |
| 8 | Fixtures de prueba | `test/fixtures/` | Base para tests |
| 9 | Tests unitarios servicios | `test/test_serpapi_client.py`, `test/test_gemini_evaluator.py` | Mocks externos |
| 10 | Tests unitarios repositorios | `test/test_hospedaje_repository.py`, `test/test_evaluacion_ia_repository.py` | BD real test |
| 11 | Test de integración | `test/test_integracion_flujo_completo.py` | Flujo end-to-end |
| 12 | Script demo manual | `src/demo_integracion.py` | Verificación opcional real |

---

## 6. Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Cambios en respuesta SerpAPI rompen mapeo | Alto | Tests con fixtures versionados; validación defensiva en `crear_lista_hospedajes` |
| Gemini devuelve schema inesperado | Alto | Validación Pydantic estricta + reintentos con prompt correctivo (RF-7) |
| Rate limits más estrictos de lo esperado | Medio | Configurable `rate_limit_rps`, `max_pages`, `max_results`; defaults conservadores |
| Transacción BD falla a medio persistir | Alto | `HospedajeRepository.guardar_varios()` en transacción única; rollback automático |
| Concurrencia rompe token bucket global | Medio | `threading.Lock` en bucket; documentar límite actual (single-process) |

---

## 7. Criterios de Aceptación del Plan

- [ ] Todos los módulos listados existen y compilan (`python3 -m py_compile`).
- [ ] Tests unitarios pasan: `python3 -m unittest discover test/ -v`.
- [ ] Test de integración pasa con BD `destino3_test_db`.
- [ ] Demo manual ejecuta flujo completo contra APIs reales (si hay credenciales).
- [ ] Sin `print()` para errores; uso de `logging` estructurado.
- [ ] Código en español, snake_case/PascalCase, sin hardcoded config en servicios.

# 01. Arquitectura de Módulos y Modelo de Datos

> **Alcance V0:** este documento describe el v1 completo. Los incrementos I1–I4 implementan el corte V0 de [`plan.md`](plan.md): sin caché, sin Routes, sin evaluación ni itinerario con Gemini, y con una sola base de pruebas. Lo diferido se añade en V1.

## 1.1 Arquitectura de Módulos

**Flujo general**

```text
frase en español
    → CLI: lectura y preguntas
    → interpretación + validación
    → planificador
        → destino/ancla (Places)
        → hoteles (SerpAPI)
        → distancias (Routes)
        → presupuesto
        → reseñas (SerpAPI)
        → evaluación de hoteles (Gemini)
        → lugares cercanos (Places)
        → itinerario (Gemini + respaldo determinista)
    → plan en memoria
    → presentador CLI
```

**Capas**

```text
models → repositories → services → orchestrator → config → entry point
```

| Módulo | Responsabilidad | Límite |
|---|---|---|
| `cli/` | Leer la frase, preguntar datos faltantes, mostrar el plan | Único punto de interacción con la persona |
| `config/` | Claves, timeouts, TTL, límites y selección de entorno | No contiene lógica de negocio |
| `models/` | Solicitud, fechas, hotel, reseña, lugar, distancia, itinerario y plan | Modelos del dominio; nunca JSON crudo del proveedor |
| `repositories/` | Persistencia y caché con SQL crudo | Único lugar con SQL |
| `services/` | SerpAPI, Gemini, Places y Routes | Encapsulan URLs, parámetros y respuestas del proveedor |
| `orchestrator/` | Pipeline, cercanía, presupuesto, ranking, caché y degradación | No ejecuta SQL ni llama HTTP directamente |
| `exceptions/` | Errores tipados por configuración, entrada, proveedor y persistencia | Mensajes en español, sin secretos |

**Componentes principales**

- `interpretador_solicitud`: Gemini estructurado + normalizador determinista para fechas, montos y ocupación.
- `resolutor_destino` y `resolutor_ancla`: Places Text Search.
- `buscador_hoteles` y `buscador_resenas`: SerpAPI.
- `calculador_distancias`: Routes `computeRoutes`.
- `buscador_lugares`: Places Nearby Search.
- `evaluador_hoteles_ia` y `generador_itinerario_ia`: Gemini con salida Pydantic.
- `validador_ia`: contrasta citas, IDs y puntajes contra los datos reales.
- `planificador`: ordena las etapas y decide qué hacer ante cada fallo.
- `reglas_cercania`, `reglas_presupuesto`, `ranking`: lógica pura y testeable.
- `politica_cache` y `degradacion`: TTL, respaldo vencido y matriz de fallos.

**Reglas de frontera**

- El CLI no ejecuta SQL ni llama proveedores.
- El orquestador no ejecuta SQL.
- Los repositorios no importan servicios.
- Ningún módulo fuera de `services/` conoce URLs, parámetros o JSON de proveedores.
- Ningún dato de Places se persiste salvo `place_id` y coordenadas.
- Ningún lugar, precio, enlace o cita puede aparecer si no vino de un proveedor o de la caché.

## 1.2 Esquema del Modelo de Datos

**Entidades**

| Tabla | Propósito | Campos clave | Relaciones |
|---|---|---|---|
| `destinos` | Ciudad y país con coordenadas y zona horaria | `id`, `ciudad`, `pais`, `zona_horaria`, `latitud`, `longitud`, `google_place_id` | 1 → N `hospedajes` |
| `hospedajes` | Hoteles reales con precio total y coordenadas | `id`, `nombre`, `precio_noche`, `precio_total`, `moneda`, `noches`, `total_antes_impuestos`, `calificacion`, `estrellas`, `latitud`, `longitud`, `amenidades`, `admite_mascotas`, `url_reserva`, `destino_id`, `google_place_id`, `serpapi_property_token` | N → 1 `destinos`; 1 → 1 `evaluaciones_ia` |
| `evaluaciones_ia` | Evaluación vigente de un hotel | `id`, `resumen_ejecutivo`, `puntos_fuertes`, `puntos_debiles`, `cita_textual`, `score_calidad_precio`, `basada_en_resenas`, `modelo`, `hospedaje_id` | 1 → 1 `hospedajes` |
| `lugares` | Caché de coordenadas de lugares y anclas | `id`, `google_place_id`, `latitud`, `longitud`, `expira_en` | Independiente |
| `cache_api` | Respuestas normalizadas con TTL | `id`, `proveedor`, `operacion`, `clave_hash`, `contenido`, `version_esquema`, `expira_en` | Independiente |

**Relaciones y reglas**

- Un destino tiene muchos hospedajes; un hospedaje pertenece a un destino.
- Un hospedaje tiene una sola evaluación vigente. Una nueva ejecución la reemplaza.
- `lugares` no guarda nombre, calificación, horario, nivel de precio ni reseñas: solo `place_id` y coordenadas durante 30 días.
- `cache_api` guarda hoteles y reseñas normalizados, sin autores de reseñas ni JSON crudo.
- No existen tablas de usuarios, búsquedas, recomendaciones, planes ni historial.
- Restricciones: `google_place_id` único cuando no es nulo; `(destino_id, serpapi_property_token)` único cuando no es nulo; `hospedaje_id` único en evaluaciones; `clave_hash` único en caché; índices por destino, precio, calificación y caducidad.
- Tipos: `NUMERIC(12,2)` para precios en COP, `TIMESTAMPTZ` para auditoría y TTL, `JSONB` para amenidades y contenido normalizado, `DOUBLE PRECISION` para coordenadas.

**Justificación de la persistencia**

- **PostgreSQL** ya es el motor del proyecto, permite TTL con consultas por `expira_en`, `upsert` atómico y aislamiento por entorno sin añadir dependencias.
- **No se usa una base documental ni archivos locales** porque se perdería la transacción, la unicidad y el control de las tres bases.
- **Lo que no se persiste** vive en memoria durante el plan: contenido completo de Places, duraciones de Routes, `id_temporal` de Gemini y la frase original.
- **Tres entornos** comparten esquema: `testing` → `destino3_test_db`, `demo` → `demo_db`, `production` → `destino3_db`. Sin fallback.
- **Migración:** `sql/schema.sql` para bases nuevas y `003_mvp_planificador.sql` aditiva para bases existentes; `atracciones` se retira solo si está vacía.

## 1.3 Decisiones Técnicas Clave y Trade-offs

**D1. Pipeline de etapas en lugar de un orquestador monolítico**
* **Decisión adoptada:** dividir el flujo en etapas con responsabilidades separadas y un `Planificador` que las compone.
* **Alternativa descartada:** un único orquestador que busque, evalúe, persista y presente todo.
* **Justificación técnica:** cada etapa se prueba aislada y la degradación se decide en un solo lugar. A cambio de más módulos, se reduce el acoplamiento y se evita que un fallo de Places arrastre la búsqueda de hoteles.

**D2. El CLI es el único que pregunta**
* **Decisión adoptada:** el CLI valida y repregunta; el planificador recibe una solicitud completa.
* **Alternativa descartada:** el orquestador pregunta durante el flujo.
* **Justificación técnica:** el pipeline queda determinista y testeable sin simular una terminal. El costo es mantener dos contratos, entrada y dominio, pero se evita mezclar interacción con lógica de negocio.

**D3. Interpretación híbrida: Gemini + normalizador determinista**
* **Decisión adoptada:** Gemini extrae destino, ancla y preferencias; el normalizador manda en fechas, montos y ocupación.
* **Alternativa descartada:** confiar toda la interpretación a Gemini o resolverla solo con reglas.
* **Justificación técnica:** las fechas y los montos no pueden depender de la creatividad del modelo. El normalizador es barato, reproducible y sirve de respaldo si Gemini falla; Gemini aporta valor en el lenguaje natural.

**D4. De Places solo se guardan `place_id` y coordenadas**
* **Decisión adoptada:** `lugares` almacena únicamente identificador, latitud, longitud y caducidad.
* **Alternativa descartada:** cachear nombres, calificaciones, horarios y reseñas durante 7 días.
* **Justificación técnica:** cumple la política de Google y evita un riesgo legal. Se pierde ahorro de llamadas, pero el contenido se consulta fresco y el plan siempre refleja el estado actual del lugar.

**D5. Caché en PostgreSQL, no en archivos ni memoria**
* **Decisión adoptada:** `cache_api` y `lugares` con TTL y `upsert`.
* **Alternativa descartada:** archivos JSON locales o `functools.lru_cache`.
* **Justificación técnica:** PostgreSQL comparte caché entre ejecuciones, funciona en los tres entornos y permite respaldo vencido con consultas simples. Los archivos y la memoria se pierden al reiniciar y no ofrecen atomicidad.

**D6. Hoteles sin `max_price`; filtro local por total**
* **Decisión adoptada:** pedir hoteles sin límite de precio y filtrar por `precio_total` antes de impuestos.
* **Alternativa descartada:** enviar `max_price` por noche al proveedor.
* **Justificación técnica:** el presupuesto del viajero es total, no por noche. Enviar `max_price` por noche descartaría hoteles válidos o dejaría pasar hoteles que en total se exceden. El costo es recibir más resultados y filtrar en memoria.

**D7. `upsert` y una evaluación vigente, sin historial**
* **Decisión adoptada:** actualizar hoteles por `google_place_id` o `property_token` y evaluaciones por `hospedaje_id`.
* **Alternativa descartada:** insertar filas nuevas en cada ejecución.
* **Justificación técnica:** evita duplicados y mantiene el esquema simple. Se pierde la comparación entre ejecuciones, que está fuera del alcance del MVP.

**D8. Gemini con salida estructurada y respaldo determinista**
* **Decisión adoptada:** Pydantic en entrada y salida; si Gemini falla o inventa datos, ranking e itinerario deterministas.
* **Alternativa descartada:** texto libre parseado a mano o depender solo del modelo.
* **Justificación técnica:** un ítem inválido no tumba todo el lote y las citas o IDs inventados se descartan. El respaldo garantiza que el plan nunca quede vacío por un fallo del modelo.

**D9. Esquema canónico + migración aditiva**
* **Decisión adoptada:** `schema.sql` para bases nuevas y migración 003 para bases existentes.
* **Alternativa descartada:** recrear las tres bases desde cero.
* **Justificación técnica:** recrear borraría datos y exigiría otra decisión destructiva. La migración aditiva permite aplicar el cambio en `testing`, `demo` y `production` sin perder filas, a cambio de mantener dos caminos coherentes.

**D10. Nearby Search para lugares, Text Search para destino y ancla**
* **Decisión adoptada:** Nearby Search con `includedTypes` y radio para lugares cercanos; Text Search para resolver ciudad y ancla.
* **Alternativa descartada:** usar Text Search para todo o Nearby Search para el ancla.
* **Justificación técnica:** Nearby Search garantiza proximidad y no mezcla relevancia textual; Text Search acepta lenguaje natural y permite validar el tipo del ancla. Cada API se usa para lo que está diseñada.

**D11. Routes por par con prefiltro, sin matriz**
* **Decisión adoptada:** `computeRoutes` por hotel y lugar, con prefiltro haversine y topes de llamadas.
* **Alternativa descartada:** `computeRouteMatrix` o estimar minutos desde la distancia en línea recta.
* **Justificación técnica:** la estimación lineal no cumple el requisito de minutos reales; la matriz añade complejidad y dependencia de una API beta. El prefiltro mantiene el costo y la latencia bajo control.

**D12. Sin tablas de usuarios, planes ni historial**
* **Decisión adoptada:** el plan vive en memoria y solo se persisten hoteles, evaluaciones, lugares y caché.
* **Alternativa descartada:** guardar cada plan para consultarlo después.
* **Justificación técnica:** cumple el alcance «sin login ni historial» y evita PII. Se pierde la posibilidad de reabrir un plan, que no forma parte del MVP.

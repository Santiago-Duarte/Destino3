# 02. Estrategia de Integración y Pruebas

> **Alcance V0:** este documento describe el v1 completo. Los incrementos I1–I4 implementan el corte V0 de [`plan.md`](plan.md): sin caché, sin Routes, sin evaluación ni itinerario con Gemini, y con una sola base de pruebas. Lo diferido se añade en V1.

## 2.1 Estrategia de Integración

### 2.1.1 Cliente HTTP común

- `services/cliente_http.py` centraliza timeouts, reintentos y backoff.
- Reintenta hasta 2 veces (3 intentos) ante 429, 5xx, timeout y error de conexión.
- Respeta `Retry-After`; no reintenta 4xx distintos de 429.
- Redacta `api_key`, `key` y `Authorization` antes de registrar errores.
- Recibe un transporte inyectable para tests sin red.
- Conserva el limitador de SerpAPI (1 RPS). No se añade rate limiting propio de la aplicación.

### 2.1.2 Interpretación y validación

- Gemini `gemini-3.8-flash` con entrada y salida Pydantic.
- El normalizador determinista manda en fechas, montos y ocupación; Gemini en destino, ancla y preferencias.
- Si ambos difieren en un campo numérico, se pregunta.
- No se consulta ningún proveedor de datos antes de completar la solicitud (RF-2).
- La ambigüedad de destino se detecta en la interpretación, no con Places.
- Fuera de alcance: Monserrate, Buritaca, Muralla China, Disneyland, excursiones de día completo y multi-ciudad. Se avisa una vez y no se gastan llamadas extra.

### 2.1.3 Destino y ancla

- **Destino:** Places Text Search con `textQuery="{ciudad}, {pais}"`, `languageCode=es`, `pageSize=5` y campos básicos. Se persiste `google_place_id`, coordenadas y zona horaria.
- **Ancla:** Text Search con `locationBias` circular de 30 km. Se valida distancia y tipo: playa → `beach`/`natural_feature`; ciudad amurallada → `historical_landmark`/`tourist_attraction`; estadio → `stadium`; centro → `tourist_attraction`/`historical_landmark`/`locality`.
- Si hay varios candidatos, se usa el primero por relevancia y se declara.
- Si no se resuelve, cae fuera del destino o el tipo no corresponde, se repregunta sin buscar hoteles.
- Si el viajero elige «sin preferencia», no hay ancla, no se calculan distancias y no se aplica filtro de cercanía.

### 2.1.4 Hoteles

- SerpAPI `google_hotels` con `q`, fechas ISO, `currency=COP`, `adults`, `children`, `children_ages` si se conocen, `hl=es` y `gl=co` solo para Colombia.
- No se envía `max_price`: el presupuesto es total de la estancia.
- Una primera página de 20 resultados; segunda página solo si quedan menos de 3 hoteles tras deduplicar y filtrar.
- `precio_total`: `total_rate.before_taxes_fees` si existe; si no, `rate_per_night.extracted_lowest × noches`. Sin ninguno, el hotel se descarta.
- `precio_noche`: `rate_per_night.extracted_lowest`; es la tarifa más baja y se advierte que el proveedor no declara tipo de habitación.
- `total_antes_impuestos = TRUE`; se advierte que faltan impuestos y tarifas.
- Si la moneda no es COP, el hotel se conserva con `comparable=False` y no se compara con el presupuesto.
- Deduplicación por `google_place_id`, luego `serpapi_property_token`, luego nombre + dirección.
- Sin precio o sin coordenadas se descarta; sin link se conserva con advertencia.
- Persistencia con `upsert` y IDs reales de PostgreSQL.

### 2.1.5 Reseñas

- SerpAPI de reseñas con `property_token`, `hl=es` y orden por relevancia.
- Solo para los hasta 5 finalistas.
- Se guardan texto, calificación, fecha relativa y fuente; **no se guarda el autor**.
- Sin `property_token` o sin reseñas, el hotel se marca «no verificado».
- Caché de 7 días; si falla, se usa la caché vencida si tiene menos de 7 días y se avisa.

### 2.1.6 Distancias

- Routes `computeRoutes` con origen/destino en coordenadas, `travelMode=WALK`, `languageCode=es`, `units=METRIC`.
- Minutos = techo de `duration` en segundos / 60.
- Prefiltro haversine y tope de 20 hoteles para evitar llamadas obvias.
- `DRIVE` solo para los hoteles que se van a mostrar.
- Fallo puntual: ese hotel se descarta. Fallo total: se ordena por distancia en línea recta, se marca «distancia no verificada» y el plan es parcial.
- No se cachean duraciones ni distancias; solo coordenadas.
- Cada tiempo a pie lleva la advertencia de que es una estimación beta.

### 2.1.7 Lugares cercanos

- Places Nearby Search con círculo de 2.000 m (20 min) o 3.000 m (30 min), `includedTypes`, `maxResultCount=20`, `rankPreference=DISTANCE` y `languageCode=es`.
- Campos Enterprise + Atmosphere: `id`, `displayName`, `types`, `location`, `formattedAddress`, `rating`, `userRatingCount`, `regularOpeningHours`, `priceLevel`, `websiteUri`, `googleMapsUri`, `allowsDogs`, `goodForChildren`, `businessStatus`.
- Se excluyen cerrados permanentemente, sin nombre, sin coordenadas, alojamientos y agencias de viaje.
- Restaurante si incluye `restaurant`, `cafe`, `bar`, `bakery` o `meal_takeaway`.
- Si hay menos de 5 lugares o menos de 2 restaurantes, se amplía a 30 minutos y se avisa.
- Si no hay lugares, el plan queda sin itinerario y se advierte.
- De cada lugar se guardan solo `place_id` y coordenadas durante 30 días.

### 2.1.8 Evaluación de hoteles

- Hasta 5 finalistas que cumplen distancia y presupuesto; preselección por calificación descendente, precio ascendente y distancia ascendente.
- Gemini recibe hotel, precio total, amenidades, distancia, mascotas y reseñas reales.
- Salida Pydantic validada ítem por ítem.
- La cita textual debe ser substring de una reseña; si no, se descarta.
- `id_temporal` debe existir en el mapa de finalistas.
- Si Gemini falla, ranking determinista por calificación, precio y distancia.
- Si ningún hotel cabe, no se piden reseñas ni evaluación IA: se muestran los 3 más baratos y cuánto se exceden.

### 2.1.9 Itinerario

- Gemini recibe días, bloques, lista cerrada de lugares (nombre, tipo, coordenadas y horario) y preferencias.
- No se envían calificaciones, reseñas, niveles de precio ni enlaces de Places.
- Valida que cada `lugar_id` exista, que no se repita, que el restaurante vaya en comida y que el lugar esté abierto si hay horario.
- Bloques: mañana, tarde y noche; llegada sin mañana; salida solo con mañana.
- Si Gemini falla o más de la mitad de los bloques son inválidos, se usa el planificador determinista.
- No se inventan precios de comida ni de actividades.

### 2.1.10 Caché

| Dato | TTL | Contenido permitido | Respaldo vencido |
|---|---|---|---|
| Hoteles | 12 h | Lista normalizada de hospedajes | Hasta 7 días, con aviso |
| Reseñas | 7 días | Reseñas normalizadas sin autor | Hasta 7 días, con aviso |
| Destino/ancla | 30 días | `place_id` y coordenadas | No aplica |
| Lugares | 30 días | `place_id` y coordenadas | No aplica |
| Rutas | No se cachea | Solo coordenadas de origen/destino | No aplica |

- Clave: SHA-256 de un JSON canónico con proveedor, operación y parámetros.
- Una entrada corrupta se elimina y se trata como inexistente.
- Places siempre se consulta fresco; nunca se usa contenido vencido.
- La caché no sustituye la validación: lo leído se valida contra el modelo de dominio.

### 2.1.11 Degradación

| Falla | Respuesta |
|---|---|
| Interpretación Gemini | Normalizador determinista; si no alcanza, se pregunta; si no, se aborta |
| Places destino | Se aborta antes de hoteles y se pide reformular |
| Places ancla | Se pide reformular o «sin preferencia»; no se buscan hoteles |
| SerpAPI hoteles | Caché vencida ≤7 días con aviso; si no, se aborta con sugerencias |
| SerpAPI reseñas | Top 3 sin evidencia, marcado «no verificado» |
| Routes puntual | Se descarta ese hotel |
| Routes total | Hoteles por distancia en línea recta, marcados «sin verificar»; plan parcial |
| Places lugares | Plan sin itinerario, parcial con la razón |
| Gemini evaluación | Ranking determinista; reseñas visibles |
| Gemini itinerario | Itinerario determinista con los mismos lugares |
| PostgreSQL caché | Se consulta fresco y se advierte que no se cacheó |
| PostgreSQL persistencia | Plan en memoria con advertencia y salida de plan parcial |
| Moneda distinta de COP | Se muestra y no se compara con el presupuesto |
| Sin hoteles tras filtros | Se aborta con mensaje y sugerencias |
| Ningún hotel cabe | 3 más baratos del conjunto con distancia y excedente |

Ningún fallo se rellena con datos inventados ni se oculta: cada caso agrega una advertencia visible.

### 2.1.12 CLI y errores

- `main.py` configura logging, verifica `sys.stdin.isatty()` y valida `ENVIRONMENT` y claves.
- El lector pregunta solo los campos faltantes o inválidos, en español.
- Acepta `YYYY-MM-DD` y `DD/MM/YYYY`; montos con separadores; «sin preferencia».
- Códigos de salida: `0` completo, `3` parcial, `1` entrada/configuración, `2` fatal, `130` Ctrl+C.
- Errores tipados: configuración, entrada, destino, ancla, SerpAPI, Places, Routes, Gemini, persistencia y caché.
- Cada error lleva `proveedor`, `operacion`, `reintentable`, `mensaje_usuario` y `detalle_tecnico` sin secretos.
- Los lugares muestran la atribución textual «Google Maps» y las atribuciones de terceros.

## 2.2 Pirámide de Tests

### 2.2.1 Niveles

| Nivel | Qué prueba | Proveedores | BD |
|---|---|---|---|
| 1. Unitario puro | Fechas, montos, ocupación, cercanía, presupuesto, ranking, claves de caché, citas e IDs | Ninguno | No |
| 2. Contrato con fixtures | Mapeo de SerpAPI, Places, Routes y Gemini; errores HTTP; Pydantic | Mocks | No |
| 3. Repositorios | `upsert`, FKs, unicidad, TTL, rollback y migración | Ninguno | `destino3_test_db` |
| 4. Pipeline | Frase → plan con todos los proveedores mockeados | Mocks | `destino3_test_db` |
| 5. Smoke manual | CLI real con proveedores reales | Reales | `demo_db` |

La suite automatizada nunca llama APIs reales ni toca `production`.

### 2.2.2 Fixtures mínimas

- `serpapi_hoteles_cop.json`, `serpapi_hoteles_sin_precio.json`, `serpapi_hoteles_otra_moneda.json`.
- `serpapi_resenas.json`, `serpapi_sin_resenas.json`.
- `places_destino.json`, `places_ancla.json`, `places_ancla_fuera.json`.
- `places_nearby.json`, `places_nearby_pocos.json`.
- `routes_walk.json`, `routes_drive.json`.
- `gemini_solicitud.json`, `gemini_solicitud_invalida.json`.
- `gemini_evaluacion.json`, `gemini_evaluacion_cita_falsa.json`.
- `gemini_itinerario.json`, `gemini_itinerario_id_inventado.json`.
- `cache_vencida.json`.

### 2.2.3 Matriz de pruebas por RF

| RF | Casos mínimos |
|---|---|
| RF-1 | Frase completa; destino ambiguo; ancla genérica; mención fuera de alcance; Gemini inválido con fallback |
| RF-2 | Faltan fechas, adultos, presupuesto, ancla o minutos; no se llama a proveedores hasta completar; sin TTY falla |
| RF-3 | Fecha pasada; salida igual o anterior; más de 30 noches; año omitido; conflicto duración/salida; 1 y 30 noches; zona horaria |
| RF-4 | Ancla resuelta; varios candidatos; fuera del destino; tipo incorrecto; Places falla |
| RF-5 | Hoteles en COP; sin precio; sin coordenadas; duplicados; grupo que excede una habitación; sin resultados |
| RF-6 | 10/20/30/45/60; ampliación; 3 más cercanos; sin ancla; Routes puntual y total |
| RF-7 | Total antes de impuestos; solo precio por noche; total igual al presupuesto; ninguno cabe; moneda distinta |
| RF-8 | 5 finalistas; con y sin reseñas; cita válida y falsa; Gemini falla; mascotas con dato, sin dato y `False` |
| RF-9 | ≥5 lugares y ≥2 restaurantes; menos de 5; menos de 2; ampliación a 30; cero lugares; lugar cerrado |
| RF-10 | Llegada/salida; bloques completos; ID inventado; cerrado en el bloque; sin horario; fallback determinista |
| RF-11 | Plan completo; sin itinerario; link faltante; moneda distinta; advertencias visibles |
| RF-12 | Fallo de cada proveedor; caché vencida ≤7 días; caché corrupta; fallo de persistencia; ningún dato inventado |

### 2.2.4 Harness de base de datos

- Reparar `test/db_test_case.py`: eliminar imports de `busqueda`, `recomendacion` y repositorios inexistentes.
- Eliminar la inserción en `usuarios`.
- Mantener `ConexionConSavepoint` para absorber `commit()`, `rollback()` y `close()`.
- Abrir una conexión a `destino3_test_db` por prueba y revertir al final.
- Saltar con `SkipTest` si no hay conexión.
- No ejecutar `TRUNCATE`, `DELETE` masivo, `DROP` ni reinicio de secuencias.

### 2.2.5 Smoke manual

1. Habilitar Places API (New) y Routes API; restringir la clave.
2. Aplicar esquema y migración a `demo_db`.
3. Ejecutar una frase real con 2 adultos, 2 niños, 3 días y 2 noches.
4. Verificar top 3, reseñas, itinerario, links, distancias con aviso beta y presupuesto.
5. Repetir sin ancla y con presupuesto insuficiente.
6. Revisar logs: sin claves, sin autores de reseñas, sin frase original.
7. Anotar latencia y consumo de cuotas.

## 2.3 Matriz RF → Componente

| RF | Componentes responsables | Verificación |
|---|---|---|
| RF-1 | `cli.lector`, `interpretador_solicitud`, `solicitud_viaje`, `resolutor_destino` | Frase completa; ambigüedad antes de datos; destino con Places |
| RF-2 | `cli.lector`, `solicitud_viaje`, `planificador` | Faltantes se preguntan; no hay llamadas antes de completar |
| RF-3 | `fechas_viaje`, `interpretador_solicitud`, `zonas_horarias` | Fechas inválidas se rechazan; año y zona horaria resueltos |
| RF-4 | `resolutor_ancla`, `lugar` | Ancla real; primer candidato declarado; fuera de destino o tipo incorrecto se rechaza |
| RF-5 | `buscador_hoteles`, `hospedaje`, `hospedaje_repository` | COP, fechas, ocupación; descartes y deduplicación |
| RF-6 | `calculador_distancias`, `reglas_cercania`, `distancia` | Escalera; ampliación; 3 cercanos; sin distancia se descarta |
| RF-7 | `reglas_presupuesto`, `buscador_hoteles` | Total antes de impuestos; igual cabe; 3 más baratos con excedente |
| RF-8 | `buscador_resenas`, `evaluador_hoteles_ia`, `validador_ia`, `ranking`, `evaluacion_ia_repository` | Cita real; fortalezas/debilidades; mascotas; «no verificado» |
| RF-9 | `buscador_lugares`, `reglas_cercania` | Umbrales; ampliación; cero lugares sin itinerario |
| RF-10 | `generador_itinerario_ia`, `validador_ia`, `itinerario` | Solo lugares de la lista; horarios; IDs inventados descartados |
| RF-11 | `cli.presentador`, `reglas_presupuesto`, `plan_viaje` | Top 3, itinerario, links, presupuesto y advertencias |
| RF-12 | `cliente_http`, `politica_cache`, `cache_repository`, `degradacion` | Fallos degradados; caché vencida/corrupta; sin datos inventados |

## 2.4 Secuencia de Implementación

| Fase | Objetivo | Entregables |
|---|---|---|
| 0 | Puesta a cero | Suite en verde; harness reparado; imports muertos; `.env.example` alineado; `settings` y `main` mínimos |
| 1 | Dominio y datos | Modelos; `schema.sql`; migración 003; repositorios con `upsert` y caché; tests |
| 2 | Infraestructura | `cliente_http`; errores tipados; settings de Places/Routes/Gemini; fixtures |
| 3 | Interpretación y CLI | Interpretador; validador; lector; presentador inicial; tests de fechas y montos |
| 4 | Destino, ancla y hoteles | Resolutores; buscador de hoteles; mapeo; deduplicación; tests de contrato |
| 5 | Distancias y presupuesto | Calculador; reglas de cercanía; reglas de presupuesto; ranking base |
| 6 | Reseñas y evaluación IA | Buscador de reseñas; evaluador; validador; ranking final; persistencia |
| 7 | Lugares e itinerario | Buscador de lugares; generador; planificador determinista; presentador completo |
| 8 | Degradación y cierre | Matriz de fallos; end-to-end; smoke; README y documentación |

Cada fase termina con `python3 -m pytest test/ -q` en verde.

## 2.5 Riesgos y Criterios de Aceptación

| Riesgo | Mitigación |
|---|---|
| Google cambia Places/Routes | Servicios encapsulados; fixtures; campos mínimos; aviso beta |
| Clave de Google filtrada | `.env` gitignored; redacción en logs; restricción por API y cuota |
| SerpAPI no respeta COP | Se muestra la moneda real y no se compara |
| Cuota de SerpAPI Free | Caché 12 h; segunda página solo si faltan hoteles; degradación |
| Grupo que excede una habitación | Una búsqueda con ocupación total; aviso si no hay resultados |
| Ancla ambigua o de otro tipo | Validación de distancia y tipo; repregunta |
| Rutas a pie beta | Advertencia en cada tiempo; se muestra también el auto |
| Gemini inventa datos | IDs cerrados; cita por substring; Pydantic; fallback |
| Latencia por muchas llamadas | Prefiltro haversine; topes; auto solo para los mostrados |
| Caché con contenido de Places | `lugares` solo guarda `id` y coordenadas; tests de columnas |
| Migración con datos | Aditiva, transaccional; `atracciones` vacía o aborta |
| Tests de BD se saltan | `-rs`; unitarios y contrato no dependen de PostgreSQL; smoke manual |

**Criterios de aceptación**

- [ ] Cada RF tiene componente y verificación.
- [ ] El esquema no persiste contenido de Places ni PII de reseñas.
- [ ] Las tres bases comparten esquema y están aisladas por `ENVIRONMENT`.
- [ ] No se consultan proveedores antes de completar la solicitud.
- [ ] Ningún lugar del itinerario existe fuera de la lista consultada.
- [ ] Ninguna cita existe fuera de una reseña real.
- [ ] Cada fallo se degrada sin inventar datos.
- [ ] La suite no llama APIs reales ni toca `production`.
- [ ] La Fase 0 deja la suite en verde.

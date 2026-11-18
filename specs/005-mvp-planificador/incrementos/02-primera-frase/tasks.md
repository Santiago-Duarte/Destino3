# Tasks — I2 · Primera frase (V0)

Objetivo del incremento: convertir una frase en una solicitud validada y en hoteles reales en COP.

- Spec del incremento: [`spec.md`](spec.md)
- Requisitos: [`../../spec.md`](../../spec.md) (los RF se citan, no se redefinen)
- Plan técnico: [`../../01-arquitectura-y-modelo-datos.md`](../../01-arquitectura-y-modelo-datos.md) y [`../../02-integracion-y-pruebas.md`](../../02-integracion-y-pruebas.md)
- Índice general: [`../../tasks.md`](../../tasks.md)

## Convenciones

- IDs locales del incremento (`I2-NNN`); las dependencias de incrementos anteriores se citan con su ID completo.
- Cada tarea dura **≤ 60 minutos**, declara su **RF** y tiene un **Hecho cuando** binario y verificable.
- `Depende` lista solo la dependencia técnica que bloquea, no todas las anteriores.
- Prohibido marcar tests como `skip` para pasar o tocar `production` desde la suite.

## Resumen

| Fase | Tasks | Min |
|---|---|---|
| 2. Infraestructura | 8 | 280 |
| 3. Interpretación y CLI | 7 | 310 |
| 4. Destino, ancla y hoteles | 6 | 275 |
| **Total** | **21** | **865** |

**Gates del incremento:** `I2-008`, `I2-021`

---

## Fase 2 — Infraestructura (I2)

- [ ] **I2-001 · Jerarquía de errores tipados** — 40 min · RF-12 · Depende: I1-021
  - **Hecho cuando:** `python3 -c "from src.exceptions import ErrorProveedor; e=ErrorProveedor(proveedor='serpapi', operacion='hoteles', reintentable=True, mensaje_usuario='x'); print(sorted(e.a_dict().keys()))"` incluye `proveedor`, `operacion`, `reintentable`, `mensaje_usuario` y `detalle_tecnico`.

- [ ] **I2-002 · Tests de errores sin secretos** — 25 min · RF-12 · Depende: I2-001
  - **Hecho cuando:** `python3 -m pytest test/test_errores_tipados.py -q` devuelve `0 failed` y verifica que un mensaje con `api_key=ABC` sale redactado.

- [ ] **I2-003 · `cliente_http` con reintentos, backoff y redacción** — 55 min · RF-12 · Depende: I2-001
  - **Hecho cuando:** `python3 -m pytest test/test_cliente_http.py -q` devuelve `0 failed` con 3 intentos ante 429/5xx, 1 intento ante 400, respeto de `Retry-After` y `api_key` redactada.

- [ ] **I2-004 · Tests del cliente HTTP con transporte falso** — 45 min · RF-12 · Depende: I2-003
  - **Hecho cuando:** `python3 -m pytest test/test_cliente_http.py -q` cubre éxito, 429, 500, timeout, error de conexión y 4xx no reintentable, con `0 failed` y sin red real.

- [ ] **I2-005 · Fixtures de hoteles y reseñas** — 35 min · RF-5, RF-8 · Depende: I1-011
  - **Hecho cuando:** existen `test/fixtures/serpapi_hoteles_cop.json`, `serpapi_hoteles_sin_precio.json`, `serpapi_hoteles_otra_moneda.json`, `serpapi_resenas.json` y `serpapi_sin_resenas.json`, y todos cargan con `json.load`.

- [ ] **I2-006 · Fixtures de Places** — 30 min · RF-4, RF-9 · Depende: I1-011
  - **Hecho cuando:** existen `places_destino.json`, `places_ancla.json`, `places_ancla_fuera.json`, `places_nearby.json` y `places_nearby_pocos.json`, y todos cargan con `json.load`.

- [ ] **I2-007 · Fixtures de interpretación y loader** — 30 min · RF-1, RF-12 · Depende: I1-011
  - **Hecho cuando:** existen `gemini_solicitud.json` y `gemini_solicitud_invalida.json`; `python3 -c "from test.fixtures.loader import cargar, transporte_falso; print(len(cargar('serpapi_hoteles_cop.json')['properties']))"` imprime un entero mayor que 0.

- [ ] **I2-008 · Gate Fase 2: infraestructura aislada y suite estable** — 20 min · RF-12 · Depende: I2-001–I2-007
  - **Hecho cuando:** `python3 -m pytest test/ -q` devuelve `0 failed, 0 errors` y `grep -rln "requests\.\|urllib\|httpx" src/ | grep -v "^src/services/"` no devuelve resultados.

---

## Fase 3 — Interpretación y CLI (I2)

- [ ] **I2-009 · Normalizador de fechas, montos y ocupación** — 55 min · RF-3 · Depende: I1-012
  - **Hecho cuando:** `python3 -c "from src.orchestrator.normalizador import normalizar_fechas, normalizar_presupuesto, normalizar_ocupacion; print(normalizar_fechas('10/01/2027 al 13/01/2027', zona='America/Bogota').noches, normalizar_presupuesto('2 millones'), normalizar_ocupacion('2 adultos y 2 niños'))"` imprime `3 2000000 (2, 2)` y `python3 -m pytest test/test_normalizador.py -q` devuelve `0 failed`.

- [ ] **I2-010 · `interpretador_solicitud` con Gemini y Pydantic** — 55 min · RF-1 · Depende: I1-012, I2-003, I2-007
  - **Hecho cuando:** `python3 -m pytest test/test_interpretador_solicitud.py -q` devuelve `0 failed` con la fixture válida y produce un `SolicitudViaje` sin campos inventados.

- [ ] **I2-011 · Tests del interpretador y su respaldo** — 45 min · RF-1 · Depende: I2-010
  - **Hecho cuando:** `python3 -m pytest test/test_interpretador_solicitud.py -q` cubre respuesta inválida de Gemini, fallo del proveedor y respaldo por normalizador, con `0 failed`.

- [ ] **I2-012 · Detector de ambigüedad y de menciones fuera de alcance** — 35 min · RF-1, RF-2 · Depende: I2-010
  - **Hecho cuando:** `python3 -c "from src.orchestrator.interpretador_solicitud import clasificar_mencion; print(clasificar_mencion('quiero ir a Monserrate'))"` imprime `fuera_de_alcance` y `python3 -m pytest test/test_ambiguedad_destino.py -q` devuelve `0 failed` con ciudad homónima, Monserrate, Buritacá, Muralla China y Disneyland.

- [ ] **I2-013 · `cli/lector` de datos faltantes** — 50 min · RF-2 · Depende: I1-012, I2-009
  - **Hecho cuando:** `python3 -m pytest test/test_lector.py -q` devuelve `0 failed` con preguntas solo por campos faltantes, `YYYY-MM-DD`, `DD/MM/YYYY`, montos con separadores y «sin preferencia».

- [ ] **I2-014 · Tests del lector y terminal no interactiva** — 35 min · RF-2 · Depende: I2-013
  - **Hecho cuando:** `python3 -m pytest test/test_lector.py -q` cubre `isatty()=False` terminando con error, respuesta inválida repreguntada y fecha pasada rechazada, con `0 failed`.

- [ ] **I2-015 · `cli/presentador` inicial** — 35 min · RF-11 · Depende: I1-014
  - **Hecho cuando:** `python3 -m pytest test/test_presentador_inicial.py -q` devuelve `0 failed` y el texto muestra destino, fechas, ocupación y presupuesto en COP con separadores.

---

## Fase 4 — Destino, ancla y hoteles (I2)

- [ ] **I2-016 · `PlacesClient` con Text Search** — 50 min · RF-1, RF-4 · Depende: I2-003, I2-006
  - **Hecho cuando:** `python3 -m pytest test/test_places_cliente.py -q` devuelve `0 failed` con `places_destino.json` y `places_ancla.json`; la petición incluye `languageCode=es` y `pageSize=5`; cubre respuesta vacía, error 500 y campo faltante.

- [ ] **I2-017 · `resolutor_destino` con persistencia** — 45 min · RF-1 · Depende: I2-016, I1-018
  - **Hecho cuando:** `python3 -m pytest test/test_resolutor_destino.py -q` devuelve `0 failed` y un destino resuelto queda con `google_place_id`, coordenadas y zona horaria guardados.

- [ ] **I2-018 · `resolutor_ancla` con validación de tipo y distancia** — 50 min · RF-4 · Depende: I2-016, I1-013
  - **Hecho cuando:** `python3 -m pytest test/test_resolutor_ancla.py -q` devuelve `0 failed` con playa, ciudad amurallada, estadio, centro y «sin preferencia»; cubre varios candidatos, fuera del destino, tipo incorrecto y fallo de Places.

- [ ] **I2-019 · `buscador_hoteles` con COP y precios** — 55 min · RF-5, RF-7 · Depende: I1-013, I2-003, I2-005
  - **Hecho cuando:** `python3 -m pytest test/test_buscador_hoteles.py -q` devuelve `0 failed` con `precio_total` desde `before_taxes_fees`, respaldo por noches, `comparable=False` en otra moneda, descarte sin precio o sin coordenadas y conservación sin link con advertencia.

- [ ] **I2-020 · Deduplicación y segunda página condicional** — 40 min · RF-5 · Depende: I2-019
  - **Hecho cuando:** `python3 -m pytest test/test_buscador_hoteles.py -q` devuelve `0 failed` con duplicados por `google_place_id`, por `property_token` y por nombre+dirección, y confirma que la segunda página solo se pide con menos de 3 resultados y nunca se piden más de 2 páginas.

- [ ] **I2-021 · Gate Fase 4: hoteles persistidos con IDs reales** — 35 min · RF-5 · Depende: I2-017–I2-020
  - **Hecho cuando:** `python3 -m pytest test/test_flujo_hoteles.py -q` devuelve `0 failed` y el propio test verifica que los hospedajes tienen `id` no nulo y que el conteo dentro de la transacción es mayor que 0.

---

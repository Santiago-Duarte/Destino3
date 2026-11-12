# Investigación técnica — dudas abiertas de la spec 005

- **Rol:** Ingeniero de Investigación Técnica.
- **Fecha de consulta:** 2026-11-02.
- **Alcance:** las dudas de `specs/005-mvp-planificador/spec.md` §9 que dependen de APIs, precios, límites o términos de terceros, más los supuestos de proveedor que la spec da por ciertos y que resultaron relevantes (marcados con `H`). La duda «Actualización de contexto» no es externa y queda fuera de esta investigación. No se investigan requisitos internos ni decisiones de producto.
- **Método:** únicamente documentación oficial de SerpApi, Google Maps Platform y Google Gemini. Si la documentación no responde, se marca «no confirmado»; no se completa con memoria ni con guías de terceros.
- **Certeza:** `confirmado` = el hecho está escrito explícitamente en la fuente; `parcial` = la fuente cubre solo parte del caso o hay una laguna; `no confirmado` = la fuente no lo trata.

## 1. Tabla de hallazgos

| # | Duda | Hecho | Fuente (URL) | Fecha de consulta | Certeza |
|---|---|---|---|---|---|
| D1.1 | Composición del total del proveedor | `total_rate` expone `before_taxes_fees` y `after_taxes_fees`; este último se define como «Total rate including taxes and fees for the entire trip». | https://serpapi.com/google-hotels-properties | 2026-11-02 | confirmado |
| D1.2 | Composición del total del proveedor | `display_price` «may be before or after tax depending on the search location»; el campo no indica por sí mismo si incluye impuestos. | https://serpapi.com/google-hotels-properties | 2026-11-02 | confirmado |
| D1.3 | Composición del total del proveedor | En el listado (`engine=google_hotels` con `q`), el ejemplo de respuesta solo muestra `before_taxes_fees` dentro de `rate_per_night` y `total_rate`; no se documenta `after_taxes_fees` para el listado. | https://serpapi.com/google-hotels-api | 2026-11-02 | parcial |
| D1.4 | Composición del total del proveedor | No hay campo documentado de tipo de habitación en `rate_per_night`, `total_rate` ni `prices[]`; `prices[]` solo expone `source`, `logo`, `num_guests` y tarifas. | https://serpapi.com/google-hotels-api · https://serpapi.com/google-hotels-properties | 2026-11-02 | no confirmado |
| D2.1 | Campos de lugares | `rating`, `userRatingCount`, `regularOpeningHours`, `priceLevel`, `websiteUri` y `nationalPhoneNumber` activan el SKU Nearby Search Enterprise; `allowsDogs` y `goodForChildren` activan Enterprise + Atmosphere. | https://developers.google.com/maps/documentation/places/web-service/data-fields · https://developers.google.com/maps/documentation/places/web-service/nearby-search | 2026-11-02 | confirmado |
| D2.2 | Costos de lugares | Nearby Search: Pro 5.000 eventos gratis/mes y $32 por 1.000; Enterprise 1.000 gratis/mes y $35 por 1.000; Enterprise + Atmosphere 1.000 gratis/mes y $40 por 1.000. | https://developers.google.com/maps/billing-and-pricing/pricing | 2026-11-02 | confirmado |
| D2.3 | Campos de lugares | Nearby Search (New) no acepta consulta de texto libre: sus filtros son tipos (`includedTypes`), círculo (`locationRestriction`) y `maxResultCount` de 1 a 20; no hay `pageToken`. | https://developers.google.com/maps/documentation/places/web-service/nearby-search | 2026-11-02 | confirmado |
| D2.4 | Campos de lugares | Text Search (New) sí acepta `textQuery` y devuelve hasta 20 resultados por página con `nextPageToken`; Pro 5.000 gratis/mes y $32 por 1.000; Enterprise 1.000 gratis/mes y $35 por 1.000. | https://developers.google.com/maps/documentation/places/web-service/text-search · https://developers.google.com/maps/billing-and-pricing/pricing | 2026-11-02 | confirmado |
| D2.5 | Campos de lugares | El radio de `locationRestriction.circle` va de 0 a 50.000 metros. | https://developers.google.com/maps/documentation/places/web-service/nearby-search | 2026-11-02 | confirmado |
| D2.6 | Costos de lugares | El cobro depende del `X-Goog-FieldMask`: no hay lista de campos por defecto y cada campo pedido sube de SKU. | https://developers.google.com/maps/documentation/places/web-service/nearby-search | 2026-11-02 | confirmado |
| D3.1 | Persistencia de lugares | «You must not pre-fetch, cache, or store Places API content beyond the allowed exceptions, although the place_id is exempt from caching restrictions». | https://developers.google.com/maps/documentation/places/web-service/policies | 2026-11-02 | confirmado |
| D3.2 | Persistencia de lugares | De Places solo se pueden cachear latitud y longitud hasta 30 días consecutivos; el `place_id` se puede guardar indefinidamente. | https://cloud.google.com/maps-platform/terms/maps-service-terms (14.3 y 3) | 2026-11-02 | confirmado |
| D3.3 | Persistencia de lugares | Los términos generales prohíben pre-cargar, indexar, almacenar, recompartir o rehospedar contenido de Google Maps, y cachear salvo lo permitido en los términos específicos. | https://cloud.google.com/maps-platform/terms (3.2.3) | 2026-11-02 | confirmado |
| D3.3b | Uso del contenido con un modelo de lenguaje | Los términos prohíben usar contenido de Google Maps para entrenar, probar, validar o ajustar modelos de IA, y prohíben rehospedar o recompartir el contenido; no dicen nada explícito sobre enviarlo a un modelo de lenguaje de terceros para redactar. | https://cloud.google.com/maps-platform/terms (3.2.3.c.vii) | 2026-11-02 | no confirmado |
| D3.4 | Atribución de lugares | Sin mapa, los datos de Places deben mostrarse con el logo o el texto «Google Maps» y las atribuciones de terceros; con mapa, sobre un mapa de Google. | https://developers.google.com/maps/documentation/places/web-service/policies | 2026-11-02 | confirmado |
| D3.5 | Cumplimiento de Places | Las aplicaciones que usan Places API deben publicar términos de uso y política de privacidad accesibles que incorporen los de Google; los términos generales añaden que el servicio debe avisar que incluye funciones de Google Maps y remitir a los términos y la política de Google. | https://developers.google.com/maps/documentation/places/web-service/policies · https://cloud.google.com/maps-platform/terms (3.2.2) | 2026-11-02 | confirmado |
| D3.6 | Persistencia de hoteles | SerpApi no documenta permiso para almacenar resultados; sus términos prohíben «reproduce, duplicate, copy, sell, resell or exploit any portion of the Service» sin permiso escrito. | https://serpapi.com/legal | 2026-11-02 | parcial |
| D4.1 | COP en hoteles | `currency` acepta códigos de la lista oficial de Google Travel, que incluye `COP`. | https://serpapi.com/google-travel-currencies · https://serpapi.com/google-hotels-api | 2026-11-02 | confirmado |
| D4.2 | COP en hoteles | No se documenta ninguna restricción de moneda por destino ni se garantiza que COP esté disponible para todos los destinos. | https://serpapi.com/google-hotels-api · https://serpapi.com/google-travel-currencies | 2026-11-02 | no confirmado |
| D4.3 | Ocupación de grupo | La ocupación se envía con `adults`, `children` y `children_ages`; no existe parámetro de número de habitaciones para hoteles (`bedrooms` y `bathrooms` son solo para Vacation Rentals). | https://serpapi.com/google-hotels-api | 2026-11-02 | confirmado |
| D4.4 | Ocupación de grupo | No se documenta qué devuelve el proveedor cuando la ocupación supera la capacidad de una habitación. | https://serpapi.com/google-hotels-api | 2026-11-02 | no confirmado |
| D5.1 | Modelo de lenguaje | `gemini-3.8-flash` es el Flash más reciente; `gemini-3.6-flash` sigue disponible como generación anterior estable; `gemini-2.5-flash` está deprecado y redirige a un modelo más nuevo. | https://ai.google.dev/gemini-api/docs/models | 2026-11-02 | confirmado |
| D5.2 | Modelo de lenguaje | `gemini-3.8-flash` y `gemini-3.6-flash` cuestan lo mismo: $0,75 por 1M de entrada y $3,75 por 1M de salida hasta el 31-12-2026; $1,50 y $7,50 desde el 01-01-2027. | https://ai.google.dev/gemini-api/docs/pricing | 2026-11-02 | confirmado |
| D5.3 | Modelo de lenguaje | El nivel gratuito existe, pero «Used to improve our products: Yes»; en el nivel pago es «No». | https://ai.google.dev/gemini-api/docs/pricing | 2026-11-02 | confirmado |
| H1.1 | Rutas a pie | `WALK` está en beta y Google exige mostrar una advertencia al usuario en todas las rutas a pie que se muestren. | https://developers.google.com/maps/documentation/routes/reference/rest/v2/RouteTravelMode | 2026-11-02 | confirmado |
| H1.2 | Costos de rutas | Compute Routes Essentials cuesta $5 por 1.000 con 10.000 eventos gratis/mes; pasa a Pro ($10 por 1.000) si se usa `TRAFFIC_AWARE`. | https://developers.google.com/maps/billing-and-pricing/pricing · https://developers.google.com/maps/documentation/routes/usage-and-billing | 2026-11-02 | confirmado |
| H2.1 | Caché de rutas | De Routes API solo se pueden cachear latitud y longitud hasta 30 días; no se autoriza cachear distancia ni duración. | https://cloud.google.com/maps-platform/terms/maps-service-terms (19.3) | 2026-11-02 | confirmado |
| H3.1 | Caché de SerpApi | SerpApi cachea cada búsqueda 1 hora; las búsquedas servidas desde su caché son gratis y no cuentan contra el plan; `no_cache` lo desactiva. | https://serpapi.com/google-hotels-api | 2026-11-02 | confirmado |
| H3.2 | Límites de SerpApi | El plan Free incluye 250 búsquedas al mes y 50 por hora. | https://serpapi.com/pricing | 2026-11-02 | confirmado |
| H4.1 | Reseñas | La respuesta de reseñas trae `snippet`, `rating`, `date` relativa («2 weeks ago»), usuario y `next_page_token`; `sort_by` admite 1 a 4. | https://serpapi.com/google-hotels-reviews-api | 2026-11-02 | confirmado |
| H4.2 | Reseñas | Las reseñas exigen `property_token`, que se obtiene de Google Hotels Properties. | https://serpapi.com/google-hotels-reviews-api | 2026-11-02 | confirmado |
| H5.1 | Amenidades | En la lista oficial: `11` = Beach access, `12` = Child-friendly, `19` = Pet-friendly. | https://serpapi.com/google-hotels-amenities | 2026-11-02 | confirmado |
| H6.1 | Fechas de hotel | `check_in_date` y `check_out_date` son obligatorios y usan formato `YYYY-MM-DD`. | https://serpapi.com/google-hotels-api | 2026-11-02 | confirmado |

## 2. Fuentes que se contradicen

1. **Crédito de Google Maps.** La página de precios muestra topes gratuitos por SKU (por ejemplo, 5.000 eventos Pro y 1.000 Enterprise al mes), mientras que el resumen automático de la página de facturación de Routes todavía dice: «A $200 monthly credit is available until Feb 28, 2025».
   - https://developers.google.com/maps/billing-and-pricing/pricing
   - https://developers.google.com/maps/documentation/routes/usage-and-billing
2. **Nombres de SKU de Routes.** El texto de la misma página de facturación habla de SKU «Basic, Advanced, or Preferred», pero la tabla y la página de precios usan «Essentials, Pro, Enterprise».
   - https://developers.google.com/maps/documentation/routes/usage-and-billing
   - https://developers.google.com/maps/billing-and-pricing/pricing
3. **Caché de Places.** La página de políticas dice que no se puede cachear «beyond the allowed exceptions» y los términos específicos definen esas excepciones (coordenadas 30 días, `place_id` indefinido). No es una contradicción de fondo, pero la política sola no dice cuáles son las excepciones.
   - https://developers.google.com/maps/documentation/places/web-service/policies
   - https://cloud.google.com/maps-platform/terms/maps-service-terms

## 3. Decisiones tomadas

| Duda | Decisión |
|---|---|
| D1.3 | El presupuesto se compara con el total antes de impuestos del listado y el plan avisa que no incluye impuestos ni tarifas. |
| D1.4 | Se usa la tarifa más baja disponible y se avisa que el proveedor no declara tipo de habitación. |
| D2.1–D2.6 | Places se consulta con Enterprise + Atmosphere. |
| D3.1–D3.3 | De lugares solo se guardan `place_id` y coordenadas; el contenido se consulta fresco en cada plan. |
| D3.3b | A Gemini solo se envían nombre, tipo, coordenadas y horario del lugar. |
| D3.5 | El README avisa que el MVP usa Google Maps y enlaza los términos y la política de privacidad de Google. |
| D4.2 | Se pide COP siempre; si el proveedor devuelve otra moneda, se muestra y se advierte que no se compara con el presupuesto. |
| D4.3–D4.4 | Se mantiene una sola búsqueda con la ocupación total; si no hay resultados, se avisa y se sugiere ajustar el grupo (decisión previa). |
| D5.1–D5.3 | Se fija `gemini-3.8-flash` con nivel gratuito. |
| H1.1 | Cada tiempo a pie se muestra con la advertencia de que es una estimación beta. |
| H2.1 | De rutas solo se guardan coordenadas; la duración se recalcula en cada plan. |
| H3.1–H3.2 | La caché propia de hoteles se mantiene en 12 horas. |
| H4.1 | La fecha de la reseña se muestra tal como la entrega el proveedor. |

## 4. Dudas que siguen abiertas

| Duda | Qué falta | Siguiente paso |
|---|---|---|
| D4.2 | Cobertura real de COP en todos los destinos. | La regla ya está decidida; queda verificar el comportamiento del proveedor antes de la corrida real. |
| D4.4 | Comportamiento del proveedor cuando la ocupación excede una habitación. | La regla ya está decidida; queda verificar el comportamiento antes de la corrida real. |
| D3.6 | Permiso de SerpApi para almacenar resultados. | La caché de hoteles de 12 h y las reseñas de 7 días quedan como riesgo asumido; hay que confirmarlo con SerpApi o aceptarlo explícitamente. |

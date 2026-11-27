# Roadmap de Destino3

Objetivos de evolución del proyecto, ordenados por fases y prioridad.

**Enfoque:** herramienta personal, sólida y precisa en fechas, distancias y precios.
**Fuera de alcance por decisión:** historial de búsquedas, cuentas de usuario, web/API pública.

---

## Punto de partida

Estado del proyecto cuando se escribió este roadmap; la Fase 1 ya está implementada.
El flujo actual funciona de punta a punta (frase → interpretación → SerpAPI → persistencia →
análisis IA → ranking → top 3), pero había tres limitaciones concretas que condicionaban la
precisión:

1. **Fechas fijas.** `consultar_serpapi()` en `src/services/buscador_serpapi.py` usa
   “hoy + 7 días” con 2 noches (comentario `RF-3`). El usuario nunca elige cuándo viaja.
2. **Cercanía sin verificar.** “Cerca del metro” lo juzga el LLM leyendo solo `direccion`
   como texto libre. No hay coordenadas ni cálculo de distancia.
3. **Precio ambiguo.** Se usa `rate_per_night.extracted_lowest` en USD, sin ocupación
   (huéspedes/habitaciones), sin impuestos y descartando hoteles sin tarifa.

Cada fase ataca una de esas brechas.

| Fase | Estado |
|---|---|
| 1. Fechas y ocupación | Implementada |
| 2. Distancias verificables | Implementada |
| 3. Precio y filtros duros | Pendiente |
| 4. Cobertura del catálogo | Pendiente |
| 5. Calidad e infraestructura | Pendiente |

---

## Fase 1 — Fechas y ocupación reales (máxima prioridad) — implementada

Sin esto, todo lo demás compara hoteles en fechas que el usuario no eligió.

| # | Objetivo | Por qué | Esfuerzo |
|---|---|---|---|
| 1.1 | Extraer `fecha_entrada` y `fecha_salida` de la frase | Hoy están hardcodeadas; la URL de reserva miente | M |
| 1.2 | Validar fechas: no pasadas, salida > entrada, estancia máxima | Evita consultas inválidas y resultados basura | S |
| 1.3 | Preguntar adultos, niños y mascotas cuando la frase no lo diga (`adults`, `children`, `amenities` en SerpAPI) | El precio actual es por habitación sin ocupación definida | S |
| 1.4 | Mostrar la interpretación y confirmar solo si falta o es ambiguo algún dato | Ahorra créditos sin añadir fricción en búsquedas claras | S |
| 1.5 | Propagar fechas a `_parametros_de_busqueda` y a `construir_url_reserva` | Que el link de reserva coincida con la búsqueda | S |

**Decisión tomada:** si la frase no trae fechas, se piden por consola con un default de
próximo fin de semana (viernes a domingo, 2 noches) que se acepta con Enter. La ocupación
(adultos, niños y mascotas) se pregunta siempre que falte, porque cambia el precio y los
resultados de forma directa.

**Implementación:** `src/cli/fechas.py` (parseo y validación), `src/cli/prompts.py`
(interacción), `src/models/interpretacion.py` (salida del modelo) y
`src/models/busqueda.py` (especificación). SerpAPI recibe `check_in_date`,
`check_out_date`, `adults`, `children` y, si aplica, `amenities=19` (Pet-friendly).

---

## Fase 2 — Distancias verificables (lo que más se nota) — implementada

El mayor salto de calidad: pasar de “la IA cree que está cerca” a “está a 640 m”.

| # | Objetivo | Por qué | Esfuerzo |
|---|---|---|---|
| 2.1 | Guardar `lat`/`lon` del hotel desde `gps_coordinates` de SerpAPI | Base para cualquier cálculo real | S |
| 2.2 | Geocodificar el punto pedido (“metro”, “centro”, “playa”, “aeropuerto”) | Convierte una preferencia vaga en un punto | M |
| 2.3 | Calcular distancia real (haversine) y mostrar km + minutos a pie | Dato objetivo, no opinión del modelo | S |
| 2.4 | Pasar la distancia ya calculada al evaluador y mostrarla | El LLM solo interpreta; no inventa geografía | S |
| 2.5 | Filtro de radio solo cuando la frase lo pida (“a menos de 1 km”) | Requisito duro sin descartar hoteles por defecto | S |
| 2.6 | Persistir coordenadas en `hospedajes` | Se reutilizan entre búsquedas sin volver a geocodificar | S |

**Decisión tomada:** geocodificación con **Nominatim/OSM**, respetando su límite de 1 req/s
y guardando las coordenadas resueltas para no repetir consultas.

---

## Fase 3 — Precio y filtros duros

| # | Objetivo | Por qué | Esfuerzo |
|---|---|---|---|
| 3.1 | Comparar, ordenar y aplicar el presupuesto sobre el **total de la estancia con impuestos** | Hoy se compara pera con manzana | S |
| 3.2 | Mostrar en pantalla el total de la estancia y el precio por noche | Es lo que el usuario realmente paga | S |
| 3.3 | Moneda tomada de la frase, con USD por defecto (`currency` en SerpAPI) | Todo está forzado a USD | S |
| 3.4 | Listar aparte los hoteles sin tarifa, marcados como “sin precio” | Hoy se descartan en silencio | S |
| 3.5 | Filtros estructurados: estrellas, desayuno, cancelación gratis, tipo, rating mínimo | Dejan de depender del juicio del LLM | M |
| 3.6 | Preselección local antes de la IA | Más candidatos evaluados con menos tokens | M |

---

## Fase 4 — Cobertura del catálogo

| # | Objetivo | Por qué | Esfuerzo |
|---|---|---|---|
| 4.1 | Subir a 2 páginas por búsqueda (~40 hoteles), configurable en `.env` | Hoy el top 3 sale de ~20 hoteles | S |
| 4.2 | Deduplicar entre páginas y búsquedas por `google_place_id` | Evita repetidos en el ranking | S |
| 4.3 | Subir `MAX_CANDIDATOS_IA` con preselección local | Mejor top sin explotar el costo | M |

---

## Fase 5 — Calidad e infraestructura

Soporte de las fases anteriores; no aporta features visibles pero habilita el resto.

| # | Objetivo | Por qué | Esfuerzo |
|---|---|---|---|
| 5.1 | Runner de migraciones (`sql/migraciones`) | Se van a añadir columnas; aplicarlas a mano no escala | M |
| 5.2 | Tests deterministas de fechas, distancias y precios | Las fechas relativas a “hoy” rompen tests si no se congelan | S |
| 5.3 | Fixtures reales de SerpAPI con coordenadas y tarifas | Los tests actuales no cubren esos campos | S |
| 5.4 | Versionar el prompt del interpretador | Ya se versiona el análisis (`ANALISIS_VERSION`); falta el de la frase | S |
| 5.5 | Mostrar llamadas, latencia y errores parciales | Saber cuánto cuesta cada búsqueda | S |

---

## Decisiones tomadas

| Tema | Decisión |
|---|---|
| Fechas ausentes en la frase | Se preguntan por consola con default: próximo fin de semana (viernes a domingo) |
| Confirmación antes de buscar | Solo cuando falte o sea ambiguo algún dato |
| Ocupación | Se pregunta siempre que falte: adultos, niños y mascotas |
| Geocodificación del punto de referencia | Nominatim/OSM, 1 req/s, coordenadas guardadas |
| Distancia | Kilómetros + minutos a pie; filtro de radio solo si la frase lo pide |
| Precio comparado | Total de la estancia con impuestos; se muestra también por noche |
| Hoteles sin tarifa | Se listan aparte, marcados como “sin precio” |
| Moneda | La que indique la frase; USD por defecto |
| Créditos SerpAPI por búsqueda | 2 páginas (~40 hoteles), configurable en `.env` |

---

## Orden recomendado

1. **1.1 → 1.5** — fechas y ocupación.
2. **2.1 → 2.4** — distancias reales.
3. **3.1 → 3.4** — precio honesto.
4. **5.1** — runner de migraciones, antes de tocar el esquema otra vez.
5. **3.5 + 4.1** — filtros duros y más catálogo.

Racional: primero se corrige *cuándo* se busca, luego *dónde*, después *cuánto*.
Cada fase mejora la calidad del ranking sin cambiar la arquitectura.

---

## Fuera de alcance (por ahora)

- Historial de búsquedas.
- Web o API: no aportan precisión y multiplican el trabajo.
- Cuentas, planes o multiusuario.
- Caché persistente de búsquedas: con fechas reales la clave cambia tanto que aporta poco.

---

## Escala de esfuerzo

| Talla | Referencia |
|---|---|
| **S** | Menos de medio día; un módulo y sus tests |
| **M** | Uno o dos días; toca modelo, servicio y tests |
| **L** | Varios días; cambio transversal o dependencia externa nueva |

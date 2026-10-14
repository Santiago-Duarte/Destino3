# Contexto v2: fuentes de verdad de Destino3

Léelo completo antes de planear o implementar cualquier spec (004 a 007).
Si algo de este archivo contradice una spec o un plan, gana este archivo,
salvo que Santiago indique lo contrario.

## 1. Principio central

Las APIs y el código aportan los hechos (ubicación, distancia, precio, moneda,
link). El LLM solo interpreta y redacta. El LLM nunca produce ni modifica un número.

## 2. Reglas para el agente

1. Las decisiones de la sección 4 son definitivas. No las reabras.
2. Lo marcado [POR VERIFICAR] no se asume. Si necesitas un dato de una API
   (campos, precios, límites, términos), búscalo en la documentación oficial,
   cita la fuente, o indica que no pudiste confirmarlo.
3. Si algo no está en este archivo ni en la spec, pregunta. No inventes.
4. Credenciales solo en `.env`.
5. Operaciones destructivas sobre la BD real requieren confirmación humana explícita y se marcan
   `[CONFIRMACIÓN HUMANA]` en las tareas. Excepción autorizada solo para la spec 004: el reset total
   de la BD real se ejecuta una única vez, sin respaldo ni confirmación humana (decisión 14). No
   sirve de precedente para ninguna operación futura. Nunca tocar `destino3_test_db` con operaciones
   destructivas de reset. `demo_db` tampoco recibe resets ni borrados de datos desde la aplicación.
6. Tests en `destino3_test_db` usan respuestas grabadas, nunca APIs reales. La demo en `demo_db` usa APIs
   reales y conserva sus resultados; ni tests ni demo usan la BD real.

## 3. Estructura de specs

| Spec | Nombre | Alcance |
|---|---|---|
| 004 | esquema-y-reset-bd | Vaciado único de la BD real (`destino3_db`), esquema común para `destino3_db`/`demo_db`/`destino3_test_db`, unicidad de `google_place_id` (aún nullable: no evita duplicados en filas sin identificador), aislamiento de entornos |
| 005 | ubicacion-places | Ancla, búsqueda de hoteles, filtro por distancia, distancia caminando, contador de cuota. Cierra lo diferido de la 004: `google_place_id` NOT NULL, descarte de hoteles sin identificador y upsert |
| 006 | precios-y-reserva | Precios con SerpApi, cruce con Places, moneda, link de reserva |
| 007 | evaluacion-enriquecida | Evaluación por criterio con evidencia |

Dependencias: 005 depende de 004; 006 de 005; 007 de 005 y 006.
Spec 003 (integración de APIs externas) ya está entregada; no se modifica.
Plan y tareas de 006 y 007 se hacen después de implementar la spec anterior.

## 4. Decisiones cerradas

1. `demo_integracion` solo corre con el entorno `demo`, escribe y conserva sus resultados en
    `demo_db`, y se niega a correr con cualquier otro entorno. `testing` usa `destino3_test_db` y
    `production` usa `destino3_db`; no hay fallback entre bases.
2. `UNIQUE` en hospedajes sobre `google_place_id`. En la spec 004 queda como columna única
   todavía nullable (excepción temporal: aún no existe la fuente del identificador y la demo
   debe seguir persistiendo). Limitación conocida: PostgreSQL trata cada NULL como distinto en
   una restricción única, así que hasta la spec 005 siguen siendo posibles duplicados entre
     filas sin identificador; la demo corre en `demo_db`, donde no importa. La spec 005 cierra
   tres puntos diferidos: `NOT NULL`, descarte de todo hotel sin identificador resoluble e
   `INSERT ... ON CONFLICT DO UPDATE` (upsert).
3. Ubicación con Google Places API (New). Descubrimiento con una Text Search
   (`includedType` lodging, `locationBias` circular sobre el ancla, `pageSize` 20).
   Se acepta que `locationBias` no garantiza el radio: el filtro Haversine en
   código descarta los lejanos. Ruta caminando solo para 3 a 5 finalistas.
4. El LLM convierte las preferencias en un ancla estructurada (lugar, distancia
   máxima, modo de desplazamiento). El ancla se resuelve con Places y se cachea.
   Si no se puede resolver, se avisa al usuario y se le pide reformular, sin
   gastar búsquedas de hoteles.
5. Hotel sin distancia caminando disponible: se descarta cuando el criterio de
   distancia es duro.
6. Precios y links con SerpApi (Google Hotels), solo para candidatos y con fechas
   exactas. Cruce con Places por nombre normalizado y cercanía de coordenadas
   (umbral de referencia: unos 100 m). Sin cruce no hay precio, y el hotel se
   excluye.
7. Presupuesto máximo en la moneda local del destino (ej. COP en Colombia),
   convertido internamente. Conversor con tasa de API cacheada por día. Se guardan
   precio y moneda originales, tasa, fecha de la tasa, precio en dólares, tipo de
   habitación, desayuno incluido, fechas de entrada y salida y cuándo se capturó
   el precio.
8. CLI con `--checkin`, `--checkout` y `--adultos`. Las fechas son obligatorias;
   sin fechas no hay búsqueda.
9. Si ningún finalista cumple el presupuesto, se consulta precio a los siguientes
   candidatos por distancia hasta completar 3, con tope de 8 búsquedas de SerpApi
   por consulta de usuario. Si al llegar al tope no se completan 3, se muestran
   los que haya y se explica por qué no se completaron.
10. Precios de SerpApi cacheados por hotel + fechas durante unas horas
    (duración configurable).
11. **Control de cuota:** un contador por proveedor y tipo de llamada, con corte
    al 80% del límite gratuito de cada uno. Cubre Places (búsqueda y detalle),
    rutas (distancia caminando) y SerpApi (precios). Los límites se leen de
    configuración, no de valores fijos en el código; los de rutas y SerpApi se
    confirman en la verificación de APIs. Degradación de nivel configurable
    (`PLACES_NIVEL=atmosphere|pro`), cuota diaria en Google Cloud y alerta de
    presupuesto.
12. Link de reserva: deep link con fechas prefijadas; la tarjeta muestra la
    habitación y tarifa exactas recomendadas. El link directo por API de socios
    queda para la Fase 2.
13. Evaluación IA por criterio con veredicto y evidencia. Si falta el dato:
    "no verificado". Fortalezas, debilidades y resumen con longitud mínima medible
    en palabras Y en datos verificados citados (valores a fijar en la spec 007).
    El veredicto por criterio se guarda en la BD.
14. Reset total de la BD real: se ejecuta dentro de la spec 004, UNA SOLA VEZ, sin respaldo y sin
    confirmación humana, por decisión explícita de Santiago. Los datos existentes son de prueba y se
    descartan íntegramente (se vacían todas las tablas conservando la estructura, sin excepciones).
    Orden en la BD real: primero se vacía y después se aplica el esquema nuevo. No es un precedente:
    no se repite ni se extiende a otras specs. La verificación posterior comprueba solo que la BD
    real quedó vacía. El esquema con unicidad de hoteles entra en la misma spec 004. Las specs 006 y
     007 añaden sus propias migraciones; no hay migración única del esquema futuro.
15. Las tres bases viven en la misma instancia de PostgreSQL y usan roles de acceso independientes.
    La infraestructura las provisiona; la aplicación no crea bases ni credenciales. Las
    actualizaciones de esquema pueden aplicarse en las tres, pero no se permiten resets ni borrados
    de datos en `demo_db` o `destino3_test_db`. Un entorno inválido termina con error y no selecciona una base
    por defecto.

## 5. Datos de proveedores (confirmar antes de decidir costos)

Verificado en documentación oficial parcial y guías de terceros:
- Text Search Pro: 32 USD por 1.000 solicitudes, 5.000 gratis al mes.
- Text Search con solo IDs: gratis e ilimitada. Pedir `displayName` sube a Pro.
- `rating` y `websiteUri` pertenecen al nivel Enterprise.
- Incluir un campo de reseñas o fotos reclasifica la llamada a
  Enterprise + Atmosphere (alrededor de 40 USD por 1.000, 1.000 gratis al mes;
  confirmar).
- Google cobra por el campo más caro de la máscara; usar `X-Goog-FieldMask`
  estricta.
- `locationBias` y `locationRestriction` no se usan a la vez.
- SerpApi: plan gratuito de 250 búsquedas al mes y pago desde 25 USD por 1.000
  (las guías de terceros no coinciden; confirmar en serpapi.com/pricing).
  SerpApi no es API oficial de Google.

## 6. [POR VERIFICAR] (se cierran con documentación oficial)

- Campos de Places por nivel de cobro y precios vigentes.
- Ubicación en Essentials de Place Details.
- SKU y precio de la API de rutas para distancia caminando, y proveedor.
- Plan, límites y términos vigentes de SerpApi, incluido uso comercial.
- Si SerpApi permite pedir precios directamente en la moneda local.
- Formato del deep link de reserva por proveedor (probar a mano).
- Qué contenido de Places se puede persistir y por cuánto tiempo (referencia:
  `place_id` indefinido, latitud y longitud hasta 30 días; nombre, dirección y
  reseñas sin confirmar).
- Nombre válido del modelo de Gemini (`gemini-3.6-flash` aparece en el log).

## 7. Caché

- Identificador del lugar: sin caducidad.
- Dirección y coordenadas: con fecha de actualización, refresco pasados 30 días.
- Reseñas: no se persisten en bruto; se entregan al modelo en el momento.
- Precios: ver decisión 10.

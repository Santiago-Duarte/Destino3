# Spec 005 — MVP Planificador de Viaje

- **Spec:** 005-mvp-planificador
- **Objetivo:** convertir una frase en español en un plan de viaje completo y verificable —hotel recomendado, planes cercanos, itinerario día a día y encaje de presupuesto— sin cuentas, historial ni frontend.
- **Incluye:** interpretación de la frase; fechas obligatorias; presupuesto total en COP; ancla genérica con filtro por minutos caminando; hoteles reales con reseñas; top 3 con evidencia; restaurantes y planes cercanos; itinerario día a día; links de reserva y mapa; caché con caducidad; degradación controlada ante fallos.
- **No incluye:** login, usuarios, historial, web, pagos, vuelos o transporte, precios inventados de comida o actividades, lugares que requieran transporte o día completo (Monserrate, Buritaca, Muralla China, Disneyland y equivalentes), viajes multi-ciudad.
- **Depende de:** spec 004 (esquema y aislamiento de las tres bases).
- **Sustituye:** el alcance funcional de la spec 003 y las decisiones 3, 6, 7, 8, 9 y 11 del contexto v2; la decisión 15 se mantiene. Requiere que el usuario actualice `docs/contexto-v2-fuentes-de-verdad.md`, la constitución #1 y `fases/` para que no queden reglas contradictorias.
- **Dudas abiertas:** cobertura real de COP por destino, comportamiento del proveedor con grupos que exceden una habitación y permiso de SerpApi para almacenar resultados [POR VERIFICAR]; el resto quedó resuelto en `investigacion.md`.

## 1. Contexto y objetivo

Hoy el sistema pide ciudad, país, presupuesto y preferencias por separado, no usa fechas ni ocupación real, no lee reseñas y no produce un plan: solo persiste hoteles y evaluaciones. El objetivo es que una sola frase («quiero ir a Santa Marta, hotel frente al mar, con dos niños y un perro, 3 días y 2 noches, 2 millones») produzca un plan utilizable, con datos reales de proveedores y sin que el modelo de lenguaje invente lugares ni precios. El sistema aporta los hechos; el modelo interpreta y redacta.

El cambio es arquitectónico: se incorporan Google Places (New) y Routes como proveedores de datos, se sustituye el flujo de integración por un planificador único y se añade un entry point CLI. El concepto de «atracciones» se reemplaza por lugares cercanos al hotel.

## 2. Usuarios / actores

- **Viajero:** escribe la frase, responde las preguntas que falten y consume el plan en la terminal.
- **Sistema:** interpreta, consulta proveedores, filtra, evalúa y presenta.
- **Desarrollador/operador:** configura credenciales y límites, y valida el comportamiento con pruebas controladas.

## 3. Historias de usuario

- **H1:** Como viajero, quiero describir mi viaje en una frase para no llenar formularios.
- **H2:** Como viajero, quiero hoteles filtrados por presupuesto y por cercanía real al lugar que me interesa, para no perder tiempo mirando opciones que no me sirven.
- **H3:** Como viajero, quiero que la recomendación de hotel se base en reseñas reales, para confiar en la elección.
- **H4:** Como viajero, quiero planes y restaurantes cerca del hotel y un itinerario por días, para saber qué hacer sin investigar por mi cuenta.
- **H5:** Como viajero, quiero links de reserva y mapa, y saber si el hotel cabe en mi presupuesto, para decidir y actuar.

## 4. Requisitos funcionales (EARS)

- **RF-1:** CUANDO el viajero entrega una frase, EL SISTEMA la interpreta y produce una solicitud de viaje validada con destino, fechas, adultos, niños, mascotas, presupuesto, ancla o preferencia explícita por ninguna, minutos máximos y preferencias; SI el destino existe en varios lugares relevantes, ENTONCES pregunta cuál antes de continuar.
- **RF-2:** CUANDO la frase ha sido interpretada, SI faltan destino, fechas, adultos, presupuesto, ancla o minutos máximos, ENTONCES EL SISTEMA los solicita antes de consultar proveedores de datos (hoteles, lugares o rutas); la interpretación de la frase no cuenta como consulta de datos.
- **RF-3:** SI una fecha es pasada, la salida no es posterior a la entrada, la estancia supera 30 noches o la duración declarada contradice la fecha de salida, ENTONCES EL SISTEMA rechaza la solicitud y vuelve a preguntar; SI falta el año y la fecha ya pasó, ENTONCES usa el próximo año; las fechas se interpretan en la zona horaria del destino.
- **RF-4:** CUANDO existe un ancla, EL SISTEMA la resuelve a un lugar real; SI no la resuelve, cae fuera del destino o no corresponde al tipo pedido, ENTONCES pide reformular sin buscar hoteles; SI hay varios candidatos dentro del destino, ENTONCES usa el primero por relevancia del proveedor y lo declara en el plan.
- **RF-5:** CUANDO la solicitud está completa, EL SISTEMA busca hoteles reales para las fechas y la ocupación total indicadas, con precios en COP y link de reserva; la ocupación se consulta en una sola búsqueda, aunque el grupo exceda una habitación.
- **RF-6:** CUANDO hay hoteles y ancla resuelta, EL SISTEMA conserva los que están dentro de los minutos máximos caminando (10, 20, 30, 45 o 60) y muestra también el tiempo en auto con la advertencia de que es una estimación beta del proveedor; SI ninguno cumple, ENTONCES amplía al siguiente nivel y lo avisa; SI ya está en 60 o sigue sin cumplir, ENTONCES muestra los 3 más cercanos con su tiempo real; los hoteles sin distancia verificable se descartan.
- **RF-7:** CUANDO hay hoteles que cumplen la distancia, EL SISTEMA compara el costo total de la estancia con el presupuesto usando el total antes de impuestos informado por el proveedor o, si solo hay precio por noche, multiplicándolo por las noches, y advierte que la comparación no incluye impuestos ni tarifas; el precio mostrado es la tarifa más baja disponible y se advierte que el proveedor no declara tipo de habitación; un total igual al presupuesto cuenta como que cabe. SI ninguno cabe, ENTONCES muestra los 3 más baratos de ese mismo conjunto e indica cuánto se exceden.
- **RF-8:** CUANDO hay hoteles que cumplen distancia y presupuesto, EL SISTEMA toma hasta 5 finalistas, obtiene sus reseñas reales y entrega un top 3 con resumen, fortalezas, debilidades, al menos una cita textual cuando existan reseñas, si admite mascotas y cómo se ajusta a las preferencias declaradas; SI hay mascotas, ENTONCES prioriza los hoteles que las admiten cuando el dato existe y no penaliza cuando no existe; SI un finalista no tiene reseñas, ENTONCES lo evalúa con los datos disponibles y lo marca como no verificado.
- **RF-9:** CUANDO se elige el hotel recomendado, EL SISTEMA busca restaurantes y planes a máximo 20 minutos caminando; SI hay menos de 5 lugares o menos de 2 restaurantes, ENTONCES amplía a 30 minutos y lo avisa; SI aun así no hay lugares, ENTONCES entrega el plan sin itinerario y lo advierte.
- **RF-10:** CUANDO existen lugares reales alrededor del hotel, EL SISTEMA arma un itinerario por días con bloques de mañana, tarde y noche, reduciendo bloques en los días de llegada y salida; usa solo lugares de la lista consultada, respeta el horario cuando está disponible y, si no lo está, no garantiza que el lugar esté abierto; SI una referencia no corresponde a un lugar de la lista, ENTONCES la descarta y lo advierte.
- **RF-11:** CUANDO el plan está listo, EL SISTEMA presenta el top 3, el itinerario, los links de reserva y mapa, y la comparación del costo del hotel con el presupuesto en COP; SI el proveedor devuelve otra moneda, ENTONCES muestra el precio en esa moneda y advierte que no se puede comparar con el presupuesto; el plan es completo cuando incluye recomendación de hotel y comparación de presupuesto, y un plan sin itinerario se presenta como parcial con la razón.
- **RF-12:** SI un proveedor falla, ENTONCES EL SISTEMA reintenta hasta 2 veces y luego degrada informando el fallo: sin hoteles aborta con mensaje claro; sin reseñas entrega el top 3 sin evidencia; sin lugares o sin distancias entrega el plan sin itinerario o sin distancia verificada; sin evaluación del modelo ordena por calificación descendente, precio ascendente y distancia ascendente. Reutiliza respuestas vigentes y, si el proveedor falla, acepta respuestas vencidas de hasta 7 días indicando su antigüedad, salvo el contenido de Places, que no se almacena; una respuesta corrupta se trata como inexistente.

## 5. Requisitos no funcionales

- **Rendimiento:** un plan con datos frescos se entrega en menos de 60 segundos en el percentil 95, medido con caché fría, 2 adultos, 2 niños, 3 noches y red residencial.
- **Frescura:** los precios de hotel no se reutilizan más de 12 horas; las reseñas, 7 días; de lugares y ancla solo se conservan `place_id` y coordenadas hasta 30 días; de rutas, solo coordenadas hasta 30 días; el contenido de Places se consulta fresco en cada plan. Una respuesta vencida solo se usa como respaldo si el proveedor falla y tiene menos de 7 días.
- **Trazabilidad:** todo dato numérico o de ubicación proviene de un proveedor o de la caché; el modelo no crea ni altera cifras.
- **Validación:** la entrada y la salida del modelo se validan con Pydantic antes de usarse (constitución #5).
- **Errores:** todo fallo se informa; la degradación nunca oculta el error (constitución #6).
- **Aislamiento:** SerpAPI, Gemini, Places y Routes quedan encapsulados en servicios; la lógica interna no depende de sus detalles (constitución #14).
- **Modelos:** se persiste con modelos del dominio, nunca con modelos del proveedor (constitución #15).
- **Pruebas:** `unittest` con mocks de proveedores y base de datos de pruebas; cobertura mínima de servicios core y repositories (constitución #7).
- **Seguridad:** las credenciales viven solo en configuración de entorno; no se registran credenciales ni datos personales de reseñas.
- **Idioma:** interacción, errores y registros en español (constitución #8).

## 6. Casos límite

- **Entrada incompleta, ininteligible o ambigua:** destino, fechas, ancla o ciudad homónima sin resolver; se repregunta y no se consulta ningún proveedor de datos; sin terminal interactiva, termina con error.
- **Fechas y grupo límite:** fechas pasadas, salida igual o anterior a la entrada, más de 30 noches, año omitido o conflicto entre duración y salida; grupo que excede una habitación: una sola búsqueda con la ocupación total y aviso si no hay resultados.
- **Sin hoteles, sin distancia o sin presupuesto:** hotel sin distancia verificable se descarta; se amplía un nivel de minutos y luego se muestran los 3 más cercanos; si no hay hoteles, se termina con mensaje y sugerencia; un total igual al presupuesto cuenta como que cabe.
- **Hoteles incompletos o duplicados:** sin precio se excluye; sin link se advierte; sin coordenadas se descarta; el mismo hotel en varias fuentes se unifica.
- **Fallos y caché:** degradación por proveedor según RF-12; caché vencida de hasta 7 días con aviso, salvo Places; caché corrupta se ignora; el fallo de reseñas no elimina el top 3.
- **Lugares e itinerario límite:** cero lugares, lugares cerrados, sin horario, links rotos, mención de lugares lejanos o de «excursiones»: se avisa que quedan fuera de esta versión y no se gastan llamadas extra.

## 7. Fuera de alcance

- Cuentas, login, historial, perfiles y preferencias persistentes por usuario.
- Frontend web, aplicación móvil y API REST pública.
- Pagos, reservas transaccionales y disponibilidad en tiempo real.
- Vuelos, transporte y traslados.
- Precios exactos de comida, transporte o actividades; solo se usa el nivel de precio como referencia.
- Lugares que requieran transporte o día completo, y viajes multi-ciudad.

## 8. Criterios de aceptación

1. Una frase que ya contiene destino, fechas, adultos, presupuesto, ancla y minutos produce un plan con top 3, itinerario, links y comparación de presupuesto, sin preguntas adicionales.
2. Una frase incompleta dispara solo las preguntas de los datos faltantes y no consulta proveedores de datos antes de completarlas.
3. Fechas inválidas o contradictorias y presupuestos inválidos se rechazan con un mensaje claro y se vuelven a pedir.
4. Todo hotel mostrado cumple los minutos caminando elegidos, o el plan declara explícitamente que se amplió el nivel o que se muestran los 3 más cercanos.
5. Cada afirmación de la evaluación de hotel se apoya en una reseña real o se marca como «no verificado».
6. Ningún lugar del itinerario carece de correspondencia en la lista de lugares consultados.
7. Ante el fallo simulado de cada proveedor, el plan se degrada según RF-12 y nunca muestra datos inventados.
8. La suite de pruebas queda en verde, no aparecen credenciales en salida ni registros, y el rendimiento se mide en las condiciones del RNF de rendimiento.

## 9. Dudas abiertas

- **Proveedor de hoteles:** si respeta COP en todos los destinos y cómo cotiza grupos que exceden una habitación [POR VERIFICAR].
- **Persistencia en SerpApi:** los términos no autorizan explícitamente almacenar resultados; la caché propia de hoteles y reseñas queda como riesgo asumido [POR VERIFICAR].
- **Actualización de contexto:** la constitución #1, el contexto v2 y `fases/` deben actualizarse para reflejar Places, Routes y el nuevo alcance; queda a cargo del usuario.

## 10. Clarificaciones

| Hallazgo | Estado | Cómo se cerró |
|---|---|---|
| C-01, C-02 | Cerrado | Places y Routes se declaran proveedores aprobados en §1; la actualización de la constitución #1 y del ADR/fases queda avisada al usuario. |
| C-03 | Cerrado | RNF de pruebas cita la constitución #7 y el criterio 8 lo verifica. |
| C-04, C-09, C-11 | Cerrado | RF-12 y el RNF de frescura definen la reutilización; el RNF de modelos cita #15 y el de idioma cubre registros y errores. |
| C-05, C-06, C-07, C-08 | Cerrado | RF-10 habla de lugares de la lista consultada; los RNF exigen Pydantic (#5), errores explícitos (#6) y aislamiento de los cuatro proveedores (#14). |
| C-10, D-05 | Cerrado | §1 declara la sustitución de las decisiones 3, 6, 7, 8, 9 y 11 del contexto v2, mantiene la 15 y avisa de la actualización pendiente. |
| A-01, A-02, L-02 | Cerrado | RF-1 y RF-2 hacen el destino obligatorio y ordenan interpretar antes de consultar proveedores de datos. |
| A-03, E-03 | Cerrado | El ancla admite «sin preferencia»; sin ancla no se aplica filtro de distancia y se declara en el plan. |
| A-04, A-05, L-04 | Cerrado | RF-8 usa las preferencias y prioriza hoteles que admiten mascotas cuando el dato existe, sin penalizar cuando falta. |
| A-06, A-07 | Cerrado | Decisión 1: conflicto duración/salida se rechaza y se repregunta; el tope de 30 noches se mantiene. |
| A-08, A-09 | Cerrado | Decisión 2: primer resultado por relevancia del proveedor; ancla fuera del destino o de otro tipo se rechaza. |
| A-10, A-13, L-08 | Cerrado | RF-6 fija la escalera 10/20/30/45/60; RF-7 define el total y que un valor igual al presupuesto cabe. |
| A-11, L-06, L-09 | Cerrado | Los hoteles sin distancia verificable, sin precio o sin coordenadas se descartan; sin link se advierte. |
| A-12, A-14, E-04 | Cerrado | Decisión 3: cercanía primero y los 3 más baratos salen del conjunto que cumple la distancia. |
| A-15, A-16, A-17 | Cerrado | RF-8 fija 5 finalistas, exige al menos una cita y define «no verificado» como dato no disponible. |
| A-18, A-19 | Cerrado | Decisión 4: menos de 5 lugares o menos de 2 restaurantes amplía a 30 minutos; cero lugares deja el plan sin itinerario. |
| A-20, A-21, L-10 | Cerrado | RF-10 fija bloques de mañana, tarde y noche, respeta horarios cuando existen y excluye lugares cerrados. |
| A-22, E-02 | Cerrado | RF-11 define plan completo (hotel y presupuesto) y plan parcial (sin itinerario, con la razón). |
| A-23, A-25 | Cerrado | RF-12 fija el orden de respaldo y 2 reintentos antes de degradar. |
| A-24, E-01 | Cerrado | Decisión 7: caché vencida solo como respaldo, con máximo de 7 días y aviso de antigüedad. |
| A-26, A-27, T-02 | Cerrado | El RNF de trazabilidad vincula cada cifra a su origen; el de rendimiento fija condiciones medibles y el criterio 8 lo verifica. |
| A-28, A-29, L-13, L-16 | Cerrado | El presupuesto compara solo el hotel; la moneda es COP incluso fuera de Colombia y una moneda distinta se advierte. |
| A-30 | Cerrado | Decisión 6: se pregunta solo cuando hay ambigüedad real de destino. |
| E-05, E-06 | Cerrado | RF-12 cubre el fallo aislado de reseñas y el de lugares o distancias con resultados parciales explícitos. |
| E-07, E-08, E-09 | Cerrado | Caché corrupta se ignora; no se garantiza reproducibilidad entre ejecuciones; una corrección reemplaza solo el campo corregido. |
| E-10 | Cerrado | Precedencia fijada: validación, ancla, hoteles, distancia y presupuesto. |
| L-01, L-15 | Cerrado | Entrada ininteligible se repregunta; sin terminal interactiva el proceso termina con error. |
| L-03 | Cerrado | Decisión 5: una sola búsqueda con la ocupación total; si no hay resultados, se avisa y se sugiere ajustar el grupo. |
| L-05, L-07, L-11, L-12 | Cerrado | Zona horaria del destino y mínimo una noche; duplicados unificados; link se muestra tal cual; nombres se conservan y el plan va en español. |
| L-14 | Cerrado | No se garantiza reanudación tras interrupción ni exclusión mutua entre ejecuciones simultáneas. |
| T-01, T-03, T-04, T-05 | Cerrado | Los términos quedaron definidos en RF-6, RF-8, RF-9, RF-11 y RF-12; los criterios 1 a 8 son binarios y cubren credenciales, caché, reseñas y no regresión. |
| D-01 | Cerrado | Se mantiene el número 005; se avisa que los 005 a 007 planificados en el contexto v2 quedan obsoletos. |
| D-02, D-03, D-04, D-06 | Cerrado | Dependencia de la 004 corregida, supersesión de la 003 declarada y conteo de dudas alineado. |
| D-07, D-08, D-09 | Cerrado | La caché queda cubierta por RF-12; se declara que el esquema se aplica en las tres bases sin resets y que «atracciones» se reemplaza por lugares. |
| D-10, D-11 | Cerrado | Se avisa que `fases/` y las referencias obsoletas de la constitución #10 deben actualizarse junto con el contexto. |
| Investigación D1.3, D1.4 | Cerrado | Presupuesto contra el total antes de impuestos con aviso de impuestos y tarifas; tarifa más baja con aviso de tipo de habitación desconocido. |
| Investigación D2.1–D2.6 | Cerrado | Places se consulta con Enterprise + Atmosphere (horario, nivel de precio, calificación, admite perros y niños). |
| Investigación D3.1–D3.3, H2.1 | Cerrado | De lugares se guardan `place_id` y coordenadas; de rutas, solo coordenadas; el contenido de Places se consulta fresco. |
| Investigación D3.3b | Cerrado | A Gemini solo se envían nombre, tipo, coordenadas y horario del lugar. |
| Investigación D3.5 | Cerrado | El README avisa que el MVP usa Google Maps y enlaza sus términos y política de privacidad. |
| Investigación D4.2 | Cerrado | COP siempre; si el proveedor devuelve otra moneda, se muestra y se advierte que no se compara con el presupuesto. |
| Investigación D5.1–D5.3 | Cerrado | Se fija `gemini-3.8-flash` con nivel gratuito; se avisa que ese nivel puede usar las reseñas para mejorar productos. |
| Investigación H1.1 | Cerrado | Cada tiempo a pie se muestra con la advertencia de que es una estimación beta. |
| Investigación H3.1–H3.2, H4.1 | Cerrado | Caché propia de hoteles de 12 h; la fecha de reseña se muestra tal como la entrega el proveedor. |
| Investigación D3.6 | Dudas abiertas | SerpApi no documenta permiso para almacenar resultados; la caché propia queda como riesgo asumido [POR VERIFICAR]. |
| Dudas de §9 | Dudas abiertas | Cobertura de COP por destino, grupos que exceden una habitación y persistencia en SerpApi se marcan [POR VERIFICAR]. |

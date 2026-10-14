# Spec 004 — Esquema y reset de la base de datos

## Contexto y objetivo

Destino3 arranca con una base de datos real contaminada con datos de prueba provisionales que no
corresponden a la versión final de la app. Esta spec deja la BD real vacía (solo estructura) para que
lo único que entre en ella sean datos de la aplicación cuando esté funcionando, separa la demo en
`demo_db` y los tests en `destino3_test_db`, y aplica el mismo esquema a las tres bases. Además se introduce
en el esquema la restricción de unicidad del identificador de Google Places por hotel, para no heredar
duplicados cuando entre la búsqueda real.

El reset se ejecuta una única vez dentro de esta spec, sin respaldo y sin confirmación humana, por
decisión explícita y documentada del responsable del proyecto: los datos existentes son de prueba y se
descartan íntegramente (ver `docs/contexto-v2-fuentes-de-verdad.md`, decisión 14). Una vez ejecutado,
la BD real queda protegida frente a cualquier vaciado posterior.

## Bases por entorno

- **Producción:** `destino3_db` (base existente).
- **Testing:** `destino3_test_db` (base existente).
- **Demo:** `demo_db` (base prevista por esta spec, pendiente de provisionamiento en A2).

## Usuarios / actores

- **Responsable del proyecto:** decide el reset sin red de seguridad y el alcance del esquema.
- **Desarrollador / operador de la demo:** ejecuta la demo de integración en su día a día.
- **Sistema:** aplicación y esquema de la BD; persistencia futura de hoteles.
- **Ejecutor de pruebas:** verifica la guarda de entorno, el esquema y el estado de la BD real.

## Historias de usuario

- **H1:** Como responsable del proyecto, quiero vaciar por completo la BD real en una única ocasión
  para que no quede ningún dato de prueba que simule una versión final que aún no existe.
- **H2:** Como operador de la demo, quiero que la demo use APIs reales siempre contra `demo_db` para
  que sus datos queden separados tanto de los tests como de la BD real.
- **H3:** Como desarrollador, quiero que el esquema impida tener dos veces el mismo hotel por su
  identificador de Google Places desde ahora, para no heredar duplicados.
- **H4:** Como responsable del proyecto, quiero que tras el único reset de esta spec la BD real
  quede protegida y solo acumule datos de la aplicación ya funcionando, sin escrituras de tests,
  demos ni datos simulados.
- **H5:** Como ejecutor de pruebas, quiero verificar tras el reset que la BD real está vacía para
  saber que el punto de partida es el correcto.

## Requisitos funcionales (EARS)

- **RF-1:** CUANDO se ejecuta el reset —operación única de esta spec—, EL SISTEMA vacía todas las
  tablas de la BD real conservando su estructura, sin tablas excluidas; para esta única ejecución no
  requiere respaldo previo ni confirmación humana (decisión explícita del responsable). Comprobación
  manual objetiva sobre la BD real.

- **RF-2:** SI durante el reset se produce un error, ENTONCES se revierte toda la operación, se
  informa el fallo y la BD real queda exactamente como estaba antes de empezar, sin restauración
  automática ni reintentos.

- **RF-3:** DESPUÉS del reset, EL SISTEMA comprueba que la BD real no contiene ninguna fila en
  ninguna de sus tablas, sin excepciones, y da por válido el resultado solo si todo está en cero.
  Comprobación manual objetiva sobre la BD real.

- **RF-4:** CUANDO se aplica el esquema nuevo, EL SISTEMA garantiza que el identificador de Google
  Places de un hotel no pueda registrarse dos veces; hasta la entrega de la spec 005 el identificador
  es opcional, de modo que varios hoteles pueden carecer de él sin invalidarse entre sí.

- **RF-5:** EL SISTEMA aplica el esquema nuevo a la BD real (`destino3_db`), `demo_db` y `destino3_test_db`. En la BD real,
  el vaciado y la aplicación del esquema nuevo se ejecutan en una sola transacción: si cualquier
  paso falla, la BD real queda como estaba antes de empezar. En `demo_db` y `destino3_test_db`, la aplicación
  del esquema no elimina ni modifica los datos existentes.

- **RF-6:** CUANDO se inicia la demo con un entorno configurado distinto de `demo`, EL SISTEMA
  termina la ejecución con un error claro y no realiza ninguna operación.

- **RF-7:** EL SISTEMA ejecuta la demo siempre contra `demo_db`, usa APIs reales, conserva allí sus
  resultados y no ofrece reset ni borrado; nunca escribe en `destino3_test_db` ni en la BD real (`destino3_db`); la BD real
  solo recibe datos de la aplicación.

- **RF-8:** CUANDO se ejecutan tests, EL SISTEMA los ejecuta únicamente contra `destino3_test_db` con
  respuestas grabadas y reversión por prueba: cada prueba revierte sus cambios al terminar sin afectar el código de
  producción. Quedan prohibidos el reset del esquema, el borrado de `destino3_test_db` y el vaciado de sus
  tablas dentro de los tests.

- **RF-9:** EL SISTEMA no deberá ofrecer ninguna operación de reset repetible sobre la BD real;
  cualquier vaciado posterior queda fuera de esta spec y exige una decisión nueva con confirmación
  humana. Comprobación manual objetiva: la interfaz pública del sistema no expone ninguna operación
  de vaciado de la BD real.

## Requisitos no funcionales

- **Simplicidad:** el reset no implementa respaldos, reintentos ni restauración; comprobación
  manual objetiva por inspección de que ninguna de esas tres capacidades está presente.

- **Aislamiento:** ninguna operación de test o demo puede escribir en la BD real; tras el único
  reset de esta spec, la BD real queda protegida y no se le ofrece ninguna operación de reset.

- **Integridad entre entornos:** el esquema de `destino3_db`, `demo_db` y `destino3_test_db` debe ser equivalente.

- **Separación de accesos:** `production`, `demo` y `testing` usan roles de acceso independientes;
  cada ejecución solo puede conectarse a la base que le corresponde.

- **Observabilidad:** el resultado del reset, de la verificación posterior y de la guarda de entorno
  queda visible en la salida de ejecución (consola o logs).

## Casos límite

- **Error durante el reset:** cualquier fallo revierte toda la operación y la BD real queda intacta,
  como antes de empezar; no hay reintentos ni restauración.

- **Hoteles existentes sin identificador:** aplica a `demo_db` y `destino3_test_db`, donde se conservan al
  aplicar el esquema; en la BD real no hay filas porque el esquema se aplica después del vaciado. La
  unicidad solo afecta a los hoteles que sí tengan identificador.

- **Identificador duplicado ya presente:** aplica a `demo_db` y `destino3_test_db` (en la real no hay filas
  al aplicar el esquema): si existieran filas con el mismo identificador, la aplicación del esquema
  falla, se informa y no se deja la base a medias.

- **Demo con entorno incorrecto:** la demo termina con un error claro y no realiza ninguna operación;
  no usa `destino3_test_db` ni la BD real (`destino3_db`) como alternativa.

- **Intento de repetir el reset:** no está soportado; cualquier vaciado posterior de la BD real queda
  fuera de esta spec y exigiría una decisión nueva con confirmación humana.

- **Datos previos en `demo_db` y `destino3_test_db`:** `demo_db` conserva los resultados de la demo y `destino3_test_db`
  parte de datos semilla controlados; los tests no borran ninguna de las dos bases.

## Fuera de alcance

- Respaldo, verificación de respaldos y restauración: eliminados del alcance por decisión del
  responsable del proyecto (datos de prueba prescindibles).
- Obligatoriedad del identificador de Google Places y omisión de hoteles sin identificador: spec 005
  (ubicacion-places), cuando exista la fuente que lo resuelve.
- Persistencia con actualización en conflicto (upsert) sobre el identificador: spec 005.
- Precios y reserva: spec 006; evaluación enriquecida: spec 007.
- Modificaciones de la spec 003, ya entregada.
- Creación física de bases, credenciales y definición concreta de tablas, columnas y sentencias:
  corresponde a la infraestructura y al plan de implementación, no a la aplicación.

## Criterios de finalización

- La BD real se vació por completo (cero filas en todas sus tablas, sin excepciones) y se le aplicó
  el esquema nuevo en una sola transacción; si algo falló, quedó como estaba antes; esa fue su única
  ejecución de reset y queda protegida frente a vaciados posteriores.
- La BD real (`destino3_db`), `demo_db` y `destino3_test_db` tienen el mismo esquema; `demo_db` conserva los resultados de la
  demo y `destino3_test_db` conserva sus datos semilla sin pérdida.
- La demo termina con error claro fuera del entorno `demo`, solo escribe en `demo_db` y nunca usa
  otra base como alternativa (verificado con prueba automatizada).
- Los tests solo usan `destino3_test_db`, revierten sus cambios y no ejecutan resets ni vaciados.
- Existen pruebas automatizadas de la guarda de entorno y de la restricción de unicidad del
  identificador de Google Places.
- La suite completa de tests queda en verde.

## Dudas abiertas

- El paso de «identificador único pero no obligatorio» a «identificador obligatorio y hoteles sin él
  no persistidos» debe ocurrir al entregar la spec 005; si 005 se retrasa, la unicidad sigue activa
  pero parcial.
- El reset sin respaldo es irreversible: si apareciera algún dato real que lamentar, no hay
  recuperación posible (aceptado explícitamente por el responsable del proyecto).

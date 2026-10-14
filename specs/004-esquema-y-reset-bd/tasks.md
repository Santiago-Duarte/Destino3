# Tareas - Spec 004: Esquema y reset de la base de datos

**Reglas de ejecucion:** cada tarea dura como maximo 30 minutos, se ejecuta en el orden indicado y no se inicia una
tarea si su dependencia no esta marcada como hecha. Al terminar cada tarea se ejecuta `python3 -m pytest test/ -q`.
Los skips solo son aceptables si `-rs` confirma que proceden de una BD de testing no disponible. Ninguna tarea de tests
puede apuntar a la BD real.

**Seguridad operacional:** las tareas H4 y H5 actuan sobre la BD real. H4 es la unica ejecucion destructiva autorizada
por esta spec; no requiere confirmacion humana por la decision documentada de spec 004, no crea respaldo y no se repite.

## Bloque A - Contrato de entornos y provisionamiento

- [x] **A1. Documentar las variables separadas por entorno** (~15 min)
  - **RF:** RF-5, RF-6, RF-7, RF-8
  - **Depende de:** —
  - **Hecho cuando:** `.env.example` contiene `DB_TEST_NAME`, `DB_TEST_USER`, `DB_TEST_PASSWORD`, `DB_DEMO_NAME`, `DB_DEMO_USER`, `DB_DEMO_PASSWORD`, `DB_PRODUCTION_NAME`, `DB_PRODUCTION_USER` y `DB_PRODUCTION_PASSWORD`, sin eliminar `DB_HOST` ni `DB_PORT`.

- [x] **A2. Provisionar las tres bases y los cuatro roles** (~30 min)
  - **RF:** RF-5, RF-6, RF-7, RF-8
  - **Depende de:** A1
  - **Hecho cuando:** consultas administrativas muestran `destino3_db`, `demo_db` y `destino3_test_db`, junto con roles de `production`, `demo`, `testing` y esquema, todos creados en la misma instancia.

- [x] **A3. Configurar permisos de aislamiento entre bases** (~25 min)
  - **RF:** RF-5, RF-6, RF-7, RF-8
  - **Depende de:** A2
  - **Hecho cuando:** `has_database_privilege` devuelve acceso permitido solo para el rol de cada base y denegado para las otras dos, mientras el rol de esquema conserva acceso administrativo a las tres.

- [x] **A4. Verificar el acceso operacional con la matriz de entornos** (~20 min)
  - **RF:** RF-5, RF-6, RF-7, RF-8
  - **Depende de:** A3
  - **Hecho cuando:** las tres conexiones de verificación abren exclusivamente `destino3_db`, `demo_db` y `destino3_test_db` según su rol y la prueba de cada cruce falla con error de permisos.

## Bloque B - Esquema canonico y migracion

- [ ] **B1. Añadir `google_place_id` al esquema canonico** (~25 min)
  - **RF:** RF-4, RF-5
  - **Depende de:** A4
  - **Hecho cuando:** `sql/schema.sql` define `hospedajes.google_place_id` como columna nullable y una restriccion o indice unico con nombre estable, sin `NOT NULL` ni `ON CONFLICT`.

- [ ] **B2. Crear la migracion aditiva para bases existentes** (~25 min)
  - **RF:** RF-4, RF-5
  - **Depende de:** B1
  - **Hecho cuando:** existe `sql/migrations/002_google_place_id.sql`, contiene solo la adicion de la columna y la unicidad, y no contiene `TRUNCATE`, `DELETE`, `DROP DATABASE` ni cambios de datos.

- [ ] **B3. Verificar la idempotencia de la migracion** (~20 min)
  - **RF:** RF-4, RF-5
  - **Depende de:** B2
  - **Hecho cuando:** la migracion aplicada dos veces a una base no productiva termina sin error en la segunda ejecucion y la segunda ejecucion no cambia las columnas ni los indices observados.

- [ ] **B4. Verificar rollback ante identificadores duplicados durante la migracion** (~25 min)
  - **RF:** RF-2, RF-4, RF-5
  - **Depende de:** B3
  - **Hecho cuando:** una base no productiva con el esquema anterior y dos filas con el mismo identificador rechaza la migracion y conserva sin cambios sus filas y su esquema previo.

## Bloque C - Modelo y persistencia del identificador

- [ ] **C1. Extender el modelo de dominio `Hospedaje`** (~15 min)
  - **RF:** RF-4
  - **Depende de:** B4
  - **Hecho cuando:** `Hospedaje` acepta `google_place_id` opcional, conserva `None` y conserva un texto no nulo en una instancia sin introducir un `id_temporal` persistente.

- [ ] **C2. Persistir y recuperar `google_place_id` en el repository** (~25 min)
  - **RF:** RF-4, RF-7
  - **Depende de:** C1
  - **Hecho cuando:** `HospedajeRepository` inserta y selecciona `google_place_id`, no ejecuta un pre-chequeo de unicidad ni un upsert, y todos los errores SQL se propagan.

## Bloque D - Conexion estricta y guarda de la demo

- [ ] **D1. Implementar el mapa estricto de conexiones por entorno** (~30 min)
  - **RF:** RF-6, RF-7, RF-8
  - **Depende de:** C2
  - **Hecho cuando:** `src/config/database.py` selecciona exactamente `testing -> destino3_test_db`, `demo -> demo_db` y `production -> destino3_db`, y un entorno distinto lanza un error antes de llamar a `psycopg2.connect`.

- [ ] **D2. Probar el selector de entorno y la ausencia de fallback** (~25 min)
  - **RF:** RF-6, RF-7, RF-8
  - **Depende de:** D1
  - **Hecho cuando:** existen pruebas que verifican los tres tripletes de base/usuario/password, un entorno desconocido y una variable obligatoria ausente, y ninguna de las dos ultimas intenta otra base.

- [ ] **D3. Añadir la guarda `ENVIRONMENT=demo` al entry point de demo** (~25 min)
  - **RF:** RF-6, RF-7
  - **Depende de:** D2
  - **Hecho cuando:** `src/demo_integracion.py` rechaza cualquier entorno distinto de `demo` antes de leer claves, construir el orquestador, abrir conexion o llamar a un proveedor, y retorna codigo distinto de cero.

- [ ] **D4. Probar la guarda de la demo con proveedores y conexion simulados** (~20 min)
  - **RF:** RF-6, RF-7
  - **Depende de:** D3
  - **Hecho cuando:** la prueba del entorno invalido verifica cero llamadas a conexion, SerpAPI, Gemini y orquestador, y la prueba de `demo` verifica el nombre `demo_db` en los parametros de conexion.

## Bloque E - Harness transaccional de tests

- [ ] **E1. Crear el adaptador de conexion externa con savepoints** (~30 min)
  - **RF:** RF-8
  - **Depende de:** D4
  - **Hecho cuando:** el adaptador expone `commit()`, `rollback()` y `close()` compatibles con psycopg2, pero `commit()` solo recrea el savepoint, `rollback()` vuelve al savepoint y `close()` no cierra la conexion externa.

- [ ] **E2. Integrar una transaccion externa por prueba en `BaseDBTestCase`** (~30 min)
  - **RF:** RF-8
  - **Depende de:** E1
  - **Hecho cuando:** `setUp` abre una conexion exclusiva a `destino3_test_db`, `tearDown` revierte y cierra esa conexion, y el harness no ejecuta ningun `TRUNCATE`, `DELETE` masivo, `DROP` ni reinicio de secuencias.

- [ ] **E3. Probar el adaptador con commits, rollbacks y cierres de repositories** (~25 min)
  - **RF:** RF-8
  - **Depende de:** E2
  - **Hecho cuando:** una prueba confirma que una escritura posterior a un `commit()` del repository se revierte al finalizar el test y que un `close()` del repository no impide el rollback externo.

- [ ] **E4. Eliminar la semilla destructiva del harness existente** (~25 min)
  - **RF:** RF-8
  - **Depende de:** E3
  - **Hecho cuando:** `test/db_test_case.py` no contiene `TRUNCATE`, `DELETE`, `DROP`, `RESTART IDENTITY` ni limpieza masiva, y los datos semilla necesarios se crean dentro de la transaccion de cada prueba.

- [ ] **E5. Adaptar las pruebas de destinos y hospedajes al rollback** (~30 min)
  - **RF:** RF-4, RF-8
  - **Depende de:** E4
  - **Hecho cuando:** `test/test_destino_repository.py` y `test/test_hospedaje_repository.py` pasan sin limpiar tablas y cada prueba valida solo las filas que crea dentro de su transaccion.

- [ ] **E6. Adaptar las pruebas de busquedas y recomendaciones al rollback** (~30 min)
  - **RF:** RF-8
  - **Depende de:** E5
  - **Hecho cuando:** `test/test_recomendacion_repository.py` y las pruebas de busqueda relacionadas pasan sin depender de secuencias reiniciadas ni de una BD globalmente vacia.

- [ ] **E7. Adaptar las pruebas de orquestacion e integracion al rollback** (~30 min)
  - **RF:** RF-7, RF-8
  - **Depende de:** E6
  - **Hecho cuando:** `test/test_orquestador_evaluacion.py`, `test/test_orquestador_integracion.py` y `test/test_integracion_flujo_completo.py` pasan con respuestas grabadas y sin escribir fuera de `destino3_test_db`.

- [ ] **E8. Auditar que ningun test conserva una operacion destructiva** (~20 min)
  - **RF:** RF-8, RF-9
  - **Depende de:** E7
  - **Hecho cuando:** una busqueda de `TRUNCATE|DELETE|DROP|RESTART IDENTITY` en `test/` no encuentra instrucciones SQL destructivas fuera de la documentacion de la tarea.

## Bloque F - Aplicacion no destructiva a demo y testing

- [ ] **F1. Aplicar el esquema canonico o migracion a `demo_db`** (~20 min)
  - **RF:** RF-5, RF-7
  - **Depende de:** B4, D1
  - **Hecho cuando:** la aplicacion termina con commit en `demo_db`, existe `google_place_id` con unicidad y ninguna tabla ni fila previa de demo ha sido eliminada o modificada.

- [ ] **F2. Verificar la conservacion de datos de `demo_db`** (~20 min)
  - **RF:** RF-5, RF-7
  - **Depende de:** F1
  - **Hecho cuando:** los conteos y registros testigo capturados antes de F1 coinciden despues de F1 y una insercion duplicada no nula es rechazada por PostgreSQL.

- [ ] **F3. Aplicar el esquema canonico o migracion a `destino3_test_db`** (~20 min)
  - **RF:** RF-5, RF-8
  - **Depende de:** F2
  - **Hecho cuando:** la aplicacion termina con commit en `destino3_test_db`, existe `google_place_id` con unicidad y no ejecuta reset, borrado masivo ni reinicio de secuencias.

- [ ] **F4. Verificar la conservacion de datos semilla de `destino3_test_db`** (~20 min)
  - **RF:** RF-5, RF-8
  - **Depende de:** F3
  - **Hecho cuando:** los conteos y registros semilla capturados antes de F3 coinciden despues de F3 y varias filas con `google_place_id IS NULL` son validas.

## Bloque G - Pruebas de esquema, unicidad y aislamiento

- [ ] **G1. Añadir pruebas de contrato del esquema en `destino3_test_db`** (~25 min)
  - **RF:** RF-4, RF-5
  - **Depende de:** F4
  - **Hecho cuando:** las pruebas consultan `information_schema` y los catálogos de PostgreSQL y verifican columna nullable, unicidad, FKs y checks esperados sin modificar el esquema.

- [ ] **G2. Añadir pruebas de persistencia y conflicto de `google_place_id`** (~25 min)
  - **RF:** RF-4
  - **Depende de:** G1, C2
  - **Hecho cuando:** una prueba persiste dos hospedajes sin identificador, otra persiste un identificador no nulo y otra confirma `IntegrityError` al repetirlo, sin filas parciales despues del rollback.

- [ ] **G3. Añadir prueba de rollback de una operacion SQL fallida** (~25 min)
  - **RF:** RF-2, RF-5, RF-8
  - **Depende de:** G2
  - **Hecho cuando:** una operacion de esquema simulada que falla dentro de una transaccion controlada deja sin cambios el estado observado antes de la operacion y la excepcion llega a la capa de prueba.

- [ ] **G4. Añadir prueba de aislamiento de conexion del harness** (~20 min)
  - **RF:** RF-6, RF-8
  - **Depende de:** G3
  - **Hecho cuando:** el test verifica que `ENVIRONMENT=testing` usa `DB_TEST_NAME` y `DB_TEST_USER`, y que una configuracion `demo` o `production` no puede ser seleccionada por el harness.

- [ ] **G5. Ejecutar las pruebas focalizadas de schema, repositorios y entorno** (~15 min)
  - **RF:** RF-4, RF-5, RF-6, RF-8
  - **Depende de:** G4
  - **Hecho cuando:** `python3 -m pytest test/test_config_settings.py test/test_hospedaje_repository.py test/test_destino_repository.py -q` termina sin fallos y los skips, si existen, corresponden solo a infraestructura de testing.

## Bloque H - Preparacion y ejecucion del reset unico

- [ ] **H1. Definir el inventario y preflight del procedimiento unico** (~25 min)
  - **RF:** RF-1, RF-2, RF-5, RF-9
  - **Depende de:** G5
  - **Hecho cuando:** el procedimiento documenta las siete tablas de dominio, valida base/rol de production antes de `BEGIN` y aborta si detecta una tabla publica inesperada o una conexion distinta.

- [ ] **H2. Preparar el procedimiento transaccional sin interfaz publica** (~30 min)
  - **RF:** RF-1, RF-2, RF-3, RF-9
  - **Depende de:** H1
  - **Hecho cuando:** el artefacto operacional ejecuta vaciado, esquema y commit en una unica transaccion, propaga errores con rollback y no contiene backup, retry, restauracion, endpoint ni metodo de repository.

- [ ] **H3. Verificar el camino de error del reset sin usar la BD real** (~25 min)
  - **RF:** RF-2, RF-9
  - **Depende de:** H2
  - **Hecho cuando:** una prueba controlada provoca un error despues del vaciado simulado y verifica llamadas a rollback, propagacion del error, cero reintentos y cero restauraciones.

- [ ] **H4. Ejecutar el reset unico autorizado sobre la BD real** (~30 min)
  - **RF:** RF-1, RF-2, RF-5, RF-9
  - **Depende de:** H3, F4
  - **Hecho cuando:** el procedimiento termina con resultado exitoso, registra una unica transaccion, aplica el esquema nuevo y no realiza backup, retry, restauracion ni una segunda ejecucion.

- [ ] **H5. Comprobar manualmente que la BD real quedo vacia** (~20 min)
  - **RF:** RF-3
  - **Depende de:** H4
  - **Hecho cuando:** una consulta individual devuelve `0` filas para `busquedas`, `recomendaciones`, `evaluaciones_ia`, `atracciones`, `hospedajes`, `destinos` y `usuarios`, sin excepciones.

## Bloque I - Verificacion final y cierre

- [ ] **I1. Comparar el esquema de las tres bases** (~30 min)
  - **RF:** RF-5
  - **Depende de:** H5
  - **Hecho cuando:** la comparacion de metadatos confirma igualdad de tablas, columnas, tipos, nulabilidad, FKs, checks e indices entre `destino3_db`, `demo_db` y `destino3_test_db`.

- [ ] **I2. Verificar nuevamente el aislamiento de roles tras el reset** (~25 min)
  - **RF:** RF-6, RF-7, RF-8
  - **Depende de:** I1
  - **Hecho cuando:** cada rol conecta a su propia base, los tres cruces de acceso son rechazados y ningun rol de demo/testing puede ejecutar escritura en `destino3_db`.

- [ ] **I3. Ejecutar el smoke test real de la demo** (~30 min)
  - **RF:** RF-6, RF-7
  - **Depende de:** I2
  - **Hecho cuando:** `ENVIRONMENT=demo` ejecuta la demo con APIs reales, la salida confirma persistencia en `demo_db` y una consulta a `destino3_db` no muestra esos resultados.

- [ ] **I4. Verificar que no existe reset publico ni borrado en demo** (~15 min)
  - **RF:** RF-7, RF-9
  - **Depende de:** I3
  - **Hecho cuando:** la inspeccion de `src/`, entry points y repositories no encuentra endpoint, comando, metodo o import que exponga reset o borrado de la BD real o `demo_db`.

- [ ] **I5. Ejecutar la suite completa y revisar skips** (~15 min)
  - **RF:** RF-4, RF-6, RF-7, RF-8
  - **Depende de:** I4
  - **Hecho cuando:** `python3 -m pytest test/ -q` termina sin fallos y `python3 -m pytest test/ -q -rs` muestra solo skips justificados por disponibilidad de la BD de testing.

- [ ] **I6. Cerrar la documentacion viva de la spec** (~20 min)
  - **RF:** RF-1 a RF-9
  - **Depende de:** I5
  - **Hecho cuando:** `plan.md`, `tasks.md` y la evidencia operacional reflejan el estado final, no se modifican requisitos de `spec.md` y el checklist de criterios de finalizacion queda trazable.

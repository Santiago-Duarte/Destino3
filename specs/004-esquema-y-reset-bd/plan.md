# Plan de Implementacion - Spec 004: Esquema y reset de la base de datos

## 1. Alcance y restricciones

Este plan traduce `spec.md` y `clarificaciones.md` a una estrategia de implementacion. No crea una nueva capacidad
de reset reutilizable ni modifica los requisitos de la spec 003. El reset de la BD real es una operacion operacional
unica, fuera de la interfaz publica de la aplicacion.

Las decisiones se apoyan en:

- `docs/constitucion.md`, especialmente constitucion #2, #3, #6, #7, #11, #12, #14 y #15.
- `docs/contexto-v2-fuentes-de-verdad.md`, decisiones 1, 2, 5, 6 y 14-15.
- `specs/004-esquema-y-reset-bd/spec.md` y sus clarificaciones cerradas.

Invariantes que deben mantenerse durante toda la entrega:

1. `production` solo puede conectarse a `destino3_db`, `demo` solo a `demo_db` y `testing` solo a `destino3_test_db`.
2. Ningun servicio ejecuta SQL; el SQL de aplicacion permanece en `sql/` y en repositories (constitucion #3).
3. La columna `google_place_id` es opcional en esta spec, pero sus valores no nulos son unicos.
4. El reset real no pertenece a `src/`, no tiene endpoint, no tiene comando de la demo y no se reintenta automaticamente.
5. Los tests no ejecutan `TRUNCATE`, `DELETE` masivo, reset de esquema ni reinicio de secuencias.
6. El codigo de produccion no conoce el adaptador transaccional exclusivo del harness de tests.

## 2. Arquitectura de modulos

### 2.1 Fronteras

```text
configuracion de entorno
        |
        v
conexion PostgreSQL ---> repositories ---> modelos de dominio
        ^                    ^
        |                    |
  demo_integracion      servicios existentes

sql/schema.sql + migracion 002 ---> aplicacion operacional por entorno
                                     (fuera de la interfaz publica)
```

La aplicacion conserva las capas existentes:

```text
modelos -> repositories -> services -> orchestration -> config -> entry point
```

La provision de bases, roles, migraciones y el reset puntual no es una capa de negocio. Es una operacion de
infraestructura que usa el mismo PostgreSQL y el mismo SQL canonico, pero no es invocable por los servicios ni por la
demo.

### 2.2 Componentes y responsabilidades

| Componente | Ruta propuesta | Responsabilidad | RF cubiertos |
|---|---|---|---|
| Esquema canonico | `sql/schema.sql` | Definir el esquema completo para una base nueva, incluida la columna nullable `hospedajes.google_place_id` y su unicidad | RF-4, RF-5 |
| Migracion aditiva | `sql/migrations/002_google_place_id.sql` | Aplicar a bases existentes la columna e indice unico sin borrar filas; una colision no nula aborta la transaccion | RF-4, RF-5 |
| Selector de entorno | `src/config/database.py` y configuracion asociada | Resolver exclusivamente `testing -> destino3_test_db`, `demo -> demo_db`, `production -> destino3_db`; rechazar cualquier otro entorno antes de conectar | RF-6, RF-7, RF-8 |
| Configuracion de credenciales | `.env.example` y `src/config/settings.py` | Documentar nombres separados para base, usuario y password por entorno; nunca registrar valores | RF-6, RF-7, RF-8 |
| Repositorios existentes | `src/repositories/` | Seguir usando la conexion ya seleccionada; persistir `google_place_id` cuando el modelo lo reciba, sin pre-chequeos de unicidad en Python | RF-4, RF-7 |
| Modelo de hospedaje | `src/models/hospedaje.py` | Representar `google_place_id: str | None` como dato de dominio opcional durante esta spec | RF-4 |
| Guarda de la demo | `src/demo_integracion.py` | Verificar `ENVIRONMENT=demo` antes de credenciales, conexion, servicios o persistencia; terminar con error claro fuera de demo | RF-6, RF-7 |
| Harness transaccional | `test/db_test_case.py` y utilidades solo de `test/` | Abrir una transaccion externa por test, absorber `commit()`/`close()` de repositories y revertir al finalizar | RF-8 |
| Verificador de entornos | Runbook o utilidad operacional no importada por `src/` | Comparar tablas, columnas, restricciones/indices y tipos entre las tres bases mediante conexiones separadas | RF-3, RF-5 |
| Aplicacion unica del reset | Procedimiento operacional de `spec 004`, no modulo publico | En una transaccion de la BD real: vaciar tablas, aplicar el esquema y hacer commit solo si todo termina correctamente | RF-1, RF-2, RF-3, RF-9 |

La aplicacion de esquema y el reset se ejecutan con un rol de administracion de esquema separado de los tres roles de
la aplicacion. Los roles de produccion, demo y testing no reciben permisos para crear bases, cambiar roles ni vaciar
tablas.

### 2.3 Cambios acotados en la aplicacion

1. La resolucion de conexiones deja de tratar cualquier valor distinto de `testing` como produccion. Un valor
   desconocido genera una excepcion de configuracion y no llama a `psycopg2.connect`.
2. La demo valida el entorno antes de comprobar las claves API. Un entorno invalido no puede tener como efecto ni una
   llamada externa ni una conexion a cualquier base.
3. Los repositories incorporan el nuevo atributo del modelo solo como dato persistible. La decision de unicidad es del
   esquema PostgreSQL, no de una consulta previa susceptible a carreras.
4. El arnes actual que limpia con `TRUNCATE ... RESTART IDENTITY CASCADE` se sustituye por rollback de la transaccion
   de cada prueba. No se cambia el comportamiento transaccional de los repositories de produccion.

## 3. Modelo de datos

### 3.1 Esquema logico comun

Las tres bases deben tener la misma estructura publica. La siguiente es la forma canonica que debe reflejar
`sql/schema.sql` y que la migracion debe dejar en bases ya existentes:

| Tabla | Columnas relevantes | Relaciones y restricciones |
|---|---|---|
| `destinos` | `id`, `ciudad`, `pais`, `creado_en` | PK; indice unico por `LOWER(TRIM(ciudad))` y `LOWER(TRIM(pais))` |
| `hospedajes` | `id`, `nombre`, `tipo`, `precio_noche`, `calificacion`, `direccion`, `url_reserva`, `destino_id`, `google_place_id` | PK; FK a `destinos`; `destino_id NOT NULL`; `google_place_id` nullable; unicidad sobre valores no nulos |
| `evaluaciones_ia` | `id`, `puntos_fuertes`, `puntos_debiles`, `score_calidad_precio`, `resumen_ejecutivo`, `hospedaje_id` | PK; FK a `hospedajes`; una evaluacion por hospedaje segun la restriccion vigente |
| `atracciones` | `id`, `nombre`, `categoria`, `distancia_km`, `precio_estimado`, `hospedaje_id` | PK; FK a `hospedajes` |
| `usuarios` | `id`, `nombre`, `apellido`, `correo`, `password_hash` | PK; `correo UNIQUE NOT NULL` |
| `busquedas` | `id`, `usuario_id`, `destino_id`, `zona`, `presupuesto`, `fecha_inicio`, `fecha_fin` | PK; FKs a `usuarios` y `destinos`; presupuesto positivo; fechas validas |
| `recomendaciones` | `id`, `busqueda_id`, `hospedaje_id`, `posicion` | PK; FKs a `busquedas` y `hospedajes`; posicion 1-3; unicidad por busqueda/posicion y busqueda/hospedaje |

La adicion de esta spec es:

- `hospedajes.google_place_id`: texto, nullable hasta la spec 005.
- Restriccion o indice unico nombrado y estable para `google_place_id`.
- Varias filas con `google_place_id IS NULL` siguen siendo validas por la semantica de unicidad de PostgreSQL.
- Dos filas con el mismo valor no nulo fallan en PostgreSQL. No se implementa `upsert`; pertenece a la spec 005.

Los identificadores de PostgreSQL siguen siendo los unicos IDs persistentes. No se agrega ningun `id_temporal` al
esquema (constitucion #4), y las credenciales/roles no son tablas de dominio.

### 3.2 Estrategia de schema y migracion

`sql/schema.sql` es la fuente para instalaciones nuevas. Para bases ya creadas, la migracion 002 se ejecuta dentro de
una transaccion y realiza solo cambios aditivos. Antes de crear la unicidad se comprueba que no haya identificadores
duplicados no nulos; si los hay, la sentencia falla y la transaccion se revierte sin borrar datos.

La aplicacion no crea fisicamente bases ni roles. La infraestructura los provisiona en una misma instancia PostgreSQL:

```text
destino3_db  <- rol de aplicacion production
demo_db   <- rol de aplicacion demo
destino3_test_db   <- rol de aplicacion testing
```

El rol administrador de esquema es el unico que ejecuta `schema.sql` o la migracion. En cada base se revoca el acceso
de conexion a roles generales y se concede conexion solo al rol correspondiente, ademas de los permisos de datos que
requiera cada entorno.

## 4. Estrategia de integracion por entorno

### 4.1 Seleccion de conexion

La configuracion debe usar un mapa explicito, sin fallback:

| `ENVIRONMENT` | Base | Rol |
|---|---|---|
| `testing` | `DB_TEST_NAME` | `DB_TEST_USER` |
| `demo` | `DB_DEMO_NAME` | `DB_DEMO_USER` |
| `production` | `DB_PRODUCTION_NAME` | `DB_PRODUCTION_USER` |

`DB_HOST` y `DB_PORT` pueden ser comunes porque las tres bases viven en la misma instancia; los nombres, usuarios y
passwords deben permanecer separados. Si se conserva `DB_NAME` por compatibilidad operativa, solo puede ser el valor de
`DB_PRODUCTION_NAME` documentado explicitamente, nunca un fallback silencioso para demo o testing.

La funcion de conexion debe:

1. Leer y validar el entorno antes de construir los parametros de `psycopg2.connect`.
2. Seleccionar exactamente el triplete de base, usuario y password del mapa.
3. Rechazar valores ausentes o desconocidos con un error explicito.
4. No intentar otra base si la conexion seleccionada falla.
5. No incluir password, DSN completo ni claves API en logs (constitucion #6 y NFR de seguridad).

### 4.2 Provisionamiento y aplicacion del esquema

El orden operacional propuesto es:

1. Provisionar `destino3_db`, `demo_db` y `destino3_test_db` en la misma instancia con roles independientes.
2. Verificar que cada rol puede conectarse solo a su base y que el rol de esquema puede administrar las tres.
3. Aplicar el esquema canonico o la migracion aditiva a `demo_db` dentro de una transaccion, sin operaciones
   destructivas.
4. Aplicar el mismo esquema a `destino3_test_db` dentro de una transaccion, sin operaciones destructivas.
5. Ejecutar el reset unico de la BD real junto con el esquema nuevo en una sola transaccion.
6. Comparar la estructura resultante de las tres bases y registrar la evidencia operacional.

En `demo_db` y `destino3_test_db`, un fallo al crear la columna o la unicidad revierte unicamente la aplicacion de esquema de esa
base y conserva sus filas. Un duplicado previo de `google_place_id` hace fallar la aplicacion, se informa y requiere
resolucion operacional antes de reintentar la migracion; no se resuelve borrando datos desde la aplicacion.

### 4.3 Reset unico de la BD real

El reset se ejecuta como procedimiento fuera de `src/` y fuera de la interfaz publica. No se implementa como endpoint,
funcion de repository, comando de demo ni operacion disponible a la aplicacion.

La transaccion operacional tiene estas fases:

1. Preflight: comprobar que la conexion usa el rol y la base de produccion, que el inventario de tablas es el esperado
   y que la operacion esta siendo ejecutada sobre la BD real.
2. Iniciar una unica transaccion.
3. Vaciar todas las tablas de dominio del esquema, sin excluir ninguna, conservando tablas, restricciones e indices.
   El inventario explicito debe incluir `busquedas`, `recomendaciones`, `evaluaciones_ia`, `atracciones`, `hospedajes`,
   `destinos` y `usuarios`; `CASCADE` solo resuelve el orden de dependencias y no agrega una segunda operacion de
   borrado.
4. Aplicar el esquema nuevo y la restriccion de `google_place_id` dentro de esa misma transaccion.
5. Si todo termina correctamente, hacer commit y emitir un resultado visible.
6. Si cualquier paso falla, hacer rollback, propagar el error y emitir un resultado de fallo. No hay retry, backup ni
   restauracion automatica.
7. Tras el commit, verificar manualmente que cada tabla de la BD real tiene cero filas y que el esquema es el esperado.

El procedimiento se retira o se marca como ejecutado al terminar. La ausencia de una operacion de reset en la API
publica se verifica por inspeccion de `src/` y del entry point; una ejecucion posterior queda fuera de esta spec y
requiere una decision nueva con confirmacion humana.

Operatoria implementada (H4, con `operacion/reset/`): el preflight corre sobre una conexion del rol de
production (valida base, rol e inventario, sin escrituras) y la transaccion unica corre sobre una conexion
separada del rol dueño de las tablas (`postgres`), unico con privilegios de `TRUNCATE` y `ALTER TABLE` sobre las
tablas existentes de `destino3_db`. La transaccion es la implicita de psycopg2 (sin `autocommit`): el vaciado con
`TRUNCATE ... CASCADE` del inventario y las sentencias de `sql/migrations/002_google_place_id.sql` se confirman
con un unico `commit()`, y cualquier fallo revierte y propaga. El exito escribe
`operacion/reset/evidencia_reset.json`, cuya existencia bloquea toda ejecucion posterior (RF-9).

### 4.4 Demo

`src/demo_integracion.py` conserva el flujo real de SerpAPI/Gemini, pero su primera validacion debe ser el entorno:

- Con `ENVIRONMENT=demo`, usa unicamente el rol demo y `demo_db`.
- Con cualquier otro valor, registra un error claro, termina con codigo distinto de cero y no consulta credenciales,
  no crea el orquestador, no llama APIs y no abre una conexion.
- No expone reset ni borrado.
- Persiste y conserva sus resultados en `demo_db`.

Las pruebas automaticas sustituyen las APIs por mocks o respuestas grabadas, pero verifican el mismo selector de base.
La ejecucion contra proveedores reales es un smoke test manual de la demo, nunca parte de la suite automatizada.

### 4.5 Tests

El harness debe reemplazar el aislamiento destructivo actual por una conexion exclusiva por prueba:

1. `setUp` abre una conexion a `destino3_test_db` y comienza una transaccion externa.
2. Un adaptador de conexion/cursor se entrega indirectamente a los repositories sin modificar su codigo de produccion.
3. Cuando un repository llama `commit()`, el adaptador libera y recrea un savepoint interno, manteniendo viva la
   transaccion externa.
4. Cuando un repository llama `rollback()`, el adaptador vuelve al savepoint actual y crea otro.
5. `close()` del repository no cierra la conexion externa; el harness la revierte y la cierra en `tearDown`.
6. No se ejecuta `TRUNCATE`, `DELETE` masivo, `DROP`, reset de identidad ni reseteo de esquema desde los tests.

Los tests deben dejar de depender de una BD vacia: crean sus propios datos dentro de la transaccion, usan identificadores
de prueba controlados y comprueban solo el estado producido por el caso. Las respuestas SerpAPI/Gemini siguen siendo
fixtures o mocks, como exige constitucion #7.

## 5. Decisiones tecnicas y alternativas descartadas

### D1. SQL canonico mas migracion aditiva

- **Eleccion:** mantener `sql/schema.sql` como contrato de bases nuevas y agregar una migracion versionada para la
  columna/indice de `google_place_id` en bases existentes.
- **Alternativa descartada:** usar un ORM o una herramienta nueva de migraciones.
- **Trade-off:** dos caminos de aplicacion requieren mantenerlos coherentes, pero respetan constitucion #1 y #3,
  conservan el SQL crudo existente y evitan introducir dependencias o una abstraccion que la aplicacion no necesita.
- **RF/constitucion:** RF-4 y RF-5; constitucion #1, #3, #11 y #12.

### D2. Unicidad declarativa nullable en PostgreSQL

- **Eleccion:** columna nullable con restriccion/indice unico administrado por PostgreSQL.
- **Alternativa descartada:** consultar primero si existe el `google_place_id` y rechazarlo en Python.
- **Trade-off:** los duplicados se conocen como `IntegrityError` y deben propagarse, pero la regla es atomica y segura
  ante concurrencia. El pre-chequeo produciria carreras y no cumpliria una garantia real de unicidad.
- **RF/constitucion:** RF-4; constitucion #3, #6 y #15. La obligatoriedad, descarte y upsert quedan para spec 005.

### D3. Reset y esquema en una unica transaccion real

- **Eleccion:** `TRUNCATE` y aplicacion del esquema nuevo dentro de la misma transaccion PostgreSQL.
- **Alternativa descartada:** vaciar primero, hacer commit y aplicar el esquema despues.
- **Trade-off:** el procedimiento requiere que el DDL sea transaccional y que el operador mantenga una sola conexion,
  pero permite que un fallo deje la BD exactamente como estaba, incluido su contenido y esquema, como exige RF-2.
- **RF/constitucion:** RF-1, RF-2, RF-3 y RF-5; constitucion #6 y #11.

### D4. Procedimiento operacional no reutilizable

- **Eleccion:** runbook/artefacto operacional de una sola ejecucion, retirado tras el uso y sin simbolo publico en
  `src/`.
- **Alternativa descartada:** endpoint administrativo, comando permanente o metodo `reset()` en un repository.
- **Trade-off:** la operacion es menos automatizable y su evidencia es manual, pero evita convertir una decision
  irreversible en una capacidad repetible y protege RF-9. No se agregan backups, retries ni confirmaciones porque la
  spec los excluye para esta unica ejecucion.
- **RF/constitucion:** RF-1, RF-2, RF-3 y RF-9; constitucion #6, #11 y #13.

### D5. Roles y bases separados por entorno

- **Eleccion:** tres bases y tres roles de aplicacion en la misma instancia, con un rol administrativo separado para
  provisionamiento/esquema.
- **Alternativa descartada:** una base compartida con tablas o prefijos por entorno, o un unico usuario con acceso a las
  tres bases.
- **Trade-off:** aumenta la configuracion de infraestructura y credenciales, pero hace que un error de configuracion no
  sea suficiente para que demo o tests escriban en produccion; es una barrera de seguridad independiente del codigo.
- **RF/constitucion:** RF-5, RF-6, RF-7 y RF-8; constitucion #6, #7 y #14.

### D6. Rechazo estricto de entornos desconocidos

- **Eleccion:** solo se aceptan `testing`, `demo` y `production`; no hay valor por defecto ni fallback.
- **Alternativa descartada:** tratar cualquier entorno desconocido como `production` o reutilizar `DB_NAME`.
- **Trade-off:** despliegues incompletos fallan antes y requieren configurar mas variables, pero un typo no puede dirigir
  una demo o un test a la BD real.
- **RF/constitucion:** RF-6, RF-7 y RF-8; constitucion #6, #12 y #13.

### D7. Rollback por prueba mediante adaptador del harness

- **Eleccion:** conexion externa por prueba, savepoints internos y absorcion de `commit()`/`close()` en el adaptador
  exclusivo de `test/`.
- **Alternativa descartada:** conservar `TRUNCATE` en `setUp`/`tearDown`, borrar filas selectivamente o mockear toda la
  base de datos.
- **Trade-off:** el adaptador es mas complejo que limpiar tablas, pero satisface RF-8 sin borrar datos y prueba el SQL
  real contra PostgreSQL. Mockear la BD ocultaria errores de constraints y transacciones; `TRUNCATE` contradice la spec.
- **RF/constitucion:** RF-8; constitucion #3, #6 y #7.

### D8. Verificacion operacional separada de la suite de aplicacion

- **Eleccion:** verificar la BD real manualmente y comparar los tres esquemas mediante un procedimiento con conexiones
  separadas; automatizar solo las garantias de `destino3_test_db` y la configuracion.
- **Alternativa descartada:** apuntar pruebas automatizadas a la BD real o usar `dblink`/una dependencia adicional para
  consultar tres bases desde PostgreSQL.
- **Trade-off:** la evidencia de RF-1, RF-3 y parte de RF-5 requiere una lista de comprobacion operacional, pero no se
  viola el aislamiento de tests ni se añade una dependencia al stack.
- **RF/constitucion:** RF-1, RF-3 y RF-5; constitucion #1, #7 y #11.

## 6. Piramide de tests

La base de la piramide prueba decisiones puras y guardas rapidamente; el nivel intermedio usa el PostgreSQL real de
tests; la cima cubre el procedimiento y la demo con evidencia controlada. Ningun nivel usa la BD real desde la suite.

### 6.1 Base: unitarios y de contrato

| Area | Casos minimos | RF |
|---|---|---|
| Selector de entorno | tres mapeos validos, entorno desconocido, variables ausentes, ningun intento de fallback | RF-6, RF-7, RF-8 |
| Guarda de demo | `demo` permite construir el flujo; `testing`, `production` y valor invalido terminan antes de conexion/API/orquestador | RF-6, RF-7 |
| Adaptador del harness | `commit()` conserva la transaccion externa, `rollback()` vuelve al savepoint y `close()` no la cierra | RF-8 |
| Modelo/configuracion | `google_place_id` ausente es valido, valor de texto se conserva y no se registran credenciales | RF-4, RF-6 |
| Contrato del esquema | nombre de columna, nulabilidad esperada y nombre estable de la restriccion/indice | RF-4, RF-5 |

### 6.2 Centro: integracion con `destino3_test_db`

| Area | Casos minimos | RF |
|---|---|---|
| Repositorio de hospedajes | persiste un ID de Places; permite varias filas sin ID; rechaza un duplicado no nulo por constraint | RF-4 |
| Integridad del esquema | FKs, checks, unicidades existentes y nueva unicidad sobreviven la aplicacion del schema | RF-4, RF-5 |
| Rollback por prueba | una insercion realizada por un repository se ve dentro del test y desaparece al rollback externo; no quedan filas de otro caso | RF-8 |
| Aplicacion no destructiva | una migracion simulada en una transaccion conserva filas semilla de `destino3_test_db`; una colision de IDs revierte la migracion | RF-5, RF-8 |
| Flujo de demo aislado | con proveedores mock, `ENVIRONMENT=demo` selecciona parametros de `demo_db`; con otro entorno no se llama al flujo | RF-6, RF-7 |

Estos tests usan respuestas grabadas para los proveedores. Si `destino3_test_db` no esta disponible, fallan o se saltan conforme al
harness existente, pero nunca sustituyen PostgreSQL por un mock de persistencia ni cambian a la BD real.

### 6.3 Cima: aceptacion operacional y smoke controlado

| Verificacion | Evidencia | RF |
|---|---|---|
| Reset unico | salida del operador, codigo de resultado y registro de que no hubo backup/retry/restauracion | RF-1, RF-2 |
| BD real vacia | consulta manual de conteo cero para todas las tablas del inventario | RF-3 |
| Tres esquemas equivalentes | comparacion de tablas, columnas, tipos, FKs, checks, indices y nulabilidad | RF-5 |
| Aislamiento de roles | conexiones positivas a la base propia y negativas a las otras dos | RF-6, RF-7, RF-8 |
| Demo real | ejecucion con APIs reales y `ENVIRONMENT=demo`, verificando que los resultados permanecen en `demo_db` | RF-7 |
| Ausencia de reset publico | inspeccion de entry points, servicios y repositories; no existe operacion de vaciado | RF-9 |

RF-1, RF-3 y RF-9 se mantienen como comprobaciones manuales objetivas sobre la BD real/interfaz, tal como exige la
spec y como impone el aislamiento de constitucion #7. No se crea un test que se conecte a produccion.

## 7. Matriz explicita de requisitos por componente y prueba

| RF | Componentes responsables | Verificacion principal |
|---|---|---|
| RF-1 | Procedimiento operacional unico; rol de esquema | Ejecucion unica, salida visible y evidencia de commit; no hay respaldo ni confirmacion añadida |
| RF-2 | Transaccion del procedimiento; manejo de error del operador | Fallo inducido en una base no real durante el ensayo; en real, rollback y estado previo comprobados manualmente |
| RF-3 | Verificador de entornos y checklist post-reset | Conteo cero individual por cada tabla de la BD real |
| RF-4 | `schema.sql`, migracion 002, `Hospedaje`, `HospedajeRepository` | Indice/restriccion unica, nullable aceptado y duplicado no nulo rechazado en `destino3_test_db` |
| RF-5 | Provisionamiento, migracion, selector de conexion y comparador de esquemas | Las tres bases quedan equivalentes; demo/test conservan filas; real combina vaciado y esquema en una transaccion |
| RF-6 | Selector estricto y guarda de `demo_integracion` | Entorno invalido produce error sin conexion ni operacion |
| RF-7 | Mapa de conexion, rol demo y `demo_integracion` | Smoke con mocks/API real en demo; comprobacion de que no existe fallback ni reset |
| RF-8 | Harness de rollback, rol testing y fixtures grabados | Cada prueba revierte su transaccion, no ejecuta limpieza destructiva y no consume APIs reales |
| RF-9 | Ausencia de API/reset en `src`, runbook retirado y revision de interfaz | Inspeccion objetiva de entry points y repositories; cualquier futuro reset requiere nueva decision |

## 8. Secuencia de implementacion propuesta

1. Actualizar el contrato de variables en `.env.example` y definir los tres roles/bases en el procedimiento de
   provisionamiento.
2. Ajustar `sql/schema.sql` para que una base nueva ya incluya `google_place_id` nullable y su unicidad.
3. Crear la migracion aditiva 002 y validar que falla atomica y explicitamente ante duplicados previos.
4. Implementar el mapa estricto de conexiones y adaptar la demo a la guarda `ENVIRONMENT=demo`.
5. Extender el modelo/repositorio de hospedaje para transportar el identificador opcional sin cambiar el alcance de
   spec 005.
6. Construir el adaptador transaccional del harness y eliminar la dependencia de `TRUNCATE` de las pruebas existentes.
7. Agregar tests unitarios e integracion de la base de la piramide y adaptar los tests de spec 003 a la nueva seleccion
   de entorno, sin modificar sus requisitos.
8. Provisionar y migrar `demo_db` y `destino3_test_db`, conservando sus datos y comprobando los roles.
9. Ejecutar el procedimiento unico sobre la BD real bajo la excepcion de spec 004 que autoriza esta ejecucion sin
   confirmacion humana, registrar el resultado y retirar el artefacto operativo.
10. Ejecutar la verificacion manual de cero filas, equivalencia de esquemas, aislamiento de roles y smoke de demo.
11. Ejecutar `python3 -m pytest test/ -q` y cerrar la documentacion de la spec conforme a constitucion #11.

## 9. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigacion |
|---|---|---|
| El DDL o la migracion falla despues del vaciado | Alto | Una unica transaccion en la BD real; no hacer commit entre vaciado y esquema |
| El operador apunta al host/base equivocados | Critico | Preflight de base/rol, mapa estricto y permisos separados; detener antes de `BEGIN` si no coincide |
| `demo` cae en produccion por variable ausente | Critico | Demo exige `ENVIRONMENT=demo`; no hay valor por defecto ni fallback y el rol no tiene acceso cruzado |
| La unicidad encuentra duplicados en una base existente | Alto | Preflight/constraint dentro de transaccion; rollback preserva datos y la correccion queda fuera de la aplicacion |
| Un repository cierra o confirma la conexion del test | Alto | Proxy del harness absorbe `commit`, `rollback` y `close`; prueba especifica de savepoints |
| El esquema de una base diverge del resto | Medio | Schema canonico, migracion versionada y comparacion de metadatos en las tres bases |
| Se reintroduce un reset por conveniencia | Alto | No crear metodo/endpoint de reset; retirar el artefacto unico y exigir nueva decision documentada |

## 10. Criterios de aceptacion del plan

- [ ] Existe un esquema canonico que contiene las siete tablas actuales y la unicidad nullable de
  `hospedajes.google_place_id`.
- [ ] Existe una migracion aditiva para bases existentes que no borra datos y revierte ante duplicados.
- [ ] La seleccion de conexion acepta unicamente `testing`, `demo` y `production`, sin fallback.
- [ ] Los tres entornos tienen base y rol independientes en la misma instancia.
- [ ] La demo solo opera con `demo` y nunca expone reset o borrado.
- [ ] El reset real se ejecuta una sola vez, en una transaccion que incluye vaciado y esquema, sin backup, retry ni
  restauracion automatica.
- [ ] El arnes de tests usa rollback por prueba y no ejecuta operaciones destructivas sobre `destino3_test_db`.
- [ ] La piramide cubre tests unitarios, integracion PostgreSQL y comprobaciones operacionales sin conectar la suite a
  la BD real.
- [ ] Cada RF de RF-1 a RF-9 tiene componentes responsables y una verificacion explicita.
- [ ] La suite completa termina con `python3 -m pytest test/ -q` en verde, con los skips explicados si PostgreSQL no
  esta disponible.

# Clarificaciones — Spec 004 (auditoría QA)

Auditoría de `specs/004-esquema-y-reset-bd/spec.md` contra `docs/constitucion.md` y
`docs/contexto-v2-fuentes-de-verdad.md`. Solo hallazgos; no se proponen soluciones ni código.

## Resumen de hallazgos

| Id | Severidad | Dónde | Por qué es un problema |
|---|---|---|---|
| H-01 | Alta | H4 vs RF-7 | H4 exige que la BD real no reciba «escrituras de demos»; RF-7 permite que la demo corra contra la BD real con confirmación explícita, lo que implica escrituras de demo en la real. Contradicción lógica entre historia y requisito. |
| H-02 | Alta | RF-2 / RF-5 / RF-9 / DoD | Con el orden «vaciar → aplicar esquema» (RF-5), si la fase de aplicación del esquema falla sobre la BD real, esta queda vacía y sin esquema nuevo. RF-9 prohíbe reejecutar el reset y no se define vía de recuperación hacia el DoD («esquema actualizado»). Estado terminal inconsistente no cubierto por ningún caso límite. |
| H-03 | Media | RF-2 | «Durante el reset» es ambiguo tras introducir el orden en dos fases (vaciar + aplicar esquema). El comportamiento «la BD queda como esté» difiere según la fase fallida; no se delimita a cuál aplica RF-2. |
| H-04 | Media | RF-8 vs infra de tests | «La BD de pruebas nunca recibe operaciones destructivas de reset» choca con la práctica existente: `BaseDBTestCase` ejecuta `TRUNCATE … RESTART IDENTITY CASCADE` sobre la BD de pruebas en cada `setUp`/`tearDown`. No se define qué cuenta como «operación destructiva de reset» ni si el `TRUNCATE` de aislamiento de tests entra en la prohibición. |
| H-05 | Media | RF-6 / RF-7 | «La configuración apunta a la BD real» no especifica el mecanismo. El contexto (decisión 1) habla de `DATABASE_URL`; el código usa `ENVIRONMENT` + `DB_NAME` (`destino3_db`)/`DB_TEST_NAME` (`destino3_test_db`). Sin el disparador concreto, RF-6 y RF-7 no se pueden verificar de forma objetiva y reproducible con un test. |
| H-06 | Media | RF-1 / RF-3 / RF-9 | Actúan sobre la BD real, y la constitución #7 más el harness prohíben apuntar tests a la BD real. No se aclara que su verificación es una comprobación objetiva manual (no un test automatizado); el DoD solo exige pruebas automatizadas para la guarda de entorno y la unicidad, generando expectativa de cobertura que no aplica a estos RF. |
| H-07 | Media | Caso límite «Identificador duplicado ya presente» | En la BD real no hay filas al aplicar el esquema (post-vaciado), así que el caso solo puede darse en la BD de pruebas, pero no se acota el entorno, a diferencia del caso «Hoteles existentes sin identificador», que sí lo hace. Tratamiento inconsistente entre casos límite análogos. |
| H-08 | Media | Caso límite «Error a mitad del reset» vs RF-9 | «La decisión de continuar queda en manos del responsable» sugiere que el responsable puede reanudar o repetir; RF-9 y el caso «Intento de repetir el reset» establecen que cualquier vaciado posterior exige una decisión nueva con confirmación humana, fuera de esta spec. Redacciones no delimitadas de forma coherente. |
| H-09 | Media | RF-1 vs RF-9 | RF-1 presupone un modo de ejecutar el reset; RF-9 prohíbe «ofrecer operación de reset repetible». No se delimita cómo se dispara la única ejecución ni qué la diferencia de una «operación ofrecida», lo que deja ambigua la verificabilidad de RF-9 (cómo se prueba la ausencia de una operación de reset). |
| H-10 | Baja | RNF Simplicidad | «Se verifica por inspección de que ninguna de esas tres capacidades existe» carece de criterio objetivo: la «inspección» es subjetiva y no se especifica cómo demostrar la ausencia de respaldos, reintentos y restauración. |
| H-11 | Baja | RF-5 | Mezcla semánticas por entorno: en la BD real «no elimina ni modifica datos existentes» es vacío (ya se vació antes); en la BD de pruebas sí aplica. Un mismo RF describe comportamientos distintos por entorno sin separarlos, propenso a lectura errónea. |
| H-12 | Baja | Límites de tamaño | Casos límite en 6/6 (límite). Si la clarificación añade uno (p. ej. el estado terminal de H-02), se excede el límite y habría que proponer dividir la spec. |
| H-13 | Baja | DoD vs D6 | El DoD usa pasado («se vació / se aplicó»). D6 pidió eliminar redacción que presente el reset como ya ejecutado; conviene confirmar que el tiempo pasado es aceptable por ser criterio de cierre. |

## Notas de revisión (sin hallazgo)

- En la auditoría inicial: 138/150 líneas; RF: 9/12; historias: 5/5; casos límite: 6/6.
- No se detectan nombres de tablas, columnas, endpoints, SQL ni código en la spec.
- Solape con spec 005 (obligatoriedad del identificador, `NOT NULL`, upsert) acotado en «Fuera de alcance» y «Dudas abiertas»; sin huecos.
- La redacción de la regla 5 y la decisión 14 del archivo de contexto coincide con las decisiones D1/D6; sin contradicción con la spec.

## Cierre de hallazgos (ronda D-H01/D-H02/D-H04)

| Hallazgo | Estado | Cómo se cerró |
|---|---|---|
| H-01 | Cerrado | D-H01 prohibió demo→real. La decisión posterior separa `demo_db` de `destino3_test_db`; H2/H4/RF-6/RF-7 y el caso límite quedaron actualizados para `demo_db`. |
| H-02 | Cerrado | D-H02: vaciado y esquema en una sola transacción; si falla, la BD real queda como estaba. RF-2, RF-5 y DoD reescritos; caso «Error a mitad» sustituido por «Error durante el reset». |
| H-03 | Cerrado | D-H02 unifica el reset en una transacción; «durante el reset» queda delimitado a esa transacción única. |
| H-04 | Cerrado | D-H04: tests con reversión por prueba; prohibido reset/borrado/vaciado en tests. RF-8 reescrito. |
| H-05 | Cerrado | Decisión posterior: `testing`→`destino3_test_db`, `demo`→`demo_db`, `production`→`destino3_db`; cualquier otro entorno termina con error. |
| H-06 | Cerrado | RF-1, RF-3 y RF-9 marcados como comprobación manual objetiva sobre la BD real / interfaz pública. |
| H-07 | Cerrado | Caso «Identificador duplicado ya presente» acotado a la BD de pruebas. |
| H-08 | Cerrado | D-H02 reescribe el caso de error: revierte toda la operación; sin opción de reanudar. |
| H-09 | Cerrado | RF-9 marcado como comprobación manual objetiva (la interfaz pública no expone vaciado de la BD real). |
| H-10 | Cerrado | RNF Simplicidad reformulado como comprobación manual objetiva por inspección. |
| H-11 | Cerrado | RF-5 separa explícitamente el comportamiento en BD real (transacción única) y BD de pruebas (sin tocar datos). |
| H-12 | Cerrado | Sin nuevos casos límite: se sustituye «Error a mitad» por «Error durante el reset»; sigue en 6/6. |
| H-13 | Cerrado | DoD en pasado como criterio de cierre, sin afirmar que el reset ya se ejecutó. |

## Resolución de dudas abiertas

| Duda | Estado | Resolución |
|---|---|---|
| Reversión por prueba con repositorios que hacen `commit()` | Cerrada; detalle para el plan | Se usará un adaptador de conexión exclusivo del harness de tests. Mantendrá una conexión externa por prueba; los `commit()` de producción liberarán y recrearán savepoints internos, y el cierre de conexión será absorbido por el adaptador. Al terminar, la transacción externa se revertirá. El código de producción no cambia. Psycopg2 documenta transacciones por conexión y savepoints mediante `cursor.execute()` (<https://www.psycopg.org/docs/usage.html>, *Transactions control*); no ofrece commit anidado nativo. |
| H-05: selección de base | Cerrada | El mapa es `testing`→`destino3_test_db`, `demo`→`demo_db`, `production`→`destino3_db`. Cualquier otro entorno termina con error y no hay fallback. |

La spec conserva únicamente el requisito verificable de RF-8; el diseño detallado del adaptador y sus
pruebas pertenecen al plan de implementación.

## Decisiones posteriores: separación de bases

| Decisión | Estado | Aplicación |
|---|---|---|
| Separar demo y tests | Cerrada | `demo_db` queda dedicada a la demo y `destino3_test_db` queda dedicada a tests; `destino3_db` queda dedicada a la aplicación. |
| Persistencia de demo | Cerrada | La demo usa APIs reales y conserva sus resultados en `demo_db`. |
| Fuente de tests | Cerrada | Los tests usan respuestas grabadas y rollback por prueba en `destino3_test_db`. |
| Selección por entorno | Cerrada | `testing`→`destino3_test_db`, `demo`→`demo_db`, `production`→`destino3_db`; no hay fallback y un entorno inválido termina con error. |
| Aislamiento de acceso | Cerrada | Cada base usa un rol independiente; tests y demo no pueden conectarse a otra base. |
| Esquema | Cerrada | El esquema se aplica a las tres bases; en `demo_db` y `destino3_test_db` no se borran datos. |
| Operaciones destructivas | Cerrada | No hay reset ni borrado de datos desde la aplicación en `demo_db` o `destino3_test_db`; el reset único sigue limitado a `destino3_db`. |
| Provisionamiento | Cerrada | La infraestructura crea las tres bases y sus credenciales; la aplicación no las crea. |
| Instancia PostgreSQL | Cerrada | Las tres bases viven en la misma instancia de PostgreSQL. |

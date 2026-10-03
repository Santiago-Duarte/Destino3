# AGENTS.md — Destino3

## Proyecto

Destino3 recomienda alojamiento real: busca hospedajes con SerpAPI, los evalúa con Gemini (Top 3 con análisis de IA) y los persiste en PostgreSQL para reutilizarlos. Proyecto construido por fases (BD → backend → APIs externas → CLI → API REST → frontend → despliegue); la fase activa integra las APIs externas.

- Stack: Python 3.13 · PostgreSQL con psycopg2 (SQL crudo, sin ORM) · SerpAPI · Google GenAI (Gemini) · Pydantic · python-dotenv · pytest (solo como runner de tests).
- Arquitectura: `modelos → repositories → services → orquestación → config → entry point` (capas estrictas, constitución #2).

## Estructura

- `src/models/` — modelos de dominio (clases simples; solo `evaluacion_ia.py` usa Pydantic).
- `src/repositories/` — único lugar con SQL crudo (psycopg2).
- `src/services/` — APIs externas: `api_searcher.py` (SerpAPI), `ai_evaluator.py` (Gemini).
- `src/orchestrator/` — orquestación del flujo de evaluación.
- `src/config/` — `settings.py` (parámetros operativos), `database.py` (conexión), `__init__.py` (carga del `.env`).
- `src/main.py` — vacío: la app aún no tiene punto de entrada.
- `test/` — pruebas en `unittest` (`db_test_case.py` define `BaseDBTestCase`); **no** existe `conftest.py` ni fixtures de pytest.
- `sql/` — `schema.sql` (esquema nuevo) y `migrations/*.sql` (se aplican a mano).
- `docs/constitucion.md` — reglas permanentes del proyecto.
- `specs/003-integracion-apis-externas/` — spec + plan + tasks de la fase activa.
- `fases/fase-1.md` … `fases/fase-7.md` — roadmap por fases.
- `.env` (gitignored) y `.env.example` — variables de entorno.

## Fuentes de verdad

- `docs/constitucion.md` manda sobre cualquier otra fuente.
- Fase activa: `specs/003-integracion-apis-externas/` → `spec.md` (requisitos), `plan.md` (decisiones), `tasks.md` (qué está hecho y qué no).
- Fuera de esas fuentes no se inventan requisitos (reglas #1 y #2 de más abajo).
- Las specs citan reglas de este archivo como «AGENTS.md #N»: **mantén la numeración**.
- Rutas antiguas que ya no existen y que aún aparecen en documentación: `specs/arquitectura.md`, `specs/reglas.md`, `specs/estado.md`, `specs/decisiones/`.

## Comandos

- Instalar dependencias: `python3 -m pip install -r requirements.txt`
- Tests (todos): `python3 -m pytest test/ -q` (desde la raíz del repo)
- Test individual: `python3 -m pytest test/test_destinos.py::TestDestinos::test_crear_destino_cuando_no_existe -q`
- Ver por qué un test se salta: `python3 -m pytest test/ -q -rs`
- Lint / formato / typecheck / build: **no existen** en este proyecto; la única verificación es la suite en verde.
- **pytest no está en `.venv` ni en `requirements.txt`**: usa el `python3` del sistema (3.13), que ya tiene `psycopg2`, `dotenv`, `requests`, `google-genai`, `pydantic` y `pytest`. Si falta: `python3 -m pip install pytest`.
- No hay ejecutable: `src/main.py` está vacío; el bloque `__main__` de `src/services/api_searcher.py` es una prueba manual, no el entry point de la app.

## Base de datos de pruebas

- `ENVIRONMENT=testing` → `src/config/database.py` conecta a `DB_TEST_NAME`; cualquier otro valor usa `DB_NAME`. `test/__init__.py` y `test/db_test_case.py` fijan `ENVIRONMENT=testing` al importarse.
- Con PostgreSQL apagado **la suite nunca falla**: los tests que heredan de `BaseDBTestCase` se saltan (`SkipTest` si no conecta). Todos los `skipped` deben venir de ahí (compruébalo con `-rs`); con el motor encendido no debería haber ningún skip.
- `BaseDBTestCase` hace `TRUNCATE` de `busquedas, recomendaciones, evaluaciones_ia, hospedajes, destinos, usuarios` en cada `setUp`/`tearDown`: nunca apuntes los tests a una BD real.
- Esquema nuevo: `sql/schema.sql`. A BDs existentes aplica a mano `sql/migrations/*.sql` (no hay sistema de migraciones automatizado).
- `.env` (gitignored, ver `.env.example`) se carga con `load_dotenv()` en `src/config/__init__.py`: importar cualquier cosa de `src.config` ya lee el `.env`.

## Arquitectura (lo que no se deduce de los nombres)

- Repositories = único lugar con SQL crudo (psycopg2). Services no ejecutan SQL; repositories no importan services. `services → repositories` sí está permitido (`api_searcher` lo hace).
- Los modelos de dominio en `src/models/*.py` son clases simples; **solo** `src/models/evaluacion_ia.py` usa Pydantic (valida la respuesta de Gemini).
- `id_temporal` existe solo en memoria durante la evaluación IA: nunca persistirlo. Los IDs reales los genera PostgreSQL.
- La config operativa (timeouts, reintentos, rate limit, claves) vive en `src/config/settings.py` y se lee **al importar**: para probar cambios de variables de entorno hay que recargar el módulo (lo hace `test/test_config_settings.py`).

## Estilo y convenciones

- Lenguaje: Python 3.13 con type hints; sin dependencias nuevas sin ADR (constitución #1).
- Nombres: `snake_case` en funciones y variables, `PascalCase` en clases; formato manual consistente porque no hay linter (constitución #9).
- Idioma: código, logs, comentarios y mensajes en español.
- Docstrings con `Args:`/`Returns:` en español, como el código existente.
- Sigue los patrones del código existente antes de introducir uno nuevo.

## Reglas

- Antes de tocar código, lee `docs/constitucion.md` y la spec activa (`specs/003-integracion-apis-externas/`): ahí manda la constitución.
- Haz cambios pequeños y enfocados en lo que se pidió; nada de refactors no solicitados.
- **Pregunta antes de:** añadir dependencias, cambiar la estructura de carpetas, modificar el esquema de datos (`sql/`) o la API pública, borrar archivos.
- **Nunca:** commitear `.env` o credenciales, editar archivos generados (`__pycache__/`, `*.pyc`, `respuesta_prueba.json`), desactivar tests para que pasen, apuntar los tests a una BD real.
- Si algo es ambiguo o contradice la spec, detente y pregunta en lugar de suponer.

### Reglas que las specs citan como «AGENTS.md #N»

Mantén esta numeración: `specs/003-*/plan.md` las referencia por número.

1. Las specs son la fuente de verdad; no cambies una decisión documentada sin actualizar la spec o el ADR.
2. No inventes requisitos fuera del roadmap o de una spec existente.
3. Repository Pattern: repositories = único SQL, services no ejecutan SQL, repositories no importan services.
4. Separa responsabilidades por capas; no muevas lógica de una a otra para acelerar.
5. SerpAPI y Gemini encapsulados en services; la lógica interna no depende de detalles del proveedor.
6. Gemini: entrada/salida estructurada y validada con Pydantic antes de usarla.
7. Solo PostgreSQL genera IDs persistentes; `id_temporal` nunca se persiste.
8. Persistencia con modelos propios del dominio, no con modelos del proveedor.
9. Tests en `unittest` (+ mocks de APIs externas; BD de pruebas para integración). Pytest es solo el runner: no introduces `conftest.py` ni fixtures de pytest.
10. Errores explícitos: no los ocultes con `print()`/`None`; propaga y que la capa superior decida.
11. Cambios de capas, BD, flujo principal o integración externa: revisa specs/ADRs antes de implementar.
12. Si la implementación cambia una decisión o el estado de una fase, actualiza la documentación.

## Al terminar cualquier tarea

- Ejecuta `python3 -m pytest test/ -q` y confirma que queda en verde (no hay lint que ejecutar).
- Comprueba que el cambio cumple la spec activa y la constitución; si cambia una decisión o el estado de una fase, actualiza la documentación (#12).
- Resume qué cambiaste, qué archivos tocaste y qué queda pendiente.

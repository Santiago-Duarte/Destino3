# AGENTS.md — Destino3

## Proyecto

Destino3 recomienda alojamiento real: busca hospedajes con SerpAPI, los evalúa con Gemini (Top 3 con análisis de IA) y
los persiste en PostgreSQL para reutilizarlos. Proyecto construido por fases (BD → backend → APIs externas → CLI → API
REST → frontend → despliegue); la fase activa integra las APIs externas.

- Stack: Python 3.13 · PostgreSQL con psycopg2 (SQL crudo, sin ORM) · SerpAPI · Google GenAI (Gemini) · Pydantic ·
  python-dotenv · pytest (solo como runner de tests).
- Arquitectura: `modelos → repositories → services → orquestación → config → entry point` (capas estrictas, constitución
  #2).

## Estructura

- `src/models/` — modelos de dominio (clases simples; solo `evaluacion_ia.py` usa Pydantic).
- `src/repositories/` — único lugar con SQL crudo (psycopg2).
- `src/services/` — APIs externas: `buscador_serpapi.py` (SerpAPI), `evaluador_ia.py` (Gemini).
- `src/orchestrator/` — orquestación del flujo de evaluación.
- `src/config/` — `settings.py` (parámetros operativos), `database.py` (conexión), `__init__.py` (carga del `.env`).
- `src/main.py` — vacío: la app aún no tiene punto de entrada.
- `test/` — pruebas en `unittest` (`db_test_case.py` define `BaseDBTestCase`); **no** existe `conftest.py` ni fixtures
  de pytest.
- `sql/` — `schema.sql` (esquema nuevo) y `migrations/*.sql` (se aplican a mano).
- `operacion/` — artefactos operacionales fuera de `src/` y sin interfaz pública (spec 004:
  `reset/preflight.py` inventario y validación base/rol; `reset/procedimiento.py` transacción única de
  vaciado + esquema con evidencia en `reset/evidencia_reset.json` que bloquea reejecutar (RF-9);
  `reset/ejecutar.py` orquesta preflight con el rol de production y transacción con el dueño de las tablas).
- `docs/constitucion.md` — reglas permanentes del proyecto.
- `specs/003-integracion-apis-externas/` — spec + plan + tasks de la fase activa.
- `fases/fase-1.md` … `fases/fase-7.md` — roadmap por fases.
- `.env` (gitignored) y `.env.example` — variables de entorno.

## Fuentes de verdad

- `docs/constitucion.md` manda sobre cualquier otra fuente.
- Fase activa: `specs/003-integracion-apis-externas/` → `spec.md` (requisitos), `plan.md` (decisiones), `tasks.md` (qué
  está hecho y qué no).
- Fuera de esas fuentes no se inventan requisitos (constitución #12 y #13).
- Specs y código citan las reglas como «constitución #N»: **mantén la numeración** de `docs/constitucion.md`.
- Rutas antiguas que ya no existen y que aún aparecen en documentación: `specs/arquitectura.md`, `specs/reglas.md`,
  `specs/estado.md`, `specs/decisiones/`.

## Comandos

- Instalar dependencias: `python3 -m pip install -r requirements.txt`
- Tests (todos): `python3 -m pytest test/ -q` (desde la raíz del repo)
- Test individual: `python3 -m pytest test/test_destino_repository.py::TestDestinoRepository::test_crear_destino_cuando_no_existe -q`
- Ver por qué un test se salta: `python3 -m pytest test/ -q -rs`
- Lint / formato / typecheck / build: **no existen** en este proyecto; la única verificación es la suite en verde.
- **pytest no está en `.venv` ni en `requirements.txt`**: usa el `python3` del sistema (3.13), que ya tiene `psycopg2`,
  `dotenv`, `requests`, `google-genai`, `pydantic` y `pytest`. Si falta: `python3 -m pip install pytest`.
- No hay ejecutable: `src/main.py` está vacío y la app aún no tiene entry point.

## Base de datos de pruebas

- `ENVIRONMENT=testing` → `src/config/database.py` conecta a `DB_TEST_NAME`; cualquier otro valor usa `DB_NAME`.
  `test/__init__.py` lo fija al importarse, antes de que cualquier módulo de `src.config` lea la variable.
- Con PostgreSQL apagado **la suite nunca falla**: los tests que heredan de `BaseDBTestCase` se saltan (`SkipTest` si no
  conecta). Todos los `skipped` deben venir de ahí (compruébalo con `-rs`); con el motor encendido no debería haber
  ningún skip.
- `BaseDBTestCase` hace `TRUNCATE` de `busquedas, recomendaciones, evaluaciones_ia, hospedajes, destinos, usuarios` en
  cada `setUp`/`tearDown`: nunca apuntes los tests a una BD real.
- Esquema nuevo: `sql/schema.sql`. A BDs existentes aplica a mano `sql/migrations/*.sql` (no hay sistema de migraciones
  automatizado).
- `.env` (gitignored, ver `.env.example`) se carga con `load_dotenv()` en `src/config/__init__.py`: importar cualquier
  cosa de `src.config` ya lee el `.env`.

## Arquitectura (lo que no se deduce de los nombres)

- Repositories = único lugar con SQL crudo y services no ejecutan SQL (constitución #3); `services → repositories` sí
  está permitido (`buscador_serpapi` lo hace).
- Los repositories **propagan** cualquier error de SQL y `_transaccion` revierte; la capa superior es la que decide
  qué responder (constitución #6).
- `id_temporal` solo vive en memoria durante la evaluación IA (constitución #4); los IDs reales los genera PostgreSQL.
- La config operativa (timeouts, reintentos, rate limit, claves) vive en `src/config/settings.py` y se lee **al
  importar**: para probar cambios de variables de entorno hay que recargar el módulo (lo hace
  `test/test_config_settings.py`).

## Estilo y convenciones

- Lenguaje: Python 3.13 con type hints; sin dependencias nuevas sin ADR (constitución #1).
- Nombres: `snake_case` en funciones y variables, `PascalCase` en clases; formato manual consistente porque no hay
  linter (constitución #9).
- Idioma: código, logs, comentarios y mensajes en español.
- Docstrings con `Args:`/`Returns:` en español, como el código existente.
- Sigue los patrones del código existente antes de introducir uno nuevo.

## Reglas

- Antes de tocar código, lee `docs/constitucion.md` y la spec activa (`specs/003-integracion-apis-externas/`): ahí manda
  la constitución.
- Haz cambios pequeños y enfocados en lo que se pidió; nada de refactors no solicitados.
- **Pregunta antes de:** añadir dependencias, cambiar la estructura de carpetas, modificar el esquema de datos (`sql/`)
  o la API pública, borrar archivos.
- **Nunca:** commitear `.env` o credenciales, editar archivos generados (`__pycache__/`, `*.pyc`,
  `respuesta_prueba.json`), desactivar tests para que pasen, apuntar los tests a una BD real.
- Si algo es ambiguo o contradice la spec, detente y pregunta en lugar de suponer.

### Reglas permanentes

Las reglas viven en `docs/constitucion.md` con numeración canónica (#1–#15): léelas antes de tocar código y
cítalas como **«constitución #N»**. Aquí no se copian para no duplicarlas.

## Al terminar cualquier tarea

- Ejecuta `python3 -m pytest test/ -q` y confirma que queda en verde (no hay lint que ejecutar).
- Comprueba que el cambio cumple la spec activa y la constitución; si cambia una decisión o el estado de una fase,
  actualiza la documentación (constitución #11).
- Resume qué cambiaste, qué archivos tocaste y qué queda pendiente.

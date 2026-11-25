# Destino3

CLI que busca hoteles en lenguaje natural, los puntúa con IA y devuelve los mejores candidatos.

```bash
python -m src.main "quiero hoteles en Medellin, Colombia hasta 100 USD cerca del metro"
```

## Qué hace

1. **Interpreta la frase con Gemini**: extrae ciudad, país, presupuesto máximo por noche y preferencias.
2. **Consulta Google Hotels vía SerpAPI**: usa una estancia provisoria de 2 noches, 7 días después de hoy, moneda USD y español.
3. **Persiste en PostgreSQL**: crea o reutiliza el destino y hace upsert de los hoteles por `google_place_id`.
4. **Preselecciona**: filtra por presupuesto, ordena por calificación y precio, y deja hasta 10 candidatos para la IA.
5. **Analiza y puntúa con Gemini**:
   - análisis intrínseco del hotel, persistido en `analisis_ia` y reutilizado;
   - doble score por búsqueda: calidad y cumplimiento de lo pedido.
6. **Rankea y muestra**: cumplimiento primero, calidad después; top 3 con requisitos cumplidos/faltantes y URL de reserva.

Si la IA falla, la búsqueda continúa sin análisis o sin puntaje. Si fallan SerpAPI, PostgreSQL o la configuración, el CLI muestra el error y sale con código distinto de 0.

## Requisitos

- Python 3.13
- PostgreSQL 15 o superior
- Cuenta y API key de [SerpAPI](https://serpapi.com/)
- API key de Gemini

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Completa en `.env` las credenciales de SerpAPI, Gemini y las tres bases.

## Base de datos

El proyecto usa tres entornos seleccionados con `ENVIRONMENT`: `testing`, `demo` y `production`.

Para crear roles, bases y esquema:

```bash
set -a
source .env
set +a
psql -h "$DB_HOST" -p "$DB_PORT" -d postgres -f sql/crear_bases.sql
```

Ese script aplica `sql/schema.sql` en cada base.

### Actualizar una base existente

Aplica las migraciones en orden. Cada una es idempotente en lo posible, pero
está pensada para ejecutarse una sola vez:

```bash
set -a
source .env
set +a
for migracion in sql/migraciones/*.sql; do
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_TEST_USER" -d "$DB_TEST_NAME" \
    -f "$migracion"
done
```

Repite el comando para la base de demo o producción cambiando las variables.
Las migraciones actuales:

- `001_direccion_text.sql`: permite descripciones de más de 200 caracteres.
- `002_descripcion.sql`: separa `descripcion` de `direccion` y mueve los
  datos antiguos.
- `003_analisis_version.sql`: versiona el análisis y registra su última
  actualización.

## Uso

Ejecuta el programa sin argumentos y escribe la frase cuando la pida:

```bash
python -m src.main
```

```text
¿Qué hoteles buscas? (ej. "hoteles en Medellin hasta 100 USD cerca del metro"): hoteles en Cartagena cerca de la playa
```

Si pulsas Enter sin escribir nada, vuelve a preguntar. Con `--help` puedes ver
la ayuda del comando:

```bash
python -m src.main --help
```

Salida esperada:

```text
Búsqueda: Medellin, Colombia | presupuesto: hasta USD $100/noche
Preferencias: cerca del metro

TOP 3 de 7 candidatos

1. Hotel Ejemplo — USD $80/noche — calificación 4.5
   Cumplimiento 9/10 | calidad 8/10
   Cumple: presupuesto hasta 100 USD, cerca del metro
   Falta: —
   ...
   Reserva: https://www.google.com/travel/hotels/entity/...
```

## Pruebas

```bash
pytest
```

Las pruebas de integración usan PostgreSQL y se omiten si no hay conexión. En CI o cuando quieras exigir la base:

```bash
REQUIRE_DB_TESTS=1 pytest
```

Calidad estática:

```bash
ruff check .
mypy src
```

## Estructura

```text
src/
  config/        settings y conexión a PostgreSQL
  models/        modelos de dominio y contratos Pydantic para Gemini
  repositories/  acceso a datos y transacciones
  services/      SerpAPI, Gemini, interpretación y evaluación
  orchestrator/  flujo completo de búsqueda
  main.py        CLI
sql/             esquema, creación de bases y migraciones
test/            pruebas unitarias y de integración
```

## Configuración

Los valores de proveedores y comportamiento están en `src/config/settings.py`:

- `SERPAPI_*`: timeout, páginas, resultados, rate limit y reintentos.
- `GEMINI_*`: modelo, timeout, reintentos, backoff y temperatura.
- `MAX_CANDIDATOS_IA`, `TOP_RESULTADOS`, `SCORE_CUMPLIMIENTO_MINIMO`.
- `ANALISIS_VERSION`: súbelo cuando cambie el prompt de análisis para
  invalidar los análisis guardados.

## Limitaciones actuales

- Las fechas son provisorias: entrada en 7 días y salida 2 días después.
- El presupuesto se asume en USD.
- Se consulta una sola página de Google Hotels para acotar costo y latencia.
- El top es de 3 hoteles y la ocupación usa el default de Google.
- No hay migraciones automáticas ni servicio web; el uso actual es CLI.

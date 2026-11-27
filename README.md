# Destino3

CLI que busca hoteles en lenguaje natural, los puntúa con IA y devuelve los mejores candidatos.

```bash
python -m src.main "quiero hoteles en Medellin, Colombia hasta 100 USD cerca del metro"
```

## Qué hace

1. **Interpreta la frase con Gemini**: extrae ciudad, país, fechas, ocupación, presupuesto máximo por noche, preferencias, distancia máxima y, si se pide, un punto de referencia específico (ej. "cerca del metro", "cerca del aeropuerto", "cerca de la playa El Rodadero").
2. **Consulta Google Hotels vía SerpAPI**: usa las fechas y la ocupación reales, moneda USD y español.
3. **Persiste en PostgreSQL**: crea o reutiliza el destino y hace upsert de los hoteles por `google_place_id`, incluidas sus coordenadas GPS.
4. **Calcula distancias verificables**: geocodifica el punto de referencia pedido (o el centro de la ciudad si no se especifica) con Nominatim (OSM), calcula la distancia en línea recta (haversine) y estima tiempos en auto, transporte público y a pie. Si la frase pide un radio ("a menos de 1 km"), descarta los hoteles fuera de él.
5. **Preselecciona**: filtra por presupuesto, ordena por calificación y precio, y deja hasta 10 candidatos para la IA.
6. **Analiza y puntúa con Gemini**:
   - análisis intrínseco del hotel, persistido en `analisis_ia` y reutilizado;
   - doble score por búsqueda: calidad y cumplimiento de lo pedido;
   - la distancia y los tiempos ya calculados se pasan como datos objetivos, indicando desde qué punto se midieron.
7. **Rankea y muestra**: cumplimiento primero, calidad después; top 3 con distancia, tiempos, punto de referencia usado, requisitos cumplidos/faltantes y URL de reserva.

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
- `004_coordenadas_hospedajes.sql`: añade `latitud`/`longitud` a los hoteles.
- `005_coordenadas_destinos.sql`: añade `latitud`/`longitud` a los destinos.

## Uso

Ejecuta el programa sin argumentos y escribe la frase cuando la pida:

```bash
python -m src.main
```

```text
¿Qué hoteles buscas? (ej. "hoteles en Medellin hasta 100 USD cerca del metro"): hoteles en Cartagena del 12 al 15 de diciembre para 2 adultos
```

El programa extrae de la frase la ciudad, las fechas, la ocupación y el presupuesto.
Si falta algo, lo pregunta por consola:

```text
Necesito las fechas de entrada y salida.
Entrada [dd/mm] (vie 27/11): 
Salida [dd/mm] (dom 29/11): 
Adultos [2]: 
Niños [0]: 
¿Viajan con mascotas? (s/n) [n]: 

Destino: Cartagena, Colombia
Fechas: vie 27/11 → dom 29/11 (2 noches)
Ocupación: 2 adultos, 0 niños, sin mascotas
Presupuesto: sin límite
¿Buscar con estos datos? [S/n]: 
```

- Enter acepta el valor mostrado.
- Las fechas se escriben como `dd/mm` o `dd/mm/aaaa`; el año se infiere si falta.
- No se aceptan fechas pasadas, salidas anteriores a la entrada, estancias de más de 30 noches ni entradas a más de un año.
- Solo se pide confirmación cuando hubo que completar datos.
- Si la frase pide una distancia máxima ("a menos de 1 km del centro"), se aplica como filtro duro y se muestra en el resumen.

Si pulsas Enter sin escribir la frase, vuelve a preguntar. Con `--help` puedes ver
la ayuda del comando:

```bash
python -m src.main --help
```

Salida esperada:

```text
Búsqueda: Medellin, Colombia | 04/12 → 06/12 (2 noches) | 2 adultos, 0 niños
Presupuesto: hasta USD $100/noche
Preferencias: cerca del metro

TOP 3 de 7 candidatos

1. Hotel Ejemplo — USD $80/noche — calificación 4.5
   0.85 km de estación metro Poblado | auto 2 min | bus 3 min | a pie 10 min
   Cumplimiento 9/10 | calidad 8/10
   Cumple: presupuesto hasta 100 USD, cerca del metro
   Falta: —
   ...
   Reserva: https://www.google.com/travel/hotels/entity/...
```

La distancia es la línea recta entre el punto de referencia (centro de la ciudad,
estación de metro, aeropuerto, etc.) y el hotel; los tiempos son estimaciones
por velocidad media urbana (auto 30 km/h, transporte público 20 km/h, a pie 5 km/h),
no rutas reales.

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
- `NOMINATIM_*`: URL, timeout, rate limit y `User-Agent` para la geocodificación.
- `MAX_CANDIDATOS_IA`, `TOP_RESULTADOS`, `SCORE_CUMPLIMIENTO_MINIMO`.
- `ANALISIS_VERSION`: súbelo cuando cambie el prompt de análisis para
  invalidar los análisis guardados.

## Limitaciones actuales

- El presupuesto se asume en USD.
- Se consulta una sola página de Google Hotels para acotar costo y latencia.
- El top es de 3 hoteles.
- La distancia se mide desde el punto de referencia geocodificado (centro de la ciudad,
  estación de metro, aeropuerto, etc.); si Nominatim no resuelve el punto concreto,
  se usa el centro como fallback.
- No hay migraciones automáticas ni servicio web; el uso actual es CLI.

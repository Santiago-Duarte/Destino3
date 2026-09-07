# ADR-001 — Repository Pattern

## Estado

ACEPTADA

## Contexto

Destino3 necesita separar el acceso a PostgreSQL de la lógica de negocio.

## Decisión

Destino3 utilizará Repository Pattern.

Cada entidad persistente tendrá un Repository responsable de las operaciones de persistencia.

Los repositories utilizan SQL crudo mediante `psycopg2`.

## Consecuencias

### Positivas

- Separación entre persistencia y negocio.
- Mayor facilidad para testing.
- Control explícito sobre SQL.
- Menor acoplamiento entre Services y PostgreSQL.

### Negativas

- Mayor cantidad de código.
- Mapeo manual entre resultados SQL y modelos.
- Necesidad de mantener múltiples repositories.

## Restricciones

Los repositories no deben importar Services.

Los Services no deben ejecutar SQL directamente.
# Constitución — Destino3

> Numeración canónica: specs, código y `AGENTS.md` citan estas reglas como **«constitución #N»**.
> No renumerar: las citas existentes dependen de estos números.

1. **Stack fijo**: Python 3.13, PostgreSQL/psycopg2, SerpAPI, Google GenAI, Pydantic. Sin añadir dependencias sin ADR.
2. **Capas estrictas**: modelos → repositories (SQL crudo) → services (APIs externas) → orchestration → config → entry point. No cruzar capas.
3. **Repository Pattern**: Repositories = único lugar con SQL. Services no ejecutan SQL. Repositories no importan services.
4. **IDs**: Solo PostgreSQL genera IDs persistentes. `id_temporal` solo en memoria durante evaluación IA; nunca se persiste.
5. **Validación obligatoria**: Entrada/salida de Gemini con Pydantic. Validar antes de usar.
6. **Errores explícitos**: No ocultar con `print()`/`None`. Propagar excepciones; capa superior decide respuesta.
7. **Tests**: `unittest` + mocks de APIs externas. BD de pruebas para integración. Pytest solo runner. Cobertura mínima: servicios core y repositories.
8. **Idioma**: Código, logs, errores en español.
9. **Sin lint configurado**: Formato manual consistente (snake_case, PascalCase).
10. **Cambios arquitectónicos**: Requieren revisar `../fases`, `specs/arquitectura.md` y ADRs antes de implementar.
11. **Documentación viva**: Actualizar specs/ADRs/estado al cambiar decisiones, reglas o fases.
12. **Las specs son fuente de verdad**: No cambiar una decisión documentada sin actualizar la spec o el ADR.
13. **No inventar requisitos**: Fuera del roadmap o de una spec existente no hay requisitos.
14. **Aislamiento de proveedores**: SerpAPI y Gemini encapsulados en services; la lógica interna no depende de detalles del proveedor.
15. **Modelos propios del dominio**: Persistir con modelos del dominio, nunca con modelos del proveedor.
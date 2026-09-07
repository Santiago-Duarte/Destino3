# AGENTS.md — Destino3

## Propósito

Este archivo define las reglas que deben seguir los agentes de IA al trabajar sobre Destino3.

Las especificaciones funcionales y arquitectónicas del proyecto se encuentran en `specs/`.

Antes de modificar el proyecto, el agente debe consultar:

1. `specs/arquitectura.md`
2. `specs/reglas.md`
3. `specs/estado.md`
4. La spec de la fase correspondiente
5. Los ADR relacionados con la tarea

---

## Principios generales

### 1. Respetar las specs

Las specs representan la fuente de verdad del comportamiento esperado de Destino3.

El agente no debe modificar una decisión documentada simplemente porque exista otra alternativa técnicamente válida.

Si una decisión documentada necesita cambiar, primero debe actualizarse la especificación o crear/modificar el ADR correspondiente.

---

### 2. No inventar requisitos

No agregar funcionalidades que no formen parte del roadmap o de una spec existente.

Una mejora potencial debe considerarse como una propuesta separada y no incorporarse automáticamente al desarrollo actual.

---

### 3. Repository Pattern

Destino3 utiliza Repository Pattern.

Los repositories son responsables del acceso a PostgreSQL mediante SQL crudo.

Los Services no deben ejecutar SQL directamente.

Los repositories no deben importar Services.

---

### 4. Separación de responsabilidades

Cada componente debe tener una responsabilidad clara.

La arquitectura distingue entre:

- modelos;
- repositories;
- services;
- orquestación;
- configuración;
- punto de entrada.

No colocar responsabilidades de una capa en otra únicamente para acelerar una implementación.

---

### 5. Servicios externos

SerpAPI y Gemini son dependencias externas.

Su comportamiento debe estar encapsulado en Services.

La lógica interna de Destino3 no debe depender directamente de detalles innecesarios de los proveedores externos.

---

### 6. Gemini

Gemini debe recibir información estructurada y devolver información estructurada.

Las respuestas de Gemini deben validarse antes de utilizarse.

Los identificadores temporales utilizados para relacionar candidatos con las respuestas de Gemini no son IDs persistentes.

---

### 7. Identificadores

El ID real de una entidad persistida pertenece a PostgreSQL.

`id_temporal` solamente existe durante el procesamiento de la evaluación IA.

Nunca debe persistirse `id_temporal`.

Cuando sea necesario, la aplicación debe resolver:

`id_temporal → hospedaje_id real`

---

### 8. Persistencia

Los repositories deben trabajar con modelos propios de Destino3.

La capa de persistencia no debe depender de modelos pertenecientes directamente a un proveedor externo.

---

### 9. Testing

El proyecto utiliza `unittest`.

No introducir `pytest`, `conftest.py` ni fixtures de pytest salvo que exista una decisión explícita posterior para cambiar la estrategia.

Los servicios externos deben mockearse en las pruebas unitarias.

La base de datos de pruebas puede utilizarse para pruebas de integración.

---

### 10. Manejo de errores

Los errores importantes no deben ocultarse mediante `print()` y `None`.

El agente debe preservar errores explícitos y permitir que la capa adecuada decida cómo responder.

---

### 11. Cambios arquitectónicos

Cualquier modificación que afecte:

- estructura de capas;
- Repository Pattern;
- relaciones entre entidades;
- persistencia;
- flujo principal;
- integración con APIs externas;

debe revisarse contra `specs/arquitectura.md` y los ADR correspondientes.

---

### 12. Actualización de documentación

Cuando una implementación cambie una decisión, una regla, el estado de una fase o una parte importante de la arquitectura, la documentación correspondiente debe actualizarse.

---

## Flujo de trabajo

Antes de implementar:

1. Leer `AGENTS.md`.
2. Leer la spec de la tarea.
3. Revisar la arquitectura.
4. Revisar las reglas relacionadas.
5. Revisar ADRs relacionados.
6. Inspeccionar el código actual.
7. Implementar únicamente lo necesario.
8. Ejecutar las pruebas correspondientes.
9. Actualizar el estado del SDD si corresponde.

---

## Regla fundamental

El agente debe implementar el sistema definido por las specs, no rediseñar Destino3 por iniciativa propia.

Cuando exista una decisión no definida, debe señalarla antes de asumirla.
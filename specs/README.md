# Destino3 — Specifications

Esta carpeta contiene las especificaciones utilizadas para desarrollar Destino3 mediante Spec-Driven Development.

## Estructura

### arquitectura.md

Define la arquitectura objetivo del sistema, las capas, responsabilidades y dependencias permitidas.

### reglas.md

Define las reglas de negocio e invariantes que debe respetar el sistema.

### estado.md

Describe el estado actual del proyecto.

### proximas-tareas.md

Define las siguientes tareas que deben realizarse según el estado actual y el roadmap.

### fases/

Contiene la especificación de cada una de las siete fases del proyecto.

Cada fase define su objetivo, requisitos, restricciones y criterios de aceptación.

### decisiones/

Contiene los Architecture Decision Records (ADR).

Cada ADR documenta una decisión importante, su motivo y sus consecuencias.

---

## Fuente de verdad

La documentación de esta carpeta debe mantenerse alineada con la implementación.

Una decisión pendiente no debe documentarse como una decisión definitiva.

Una característica no implementada no debe describirse como completada.

---

## Orden recomendado para consultar el SDD

1. `AGENTS.md`
2. `specs/arquitectura.md`
3. `specs/reglas.md`
4. `specs/estado.md`
5. `specs/fases/`
6. `specs/decisiones/`
7. `specs/proximas-tareas.md`
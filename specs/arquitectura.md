# Arquitectura — Destino3

## Objetivo

Destino3 utiliza una arquitectura por capas orientada a separación de responsabilidades.

La arquitectura debe permitir:

- aislar la persistencia;
- aislar servicios externos;
- mantener la lógica de negocio separada;
- facilitar testing;
- permitir evolucionar desde CLI hacia API REST y frontend web.

---

## Capas

```text
main.py
   ↓
orchestrator/
   ↓
services/
   ↓
repositories/
   ↓
config/

Los modelos se utilizan como estructuras de dominio e intercambio.

models/
   ↑
services/
   ↑
repositories/
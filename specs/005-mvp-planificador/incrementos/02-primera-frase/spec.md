# Spec — I2 · Primera frase (V0)

- **Incremento:** I2
- **Fases:** 2 (infraestructura), 3 (interpretación y CLI) y 4 (destino, ancla y hoteles)
- **Tasks:** 21 (`I2-001`–`I2-021`)
- **Esfuerzo:** 865 min ≈ 14,4 h
- **Depende de:** I1 cerrado (`I1-021`)
- **RF que cubre en V0:** RF-1, RF-2, RF-3, RF-4, RF-5, RF-7 (parcial), RF-12 (parcial)
- **Spec madre:** [`../../spec.md`](../../spec.md) — los RF se citan, no se redefinen.
- **Diferido a V1:** distancias reales (RF-6), evaluación IA (RF-8), itinerario (RF-10), caché y matriz de degradación (RF-12).

## 1. Objetivo

Que una frase en español se convierta en una solicitud validada y en hoteles reales en COP, sin preguntar lo que ya está dicho y sin consultar proveedores antes de completar los datos.

## 2. Alcance

- Errores tipados y cliente HTTP con reintentos y redacción de claves.
- Fixtures de SerpAPI, Places y la interpretación; transporte falso para tests.
- Normalizador de fechas, montos y ocupación; intérprete Gemini; detector de ambigüedad y de menciones fuera de alcance.
- Lector CLI que pregunta solo lo faltante.
- Places Text Search para destino y ancla; buscador de hoteles en COP con deduplicación y paginación condicional.

## 3. Demo al cerrar

```text
> quiero ir a Santa Marta, hotel frente al mar, 2 adultos, 3 días y 2 noches, 2 millones
```

Debe resolver destino y ancla, buscar hoteles reales en COP y mostrarlos con precio, link y advertencias, sin pedir datos ya presentes.

## 4. Criterios de aceptación

- [ ] `I2-008`: ningún módulo fuera de `src/services/` hace HTTP directo y la suite sigue estable.
- [ ] `I2-021`: los hoteles quedan persistidos con IDs reales de PostgreSQL.
- [ ] Una frase incompleta dispara solo las preguntas de los campos faltantes.
- [ ] Ningún proveedor se consulta antes de completar la solicitud.
- [ ] Los hoteles sin precio o sin coordenadas se descartan; sin link se conserva con advertencia.

## 5. Fuera de alcance (V1)

- Cálculo de distancias y filtro de cercanía.
- Comparación con presupuesto y ranking final.
- Reseñas evaluadas por IA e itinerario.

## 6. Riesgos

| Riesgo | Mitigación |
|---|---|
| SerpAPI no respeta COP | Se muestra la moneda real y `comparable=False` |
| Ancla ambigua o de otro tipo | Validación de tipo y distancia; repregunta sin buscar hoteles |
| Cuota de SerpAPI | Segunda página solo si faltan hoteles; sin caché en V0 |
| Almacenar resultados de SerpAPI | Riesgo asumido y documentado [POR VERIFICAR] |

## 7. Trazabilidad

| RF | Tasks |
|---|---|
| RF-1 | `I2-010`–`I2-012`, `I2-016`–`I2-018` |
| RF-2 | `I2-012`–`I2-014` |
| RF-3 | `I2-009` |
| RF-4 | `I2-016`, `I2-018` |
| RF-5 | `I2-005`, `I2-019`–`I2-021` |
| RF-7 | `I2-019` |
| RF-12 | `I2-001`–`I2-008` |

## 8. Definición de terminado

El incremento termina cuando `I2-021` está marcado: frase completa sin preguntas extra, frase incompleta solo con faltantes, y hoteles reales en COP persistidos.

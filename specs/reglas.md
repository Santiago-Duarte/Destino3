# Reglas de Negocio — Destino3

## Destinos

1. Un destino se identifica por ciudad y país.
2. La comparación de ciudad y país es normalizada.
3. No deben existir destinos duplicados únicamente por diferencias de mayúsculas/minúsculas o espacios.
4. Un destino puede tener múltiples hospedajes.
5. Un destino puede aparecer en múltiples búsquedas.

---

## Hospedajes

1. Todo hospedaje debe pertenecer a un destino.
2. `destino_id` es obligatorio.
3. El tipo de hospedaje permitido es:
   - hotel
   - airbnb
   - otro
4. Un hospedaje puede aparecer en múltiples búsquedas.
5. Un hospedaje no debe contener directamente su evaluación ni sus recomendaciones.

---

## Búsquedas

1. Una búsqueda pertenece a un usuario.
2. Una búsqueda pertenece a un destino.
3. El presupuesto debe ser mayor que cero.
4. La fecha final no puede ser anterior a la fecha inicial.
5. Una búsqueda representa los criterios utilizados en una consulta.
6. Los resultados de una búsqueda no deben almacenarse directamente dentro de la entidad búsqueda.

---

## Evaluaciones IA

1. Una evaluación contiene:
   - resumen ejecutivo;
   - puntos fuertes;
   - puntos débiles;
   - score de calidad-precio.
2. El score debe estar entre 1 y 10.
3. `id_temporal` no pertenece al dominio persistente.
4. `id_temporal` nunca debe persistirse.
5. La evaluación se obtiene mediante el servicio de IA.
6. La relación exacta entre evaluación y búsqueda permanece pendiente de decisión.

---

## Recomendaciones

1. Una recomendación pertenece a una búsqueda.
2. Una recomendación apunta a un hospedaje.
3. La posición válida está entre 1 y 3.
4. Una búsqueda puede tener como máximo 3 posiciones.
5. Un hospedaje no puede repetirse dentro de la misma búsqueda.
6. Cada posición de una búsqueda solo puede estar ocupada una vez.

---

## Identificadores

`id_temporal`:

- se genera durante el procesamiento;
- sirve para relacionar candidatos con la respuesta de Gemini;
- no corresponde a un ID de PostgreSQL;
- no se persiste;
- debe transformarse al `hospedaje_id` real antes de persistir.

---

## Evaluación ≠ recomendación

La evaluación responde:

> ¿Qué valoración recibe este hospedaje según los criterios utilizados?

La recomendación responde:

> ¿Qué posición ocupa este hospedaje dentro de esta búsqueda?

Son responsabilidades diferentes.

---

## Persistencia

La persistencia debe trabajar con estructuras propias de Destino3 y no depender directamente de modelos específicos del proveedor externo.

---

## Servicios externos

Las llamadas a SerpAPI y Gemini deben estar encapsuladas.

El resto del sistema no debe ejecutar directamente llamadas a estos proveedores.

---

## Error explícito

Los errores relevantes no deben convertirse silenciosamente en `None`.

Una operación fallida debe permitir que la capa superior conozca que ocurrió un error.

---

## Testing

El proyecto utiliza `unittest`.

Los servicios externos deben utilizar mocks en pruebas unitarias.

La base de datos de testing se utiliza para probar persistencia real cuando corresponda.
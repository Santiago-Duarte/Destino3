# Próximas Tareas — Destino3

## Objetivo inmediato

Completar la integración de la Fase 3.4 sin avanzar todavía hacia CLI, API o frontend.

---

## Orden de trabajo

### 1. Separar modelos de evaluación

Crear un modelo propio de evaluación que no dependa directamente del DTO utilizado para representar la respuesta de Gemini.

---

### 2. Resolver la dependencia Repository → Service

Eliminar la dependencia de `evaluaciones_repository.py` respecto de `ai_evaluator.py`.

---

### 3. Resolver la decisión de evaluación contextual

Determinar si una evaluación pertenece:

- únicamente a un hospedaje;
- o a un hospedaje dentro del contexto de una búsqueda.

Esta decisión debe resolverse antes de cerrar Fase 3.4.

---

### 4. Completar repositories

Completar los métodos que sean necesarios para el flujo actual.

Crear los repositories faltantes cuando corresponda al roadmap.

---

### 5. Implementar mapeo `id_temporal → hospedaje_id`

Resolver el ID real de PostgreSQL antes de persistir evaluaciones y recomendaciones.

`id_temporal` nunca debe llegar a la base de datos.

---

### 6. Crear orquestación

Implementar el flujo completo de la búsqueda mediante una capa de orquestación.

---

### 7. Separar responsabilidades de `api_searcher`

Eliminar responsabilidades que no correspondan a la búsqueda externa, especialmente la escritura de archivos de prueba.

---

### 8. Mejorar manejo de errores

Sustituir el manejo basado exclusivamente en `print()` y valores silenciosos.

---

### 9. Verificar pruebas

Mantener la estrategia de testing basada en `unittest`.

Agregar mocks de Gemini donde corresponda y pruebas de integración contra la base de datos de testing.

---

### 10. Completar Fase 3.4

El flujo deberá ser ejecutable de extremo a extremo antes de comenzar la Fase 4.
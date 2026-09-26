# Spec 003 — Integración de APIs Externas (SerpAPI + Gemini) y Persistencia

## Contexto y objetivo

El sistema necesita obtener opciones de hospedaje desde una fuente externa, analizarlas mediante IA generativa y
persistir tanto los hospedajes obtenidos como sus evaluaciones para que puedan ser utilizados posteriormente por otras
partes de Destino3. Esta fase establece la integración entre las fuentes externas, el dominio de la aplicación y la base
de datos, de forma que la información pueda ser procesada y reutilizada sin depender de una consulta manual a los
proveedores externos.

## Usuarios / actores

- **Sistema:** inicia y ejecuta el flujo de búsqueda y evaluación.
- **Desarrollador:** define los criterios y parámetros operativos de la integración.
- **Ejecutor de pruebas:** verifica el comportamiento de la integración mediante servicios externos simulados y una base
  de datos de pruebas.

## Historias de usuario
- **H1:** Como sistema, quiero buscar hospedajes aplicando los criterios definidos para la búsqueda para obtener
  opciones relevantes.
- **H2:** Como sistema, quiero evaluar en lote los hospedajes candidatos mediante IA para obtener una valoración
  estructurada de cada opción.
- **H3:** Como sistema, quiero persistir primero los hospedajes y obtener sus identificadores persistentes para poder
  relacionar posteriormente cada evaluación con el hospedaje correspondiente.
- **H4:** Como desarrollador, quiero poder ajustar los límites operativos de la integración sin modificar la lógica
  funcional para adaptarme a las restricciones de los proveedores externos.
- **H5:** Como desarrollador, quiero ejecutar pruebas de integración sin depender de los servicios externos ni consumir
  sus cuotas para verificar el comportamiento del sistema de forma controlada.

## Requisitos funcionales (EARS)

- **RF-1:** CUANDO se solicita una búsqueda con parámetros válidos, EL SISTEMA consulta el proveedor de hospedajes
  aplicando los criterios definidos para la búsqueda y obtiene los resultados disponibles.

- **RF-2:** SI el proveedor informa que se ha alcanzado un límite temporal de solicitudes, ENTONCES EL SISTEMA intenta
  recuperar la operación mediante la política de reintentos configurada y, si los reintentos se agotan, detiene la
  obtención de nuevos resultados y conserva los resultados obtenidos hasta ese momento.

- **RF-3:** SI la búsqueda supera el máximo de páginas o resultados permitido, ENTONCES EL SISTEMA detiene la obtención
  de nuevos resultados y conserva los resultados acumulados.

- **RF-4:** CUANDO la búsqueda produce hospedajes, EL SISTEMA persiste los hospedajes y obtiene para cada uno un
  identificador persistente que permita establecer posteriormente sus relaciones.

- **RF-5:** CUANDO existen hospedajes persistidos y candidatos para evaluación, EL SISTEMA envía los candidatos en un
  único lote a la IA junto con los criterios necesarios para realizar la evaluación.

- **RF-6:** CUANDO la IA responde, EL SISTEMA valida que la respuesta tenga la estructura esperada y que cada evaluación
  contenga, como mínimo, identificador temporal, resumen ejecutivo, puntos fuertes, puntos débiles y puntuación de
  calidad-precio entre 1 y 10.

- **RF-7:** SI la IA no responde correctamente debido a un error temporal, tiempo agotado o respuesta que no cumple la
  estructura esperada, ENTONCES EL SISTEMA aplica la política de reintentos configurada y, si estos se agotan, registra
  el fallo sin crear evaluaciones parciales de un lote incompleto.

- **RF-8:** CUANDO una evaluación de IA es válida, EL SISTEMA persiste la evaluación asociándola al hospedaje
  correspondiente mediante su identificador persistente.

- **RF-9:** MIENTRAS el sistema realiza solicitudes a proveedores externos, EL SISTEMA respeta los límites operativos
  configurados y evita realizar solicitudes indefinidamente cuando estos límites o los reintentos permitidos han sido
  alcanzados.

- **RF-10:** EL SISTEMA permite modificar los parámetros operativos de la integración, como tiempos de espera, cantidad
  de reintentos, límites de resultados y paginación, sin modificar la lógica funcional de la aplicación.

- **RF-11:** CUANDO se ejecutan las pruebas de integración, EL SISTEMA utiliza respuestas controladas de los proveedores
  externos y una base de datos de pruebas para verificar el flujo completo sin consumir cuotas reales de los
  proveedores.

## Requisitos no funcionales

- **Rendimiento:** el flujo completo de búsqueda y evaluación debe poder procesar hasta 20 hospedajes en menos de 30
  segundos en condiciones normales de red, medido en el percentil 95.

- **Resiliencia:** las llamadas a proveedores externos deben disponer de una política limitada de reintentos con espera
  progresiva y de límites máximos de solicitudes y resultados.

- **Seguridad:** las credenciales de proveedores externos no deben quedar expuestas en registros ni almacenadas como
  parte de los datos funcionales de la aplicación.

- **Observabilidad:** los errores y eventos relevantes de la integración deben quedar registrados de forma que pueda
  identificarse el proveedor involucrado y el resultado de la operación.

- **Mantenibilidad:** la estructura de las respuestas de IA debe mantenerse explícita y validable para detectar cambios
  o respuestas incompatibles.

## Casos límite

- **Sin resultados:** si el proveedor no devuelve hospedajes, el flujo termina correctamente con una lista vacía y no
  intenta evaluar ni persistir evaluaciones inexistentes.

- **Hospedaje sin reseñas:** si un hospedaje no tiene reseñas, la IA lo evalúa utilizando la información disponible.

- **Respuesta IA inválida:** si la respuesta de IA no cumple la estructura esperada, el sistema realiza los reintentos
  configurados. Si todos fallan, el lote de evaluación se considera fallido y no se almacenan evaluaciones parciales.

- **Límite de tasa:** si el proveedor rechaza temporalmente una solicitud por exceso de peticiones, el sistema aplica la
  política de recuperación configurada. Si no logra recuperarse, conserva únicamente los resultados obtenidos hasta ese
  momento.

- **Tiempo agotado:** si una solicitud supera el tiempo máximo permitido, el fallo cuenta dentro de la política de
  reintentos.

- **Límite de paginación:** si existen más páginas que las permitidas, el sistema deja de solicitar nuevas páginas y
  conserva los resultados acumulados.

- **Base de datos de pruebas no disponible:** las pruebas de integración deben indicar explícitamente el fallo de
  infraestructura y no sustituir la base de datos por una simulación.

- **Datos de prueba inválidos:** si una respuesta utilizada por las pruebas no cumple la estructura esperada, la prueba
  debe fallar indicando el problema de validación.

- **Concurrencia:** cuando existen varias búsquedas simultáneas, el sistema debe respetar los límites globales
  establecidos para las solicitudes a los proveedores.

## Fuera de alcance

- Interfaces de usuario: CLI, API REST y Frontend.
- Autenticación y autorización de usuarios.
- Caché de resultados.
- Circuit breaker.
- Exportación de métricas a sistemas externos.
- Persistencia de metadatos técnicos de las llamadas a IA, como tokens, latencia, versión del modelo o información del
  proveedor.
- Externalización del prompt: en esta fase el prompt permanece en la implementación actual.
- Externalización del nombre o versión del modelo de IA: en esta fase permanece definido por la implementación actual.
- Algoritmo definitivo para seleccionar u ordenar el Top 3.
- Persistencia de las recomendaciones finales derivadas del Top 3.
- Migraciones del esquema de base de datos.

## Criterios de finalización

- Todos los requisitos funcionales tienen pruebas automatizadas cubiertas y en verde mediante `unittest`.

- Existe una prueba de integración que verifica el flujo:
  búsqueda simulada → persistencia de hospedajes → evaluación simulada en lote → persistencia de evaluaciones.

- Las pruebas cubren como mínimo:
    - hospedaje completo;
    - hospedaje sin reseñas;
    - respuesta de IA válida;
    - respuesta de IA inválida;
    - respuesta de proveedor con límite de tasa;
    - agotamiento de reintentos;
    - ausencia de resultados;
    - límite de paginación.

- Las pruebas de integración utilizan una base de datos PostgreSQL destinada a pruebas y dobles de prueba para los
  proveedores externos.

- El flujo puede ejecutarse manualmente contra los proveedores reales para verificar la integración completa, cuando
  existan credenciales y condiciones para hacerlo.

## Estado actual

Esta sección describe únicamente el estado actual de la implementación y no constituye por sí misma un requisito futuro.

- **Prompt:** permanece incrustado en la implementación actual.
- **Evaluación:** actualmente se realiza en batch mediante una única llamada a la IA con los candidatos seleccionados
  por la lógica existente.
- **Respuesta IA:** actualmente utiliza los campos `id_temporal`, `resumen_ejecutivo`, `puntos_fuertes`,
  `puntos_debiles` y `score_calidad_precio`.
- **Modelo IA:** actualmente está definido directamente en la implementación.
- **Persistencia:** actualmente los hospedajes se guardan antes de la evaluación de IA, obteniendo identificadores
  persistentes que posteriormente permiten relacionar las evaluaciones.
- **Rate limiting:** actualmente no está implementado de forma completa.
- **Reintentos:** actualmente no existe una política completa de reintentos para la IA.
- **Configuración:** actualmente solo parte de la configuración se obtiene desde variables de entorno; otros parámetros
  permanecen definidos en la implementación.
- **Top 3:** actualmente la respuesta de Gemini participa directamente en la determinación de los tres elementos
  devueltos. La responsabilidad futura de determinar las recomendaciones finales corresponde a Destino3 y no a Gemini.

## Dudas abiertas

- Ninguna de las decisiones de alcance definidas para esta versión queda pendiente.
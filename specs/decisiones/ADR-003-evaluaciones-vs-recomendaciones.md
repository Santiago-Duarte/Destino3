## Estado

ACEPTADA

## Contexto

Destino3 necesita distinguir entre el análisis que realiza la IA sobre un hospedaje y la posición de ese hospedaje dentro de una búsqueda.

## Decisión

Se tratarán como conceptos distintos.

### Evaluación

Representa la valoración cualitativa y score del hospedaje.

### Recomendación

Representa la relación entre una búsqueda y un hospedaje, incluyendo su posición.

## Consecuencias

La evaluación y la recomendación tienen responsabilidades diferentes y se representan mediante estructuras distintas.

Esto evita mezclar:

```text
“qué tan bueno es”

con 

“qué posición ocupa”
---
status: accepted
---

# La Consulta cerrada no se edita: se enmienda

Una Consulta cerrada queda firmada por el veterinario que la atendió y es un documento clínico con valor legal y probatorio. Decidimos que **no admite modificación**: toda corrección o añadido posterior se registra como una Enmienda con su propia fecha y su propio autor, encadenada a la Consulta original.

La alternativa obvia — permitir editar como en cualquier CRUD — hace imposible responder a la única pregunta que importa cuando hay una reclamación o una revisión profesional: *qué decía la ficha en el momento en que se tomó la decisión clínica*. Un historial de cambios genérico no basta, porque la Enmienda es información clínica que el veterinario debe poder leer, no metadatos de auditoría.

## Consecuencias

- La Consulta tiene dos fases: **abierta** (editable libremente por su autor durante la atención) y **cerrada** (inmutable). El cierre es un acto explícito, no un guardado.
- Las vistas deben mostrar la Consulta y sus Enmiendas como una unidad legible en orden cronológico.
- Los formularios de Django no pueden exponer una Consulta cerrada en modo edición. Esa restricción va en el modelo, no en la plantilla.

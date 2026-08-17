# 06 — RUT validado y teléfono normalizado

**What to build:** recepción escribe el RUT como se lo dicten y el sistema lo guarda de una sola forma, avisando si está mal o si ya existe. El teléfono queda en un formato con el que después se pueda contactar sin ambigüedad.

**Blocked by:** 05

**Status:** ready-for-agent

- [ ] RUT **opcional**: se puede registrar un Tutor extranjero o que no quiere darlo
- [ ] Validación del dígito verificador al guardar, con mensaje claro cuando falla
- [ ] Almacenamiento normalizado sin puntos ni guion, y presentación con formato chileno
- [ ] RUT único dentro de la Clínica cuando está presente; aviso si ya existe, con enlace a la ficha existente
- [ ] Teléfono normalizado a E.164 aceptando las formas en que se escribe en Chile (con y sin `+56`, con y sin `9`, con espacios)
- [ ] Teléfono **no único**: se permite compartido entre Tutores de una familia, con aviso al guardar
- [ ] Tests de dígito verificador correcto, incorrecto, con `K`, y de ausencia de RUT
- [ ] Tests de normalización de teléfono para cada forma de escritura habitual

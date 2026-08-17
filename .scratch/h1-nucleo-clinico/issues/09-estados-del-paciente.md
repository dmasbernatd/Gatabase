# 09 — Estados del Paciente

**What to build:** cuando un Paciente muere o deja de venir, el sistema lo refleja sin borrar nada. Evita el peor error posible de cara al Tutor: tratar como activo a un animal que ya no está.

**Blocked by:** 07

**Status:** ready-for-agent

- [ ] Estados `activo`, `inactivo` y `fallecido`, y fecha en el caso de fallecido
- [ ] Un Paciente fallecido conserva **toda** su información en solo lectura; nunca se borra
- [ ] La ficha de un Paciente fallecido lo indica de forma inequívoca en la propia página
- [ ] Los listados y las búsquedas por defecto muestran solo activos, con filtro para ver el resto
- [ ] Marcar como fallecido bloquea cualquier alta futura de Cita (la comprobación se ejercita en H3; aquí queda la regla en el modelo)
- [ ] `inactivo` es un estado distinto y reversible, para el animal que dejó de venir sin que se sepa qué pasó
- [ ] El cambio de estado queda en el Registro de acceso

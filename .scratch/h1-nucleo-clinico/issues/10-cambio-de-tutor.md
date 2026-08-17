# 10 — Cambio de Tutor de un Paciente

**What to build:** un animal cambia de dueño y el sistema lo refleja sin perder el rastro de quién lo trajo antes. La información del animal sigue al animal.

**Blocked by:** 07

**Status:** ready-for-agent

- [ ] Cerrar el vínculo de un Tutor con un Paciente indicando fecha, en lugar de eliminarlo
- [ ] Vincular un Tutor nuevo y marcarlo como responsable en el mismo flujo
- [ ] La ficha del Paciente muestra los Tutores actuales y los anteriores con sus fechas
- [ ] La ficha del Tutor anterior sigue mostrando que ese Paciente fue suyo, y hasta cuándo
- [ ] Todo lo registrado sobre el Paciente permanece asociado al Paciente, no al Tutor (ADR-0001)
- [ ] Un Paciente no puede quedarse sin ningún Tutor responsable, salvo que esté `inactivo` o `fallecido`
- [ ] La operación queda en el Registro de acceso

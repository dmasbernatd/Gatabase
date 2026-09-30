# 09 — Resumen de la Consulta para el Tutor

**What to build:** recepción imprime o descarga un resumen de la Consulta para que el Tutor se lleve las indicaciones por escrito.

**Blocked by:** 03, 05

**Status:** ready-for-agent

- [ ] Página de resumen imprimible (CSS de impresión; sin generar PDF en el servidor salvo que se decida lo contrario): Clínica y Sede, Paciente, fecha, veterinario, motivo, diagnóstico, tratamiento indicado, plan, folio de la receta del SAG y constantes
- [ ] No incluye subjetivo, objetivo ni evaluación: son notas clínicas, no indicaciones (decisión a confirmar y anotar)
- [ ] Si la Consulta tiene Enmiendas que tocan lo que el resumen enseña, el resumen las incluye con su fecha
- [ ] Solo de Consultas cerradas: un resumen de algo que todavía puede cambiar no vale como indicación escrita
- [ ] Recepción y veterinario pueden sacarlo
- [ ] Sacar el resumen queda en el Registro de acceso como lectura
- [ ] Aislamiento por HTTP: el resumen de otra Clínica da 404

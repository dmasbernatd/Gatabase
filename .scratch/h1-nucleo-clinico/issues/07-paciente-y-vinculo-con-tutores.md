# 07 — Paciente, catálogos de especie y raza, y vínculo con Tutores

**What to build:** recepción registra el animal y lo vincula a quien responde por él. A partir de aquí el sistema sabe de qué Paciente habla un Tutor cuando llama.

**Blocked by:** 04, 05

**Status:** ready-for-agent

- [ ] Paciente con nombre, especie, raza, sexo, fecha de nacimiento, color y observaciones
- [ ] Catálogo de **especies cerrado**: de la especie dependen protocolos y formularios, así que no admite texto libre
- [ ] Catálogo de **razas por especie** con autocompletado, `mestizo` como entrada de primera clase, y opción `otra` con texto libre
- [ ] Vínculo Tutor–Paciente de muchos a muchos: un Paciente puede tener varios Tutores y un Tutor varios Pacientes
- [ ] Un Tutor del Paciente marcado como **responsable**; solo uno a la vez
- [ ] Desde la ficha del Tutor se ven sus Pacientes, y desde la del Paciente sus Tutores
- [ ] La ficha de Paciente y el acceso a ella quedan en el Registro de acceso
- [ ] Aislamiento por Clínica verificado por HTTP para Paciente y para el vínculo
- [ ] Los datos clínicos del Paciente son independientes de los datos personales del Tutor (ADR-0004)

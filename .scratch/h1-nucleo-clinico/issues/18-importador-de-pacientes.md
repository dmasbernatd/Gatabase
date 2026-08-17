# 18 — Importador CSV de Pacientes con vínculo a Tutores

**What to build:** el admin sube su planilla de animales y el sistema los vincula a los Tutores ya importados. Es la parte difícil de la migración: la planilla real identifica al dueño por un nombre escrito a mano, no por un identificador.

**Blocked by:** 08, 17

**Status:** ready-for-agent

- [ ] Subida de un CSV de Pacientes con nombre, especie, raza, sexo, fecha de nacimiento, color, microchip e identificación del Tutor
- [ ] Resolución del Tutor por RUT, o por teléfono, o por nombre; cuando la coincidencia es ambigua, la fila se rechaza con un mensaje que dice entre qué Tutores dudó
- [ ] Especie no reconocida: la fila se rechaza indicando las especies válidas, porque el catálogo es cerrado por diseño
- [ ] Raza no reconocida: se importa como `otra` con el texto original conservado, en lugar de rechazar la fila
- [ ] Microchip repetido dentro de la Clínica: la fila se rechaza indicando qué Paciente ya lo tiene
- [ ] Fecha de nacimiento en varios formatos habituales de planilla, y ausente sin que rompa
- [ ] Vista previa antes de confirmar e informe de errores fila a fila, igual que en el ticket 17
- [ ] Reimportar el mismo archivo no duplica Pacientes ni vínculos
- [ ] La importación queda en el Registro de acceso
- [ ] **El histórico clínico no se importa** y el sistema no ofrece hacerlo: migrar historias en texto libre es un pozo sin fondo, y la digitalización empieza en la primera Consulta nueva
- [ ] Tests de resolución de Tutor por cada vía, de ambigüedad, de especie inválida, de raza desconocida y de reimportación

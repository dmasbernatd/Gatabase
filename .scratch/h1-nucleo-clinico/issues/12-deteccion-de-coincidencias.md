# 12 — Detección de coincidencias al crear

**What to build:** cuando recepción va a crear un Tutor o un Paciente que probablemente ya existe, el sistema se lo muestra antes de guardar. Es la prevención barata que evita la mayoría de las fichas duplicadas, dado que la fusión se posterga deliberadamente.

**Blocked by:** 11

**Status:** ready-for-agent

- [ ] Al escribir el teléfono de un Tutor nuevo, el sistema muestra los Tutores existentes con ese teléfono
- [ ] Al escribir el RUT de un Tutor nuevo, el sistema avisa si ya existe y enlaza a la ficha
- [ ] Al escribir el microchip de un Paciente nuevo, el sistema avisa si ya existe en la Clínica y enlaza a la ficha
- [ ] Al crear un Paciente para un Tutor que ya tiene Pacientes, el sistema muestra los que ya tiene con nombre y especie
- [ ] La coincidencia es un **aviso con enlace**, nunca un bloqueo: dos animales de la misma familia pueden llamarse parecido
- [ ] La detección funciona con HTMX mientras se escribe, sin necesidad de guardar
- [ ] Tests de los cuatro casos de coincidencia, y de que el aviso no impide guardar cuando el Usuario insiste

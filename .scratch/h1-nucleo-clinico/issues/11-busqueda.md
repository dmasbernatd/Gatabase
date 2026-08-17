# 11 — Búsqueda de Tutores y Pacientes

**What to build:** recepción está al teléfono con un Tutor y encuentra al Paciente en segundos, escribiendo lo primero que tenga a mano: un nombre, un teléfono o un número de chip. Es la funcionalidad que hace que el sistema gane al archivador.

**Blocked by:** 06, 07, 08

**Status:** ready-for-agent

- [ ] Una única caja de búsqueda que acepta nombre de Paciente, nombre de Tutor, teléfono, RUT o microchip, sin que el Usuario tenga que elegir el campo
- [ ] Búsqueda tolerante a tildes y a mayúsculas, y a teléfonos escritos de cualquiera de las formas habituales
- [ ] Resultados que muestran Paciente, especie, Tutor responsable y teléfono, para poder confirmar por voz que es el correcto
- [ ] Respuesta rápida con el volumen de datos mock de una clínica real
- [ ] Resultados incrementales con HTMX mientras se escribe
- [ ] Los Pacientes fallecidos e inactivos aparecen marcados, no ocultos, porque a veces se busca precisamente a ellos
- [ ] Ningún resultado de otra Clínica, comprobado por test
- [ ] La búsqueda no registra un acceso por cada resultado listado; el Registro de acceso se escribe al abrir una ficha

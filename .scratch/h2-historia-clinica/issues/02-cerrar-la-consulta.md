# 02 — Cerrar la Consulta: firmada e inmutable

**What to build:** el veterinario cierra la Consulta con un acto explícito, distinto de guardar, y desde ese momento nadie puede cambiarla: ni desde la pantalla, ni con una petición construida a mano, ni desde el shell. Implementa ADR-0002.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] La Consulta tiene fase `abierta` y `cerrada`; se registra el momento del cierre y quién cerró
- [ ] «Cerrar Consulta» es un botón aparte del de guardar, con confirmación; solo el autor la cierra
- [ ] La inmutabilidad vive **en el modelo**: guardar una Consulta cerrada lanza error aunque se llame a `save()` sin pasar por ningún formulario; y también un `QuerySet.update()` sobre una cerrada (decidir aquí si basta el modelo o hace falta un disparador como el de `audit`, y dejarlo escrito)
- [ ] La vista de edición de una Consulta cerrada no ofrece formulario, y un `POST` hecho a mano contra ella se rechaza y no cambia nada
- [ ] **Suite obligatoria — inmutabilidad**: cerrar por HTTP y comprobar que todo intento posterior de editarla se rechaza, incluida la petición construida a mano
- [ ] Una Consulta cerrada no se reabre
- [ ] La página de la Consulta dice de un vistazo si está abierta o cerrada, y cuándo se cerró y quién la firmó
- [ ] El cierre queda en el Registro de acceso como modificación
- [ ] Aislamiento por HTTP: cerrar la Consulta de otra Clínica da 404

Pregunta que se decide aquí y se anota en Comments: qué pasa con una Consulta que se queda abierta días porque nadie la cerró. No hace falta cierre automático en este ticket, pero la ficha del Paciente o el panel del veterinario deben dejar ver que existe.

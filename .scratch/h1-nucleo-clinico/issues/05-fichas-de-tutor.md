# 05 — Fichas de Tutor

**What to build:** recepción registra un Tutor con sus datos de contacto, lo encuentra en un listado, abre su ficha y la corrige. Es el primer punto donde la clínica deja de depender de la planilla para saber quién es su cliente.

**Blocked by:** 03, 04

**Status:** ready-for-agent

- [ ] Tutor con nombre, apellidos, teléfono, correo y dirección
- [ ] Crear, editar, listar y ver la ficha de un Tutor, con HTMX para los flujos que lo merezcan
- [ ] Listado paginado y ordenable, usable con cientos de Tutores
- [ ] Los datos personales del Tutor viven en su propio modelo, separados de los datos clínicos del Paciente, para permitir anonimizar después sin tocar la historia
- [ ] Abrir o editar una ficha queda en el Registro de acceso
- [ ] Un Usuario de otra Clínica no ve ni encuentra estos Tutores
- [ ] Los textos de la interfaz pasan por `gettext`

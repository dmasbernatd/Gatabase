# 16 — Datos mock por comando de gestión

**What to build:** un comando que llena el sistema con datos verosímiles de una clínica chilena de una sede, para poder desarrollar contra volumen real, medir si la búsqueda es rápida y demostrarle el sistema a la clínica piloto sin usar datos de clientes reales.

**Blocked by:** 08

**Status:** ready-for-agent

- [ ] Comando de gestión que genera dos Clínicas con Sedes, Usuarios de los tres roles, Tutores y Pacientes
- [ ] **Dos** Clínicas y no una: es lo que permite comprobar el aislamiento a mano, además de por test
- [ ] Volumen realista de una clínica de una sede, suficiente para que un listado y una búsqueda lentos se noten
- [ ] Nombres, teléfonos y RUT verosímiles para Chile, con dígito verificador válido
- [ ] Mezcla realista de especies con predominio de caninos y felinos, razas del catálogo con mayoría de `mestizo`, y algunos exóticos
- [ ] Casos límite incluidos a propósito: Paciente sin chip, Paciente fallecido, Tutor sin RUT, Tutor extranjero, dos Tutores con el mismo teléfono, Paciente con dos Tutores
- [ ] El comando es idempotente o limpia lo anterior, para poder ejecutarlo repetidamente
- [ ] El comando se niega a ejecutarse contra una base de producción

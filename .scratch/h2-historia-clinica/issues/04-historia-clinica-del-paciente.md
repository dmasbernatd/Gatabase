# 04 — La Historia clínica del Paciente

**What to build:** desde la ficha del Paciente, el veterinario ve todas sus Consultas ordenadas por fecha, para ponerse al día antes de entrar al box. La Historia es del Paciente, no del Tutor: sigue al animal cuando cambia de manos.

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] Página de Historia clínica del Paciente: una línea por Consulta con fecha, Sede, veterinario, motivo, diagnóstico, estado (abierta/cerrada) y cuántas Enmiendas tiene, de la más reciente a la más antigua
- [ ] Cada línea lleva a la Consulta con su hilo de Enmiendas
- [ ] La ficha del Paciente enlaza a su Historia y deja ver si hay alguna Consulta abierta
- [ ] Tras un cambio de Tutor (ticket 10 de H1), la Historia es la misma y está entera; test por HTTP
- [ ] Leer la Historia clínica queda en el Registro de acceso con Usuario y momento — **suite obligatoria**, primera mitad
- [ ] El admin puede responder «quién ha visto la Historia clínica de este Paciente» desde la página del Registro; si hoy el filtro por objeto no lo permite con los tipos nuevos, se arregla aquí
- [ ] Recepción puede leer la Historia (necesita saber a qué vino el animal la última vez); el rol se decide aquí y se anota
- [ ] La página no hace más consultas con cincuenta Consultas que con una (test que cuenta consultas, como `test_busqueda.py`)
- [ ] Aislamiento por HTTP: la Historia del Paciente de otra Clínica da 404; no hay deduplicación por microchip entre Clínicas (ADR-0001)

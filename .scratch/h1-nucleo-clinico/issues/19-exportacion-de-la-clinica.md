# 19 — Exportación completa de la Clínica

**What to build:** el admin se descarga todos los datos de su Clínica en un formato abierto, cuando quiera y sin pedir permiso a nadie. No es una funcionalidad técnica: es lo que hace que una clínica se atreva a poner su información en un sistema ajeno.

**Blocked by:** 04, 07

**Status:** ready-for-agent

- [ ] El admin de la Clínica lanza la exportación y obtiene un archivo con Tutores, Pacientes, vínculos, catálogos y configuración de Sedes
- [ ] Formato abierto y legible por una planilla, no un volcado propio del sistema
- [ ] La exportación contiene **solo** datos de su Clínica, comprobado por test con dos Clínicas pobladas
- [ ] Solo el rol admin puede exportar; recepción y veterinario no
- [ ] La exportación queda en el Registro de acceso, porque es el acceso masivo a datos personales que más importa poder demostrar
- [ ] La descarga no queda accesible por una dirección adivinable ni permanente
- [ ] Funciona con el volumen de datos mock sin agotar la memoria del proceso

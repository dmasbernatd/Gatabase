# 02 — Clínica, Sede y login de Usuario con roles

**What to build:** un Usuario entra al sistema con su correo y su contraseña y ve a qué Clínica y a qué Sede pertenece. El admin de la Clínica puede crear Usuarios, asignarles rol y asignarles Sedes.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Modelos de Clínica y Sede; una Clínica tiene una o varias Sedes
- [ ] Usuario con rol `veterinario`, `recepción` o `admin`, y pertenencia a una o varias Sedes de su Clínica
- [ ] Login y logout con `django-allauth`, con correo y contraseña
- [ ] Tras entrar, el Usuario ve el nombre de su Clínica y su Sede actual, y puede cambiar de Sede si pertenece a varias
- [ ] El admin de la Clínica crea Usuarios, les asigna rol y Sedes, y los desactiva
- [ ] Un Usuario sin sesión que pide una página interna acaba en el login
- [ ] Un Usuario con rol de recepción no accede a la administración de Usuarios
- [ ] Comando de gestión para dar de alta una Clínica con su primera Sede y su primer admin

# 04 — Registro de acceso

**What to build:** cada vez que un Usuario ve o modifica datos personales, queda constancia de quién, qué y cuándo, y el admin de la Clínica puede consultarlo. Implementa ADR-0004.

Va antes de Paciente a propósito: el mecanismo de registro debe existir cuando se escriban las vistas siguientes, para no tener que volver a pasar por todas.

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] Modelo de Registro de acceso con Usuario, Clínica, tipo de objeto, identificador, acción y momento
- [ ] Registro escrito **desde las vistas**, porque una lectura no dispara señales de modelo
- [ ] Mecanismo reutilizable (mixin o decorador de vista) que las vistas posteriores apliquen sin duplicar lógica
- [ ] Abrir la ficha de un Tutor queda registrado con Usuario y momento
- [ ] La tabla no admite `UPDATE` ni `DELETE`: restringido a nivel de permisos de base de datos, no solo de aplicación
- [ ] El admin de la Clínica consulta el registro filtrando por Usuario, por objeto y por rango de fechas
- [ ] Test que comprueba que un intento de modificar o borrar una anotación falla
- [ ] El registro está aislado por Clínica como cualquier otro dato

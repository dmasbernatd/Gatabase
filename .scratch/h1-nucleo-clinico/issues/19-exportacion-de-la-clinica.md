# 19 — Exportación completa de la Clínica

**What to build:** el admin se descarga todos los datos de su Clínica en un formato abierto, cuando quiera y sin pedir permiso a nadie. No es una funcionalidad técnica: es lo que hace que una clínica se atreva a poner su información en un sistema ajeno.

**Blocked by:** 04, 07

**Status:** done

- [x] El admin de la Clínica lanza la exportación y obtiene un archivo con Tutores, Pacientes, vínculos, catálogos y configuración de Sedes
- [x] Formato abierto y legible por una planilla, no un volcado propio del sistema
- [x] La exportación contiene **solo** datos de su Clínica, comprobado por test con dos Clínicas pobladas
- [x] Solo el rol admin puede exportar; recepción y veterinario no
- [x] La exportación queda en el Registro de acceso, porque es el acceso masivo a datos personales que más importa poder demostrar
- [x] La descarga no queda accesible por una dirección adivinable ni permanente
- [x] Funciona con el volumen de datos mock sin agotar la memoria del proceso
- [x] Una Clínica que se va **se exporta y se cierra, no se borra**: su Registro de acceso no admite `DELETE` y el borrado en cascada falla (ADR-0004). Lo que hay que definir aquí es qué significa cerrarla — desactivar a sus Usuarios, dejarla sin acceso — y que el sistema lo ofrezca, en vez de que el admin descubra el `IntegrityError`.

## Comments

**Hecho el 26 de agosto de 2026.** La exportación vive en una app propia,
`apps/exports/`, y no dentro de `apps/imports/`: son dos gestos con dos páginas,
dos formatos y dos permisos, y lo único que comparten —qué planilla entiende un
Excel chileno— se quedó en `apps/imports/planilla.py`, que ganó un escritor que
suelta las filas de a una.

**Qué se decidió que significa cerrar una Clínica** (`apps/exports/cierre.py`):
consta cuándo se cerró en `Clinica.cerrada` y se desactivan todos sus Usuarios,
incluido el admin que lo pide. Los datos se quedan donde están —el Registro de
acceso incluido— y no entra nadie más: `allauth` deja fuera al Usuario inactivo
en el login, y a quien tuviera sesión abierta lo desconecta en su siguiente
petición. Es terminal a propósito: no hay pantalla que reabra una Clínica, y por
eso la vista pide escribir su nombre antes de hacerlo.

**La descarga no tiene dirección.** No es un nombre difícil de acertar: es que no
hay archivo ni fila que pedir. El zip se compone mientras sale, contra el POST de
quien pulsó el botón (`apps/exports/paquete.py`), y pedir esa URL con un GET
devuelve un 405.

**Lo que no va dentro**: los Usuarios de la Clínica y el Registro de acceso. Los
primeros son las cuentas con que entra su gente —y el cierre se las lleva—; el
segundo es evidencia ante la Ley 21.719 y no material de migración. El derecho de
acceso de un Tutor concreto a lo que se vio de él es del **20**.

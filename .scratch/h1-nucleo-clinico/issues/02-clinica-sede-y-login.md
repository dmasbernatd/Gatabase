# 02 — Clínica, Sede y login de Usuario con roles

**What to build:** un Usuario entra al sistema con su correo y su contraseña y ve a qué Clínica y a qué Sede pertenece. El admin de la Clínica puede crear Usuarios, asignarles rol y asignarles Sedes.

**Blocked by:** 01

**Status:** done

- [x] Modelos de Clínica y Sede; una Clínica tiene una o varias Sedes
- [x] Usuario con rol `veterinario`, `recepción` o `admin`, y pertenencia a una o varias Sedes de su Clínica
- [x] Login y logout con `django-allauth`, con correo y contraseña
- [x] Tras entrar, el Usuario ve el nombre de su Clínica y su Sede actual, y puede cambiar de Sede si pertenece a varias
- [x] El admin de la Clínica crea Usuarios, les asigna rol y Sedes, y los desactiva
- [x] Un Usuario sin sesión que pide una página interna acaba en el login
- [x] Un Usuario con rol de recepción no accede a la administración de Usuarios
- [x] Comando de gestión para dar de alta una Clínica con su primera Sede y su primer admin

## Comments

Implementado en `apps/tenancy`. Notas para los tickets siguientes:

- **`AUTH_USER_MODEL = "tenancy.Usuario"`**, fijado antes de que existiera ninguna migración. El Usuario entra con el **correo**, único en todo el sistema y no solo dentro de su Clínica: quien trabaje en dos Clínicas necesita dos correos. Es la consecuencia de que el login ocurre antes de saber en qué Clínica está.
- El Usuario hereda de `AbstractBaseUser` **sin `PermissionsMixin`**: los permisos de Gatabase son el `rol` y las Sedes, no los grupos de Django, y no hay sitio de administración que los use. Si algún día hace falta `has_perm`, se añade entonces.
- El manager **no tiene `create_superuser`**: no hay admin de Django al que entrar. El alta de una Clínica es `manage.py crear_clinica`, que crea Clínica, primera Sede y primer admin en una transacción y se niega a pisar una Clínica ya dada de alta.
- De `allauth` se enrutan **solo** login, logout y `account_inactive`. No hay URL de registro: `allauth` soporta esa configuración y deja de ofrecer el enlace cuando `account_signup` no se puede resolver. Sin verificación por correo (`ACCOUNT_EMAIL_VERIFICATION = "none"`) porque todavía no hay correo saliente; por lo mismo, el admin fija una **contraseña inicial** al crear un Usuario, validada con los validadores de Django. Cuando haya correo, eso se sustituye por una invitación.
- Plantilla de login propia en `templates/account/login.html`, para que su texto pase por `gettext` como el del resto. Las demás plantillas de `allauth` extienden `base.html` vía `ACCOUNT_TEMPLATE_EXTENDS`.
- **Sede actual en la sesión**, no en el Usuario (`apps/tenancy/sedes.py`): la misma cuenta puede estar abierta en el mostrador de una Sede y en el box de otra. Si el admin le quita la Sede guardada, cae a la primera que le quede en lugar de dejarlo sin Sede. El contexto de plantilla `apps.tenancy.contexto.sesion_de_clinica` pone Clínica, Sede actual y Sedes del Usuario en toda página interna; el ticket 13 lo aprovechará para mostrar siempre quién está activo.
- **Aislamiento por Clínica, a mano y en las vistas**: `Usuario.objects.filter(clinic=request.user.clinic)`, y los formularios limitan el `<select>` de Sedes a las de la Clínica de quien administra. Pedir un Usuario o una Sede de otra Clínica es **404**. Que las Sedes de un Usuario sean de su Clínica lo garantiza el formulario, no el modelo: `usuario.sedes.add(sede_ajena)` desde el ORM sigue siendo legal.
- **Deuda consciente hasta el ticket 03**: ADR-0003 pide manager por defecto que filtre y middleware que resuelva la Clínica, más el test estructural que recorre los modelos de dominio. Nada de eso existe todavía — aquí el filtrado es explícito, vista a vista. Al implementar el 03 hay que volver a `views.py` y `forms.py` de esta app y a los primeros modelos con `clinic`.
- Rol y acceso: el decorador `solo_admin` de `apps/tenancy/views.py` da **403** a veterinario y recepción, y manda al login a quien no tiene sesión. `login_required` va siempre **por fuera** de `require_POST`: si no, una petición sin sesión recibe un 405 que ya cuenta que la página existe. Un admin **no puede desactivarse a sí mismo**, y eso se comprueba en la vista, no solo escondiendo el botón: dejaría a la Clínica sin quien administre.
- La contraseña inicial se valida contra un Usuario armado a mano con el correo y el nombre del formulario. `self.instance` todavía está vacío durante `clean()` — Django lo rellena después, en `_post_clean` —, así que validar contra él dejaba pasar una contraseña igual al correo. Mismo cuidado en `crear_clinica`.
- Tests por HTTP en `tests/test_login.py`, `tests/test_panel.py`, `tests/test_administracion_de_usuarios.py` y `tests/test_alta_de_clinica.py`. Se comprobó en rojo — invirtiendo el filtro por Clínica, el decorador de rol, la exclusión del propio admin y la validación de la contraseña — que esos tests fallan de verdad.
- `tests/factories.py` gana `ClinicaFactory`, `SedeFactory` y una `UsuarioFactory` que crea la cuenta con la contraseña cifrada y le da una Sede de su Clínica si no se le pasa ninguna.

Pendiente y consciente: caducidad de sesión, cambio rápido de Usuario y segundo factor del admin son del ticket 13; el Horario de atención y las Clínicas de derivación de la Sede, del 14.

# Gatabase

Gestión clínica y de negocio para clínicas veterinarias en Chile: agenda, historia clínica de los Pacientes y recordatorios sanitarios.

El vocabulario del dominio está en [`CONTEXT.md`](CONTEXT.md); las decisiones estructurales, en [`docs/adr/`](docs/adr/). Léelos antes de tocar tenancy, Consulta, auditoría o mensajería.

## Estado

En desarrollo activo, con el hito **H1 — Núcleo clínico** en curso.

**Stack:** Python 3.12 · Django 6.1 · PostgreSQL (psycopg 3) · django-allauth · server-rendered.

**Funcionando hoy:**

- **Aislamiento multi-clínica por defecto.** Los modelos de dominio heredan el filtro por Clínica y un `check` de Django falla al arrancar si alguno no lo cumple ([ADR-0003](docs/adr/0003-tenancy-por-clave-ajena-y-manager.md)). La garantía no depende de acordarse de filtrar.
- **Autenticación y roles.** Login por correo, roles `veterinario` / `recepcion` / `admin`, cambio de Sede en sesión, y administración de Usuarios desde el panel. Sin registro abierto: la primera Clínica se crea por comando.
- **Fichas de Tutor**, con RUT y datos de contacto.
- **Registro de acceso** a datos personales (rama `worktree-04-registro-de-acceso`, pendiente de integrar).
- **i18n es-CL** con un test que falla si aparece texto visible fuera de `gettext`.
- **Fechas en UTC** con presentación en `America/Santiago`, verificado en verano e invierno austral.

**Calidad:** 50 tests (`pytest` + `pytest-django` + `factory_boy`) que entran por la petición HTTP y comprueban lo que el Usuario observa. 5 decisiones estructurales registradas en [`docs/adr/`](docs/adr/).

**Hoja de ruta:**

| Hito | Alcance | Estado |
|------|---------|--------|
| **H1** — Núcleo clínico | Clínica, Usuarios, Tutores y Pacientes | en curso |
| **H2** — Historia clínica | Consulta append-only, enmiendas y adjuntos | especificado |
| **H3** — Agenda y pendientes | Horas, aplicaciones y salud preventiva | especificado |
| **H4** — Conversaciones | WhatsApp y autorespuesta | especificado |

El proyecto nace de un problema concreto: una clínica veterinaria chilena de una sede que gestiona sus fichas en planillas y papel, y que además debe poder demostrar quién accede a los datos de sus clientes antes de que la **Ley 21.719** de protección de datos personales entre en vigencia el 1 de diciembre de 2026.

Se desarrolla con asistencia de IA como práctica deliberada de esa metodología sobre un stack fullstack Python.

## Requisitos

- Python 3.12 o superior
- Podman o Docker, para levantar Postgres
- `gettext` (`msgfmt`, `xgettext`), para los catálogos de idioma

## Arranque

```sh
make setup   # entorno virtual, dependencias y .env
make dev     # levanta Postgres, migra y sirve en http://localhost:8000
```

`make dev` es el comando único de arranque. Por debajo hace tres cosas: `scripts/db.sh` (levanta Postgres en un contenedor y espera a que acepte conexiones), `manage.py migrate` y `manage.py runserver`.

`scripts/db.sh` usa podman o docker directamente, sin compose, para no exigir otra herramienta más. Elige el motor con `CONTAINER_ENGINE=docker` si tienes los dos. Si prefieres un Postgres propio, apunta las variables `POSTGRES_*` de `.env` a él y sáltate `make db`.

Postgres se publica en el puerto **5433** del host, para no chocar con un Postgres del sistema en el 5432. Todos los valores configurables viven en `.env` (plantilla en `.env.example`); el entorno real tiene prioridad sobre el archivo.

## Tests

```sh
make test    # equivale a: ./scripts/db.sh && .venv/bin/pytest
```

`pytest-django` crea y destruye su propia base de datos de test contra el mismo Postgres. La configuración vive en `pyproject.toml`.

Un buen test aquí entra por la petición HTTP con el cliente de test de Django y comprueba lo que el Usuario observa: qué ve en la página, qué queda guardado, qué se le niega. Los datos se construyen con `factory_boy`: las fábricas compartidas viven en `tests/factories.py`, una por modelo de dominio; las de un solo test, junto a ese test.

## Fechas e idioma

- `USE_TZ` activo: la base de datos guarda **UTC** y la presentación usa `America/Santiago` (`TIME_ZONE`). `tests/test_horas.py` lo comprueba en verano y en invierno austral, donde el desfase cambia.
- `USE_I18N` activo con `LANGUAGE_CODE = "es-cl"`. Todo texto visible pasa por `gettext`, aunque es-CL sea el único idioma: `make messages` lo extrae a `locale/es_CL/LC_MESSAGES/django.po` y `make compile` lo compila. Los `msgstr` están vacíos a propósito — es-CL es el idioma de origen y gettext presenta el `msgid`. `tests/test_plantillas_en_gettext.py` recorre las plantillas y falla si aparece texto visible fuera de `gettext`, para que la regla no dependa de acordarse.

## Entrar en el sistema

Un Usuario entra en `/accounts/login/` con su **correo** y su contraseña, y aterriza en el panel de su Clínica (`/panel/`), que le muestra en qué Clínica y en qué Sede está trabajando. Si pertenece a varias Sedes, cambia de Sede desde la cabecera; la Sede actual vive en la sesión, no en el Usuario.

No hay registro abierto: **no existe** una URL de alta. La primera Clínica, su primera Sede y su primer admin se crean por comando:

```sh
.venv/bin/python manage.py crear_clinica \
  --clinica "Clínica Los Andes" --sede "Providencia" \
  --email admin@losandes.example --nombre Camila --apellidos Rojas
```

La contraseña se pide por teclado si no se pasa `--contrasena`. A partir de ahí, el admin de la Clínica crea el resto de los Usuarios en `/panel/usuarios/`, les asigna rol (`veterinario`, `recepcion`, `admin`) y Sedes, y los desactiva. Hasta que haya correo saliente, el admin fija una contraseña inicial y se la entrega al Usuario.

De `django-allauth` se enrutan solo el login, el logout y la página de cuenta desactivada. Lo que no está enrutado no existe.

No hay `django.contrib.admin`: sería una segunda puerta de entrada, con sus propios permisos, al lado de los roles de `tenancy`. El segundo factor para el rol admin y la caducidad de sesión son del ticket 13.

## Aislamiento por Clínica

La Clínica es la frontera de todos los datos ([ADR-0003](docs/adr/0003-tenancy-por-clave-ajena-y-manager.md)). La garantía no es acordarse de filtrar: es que filtrar sea lo que pasa por defecto.

**Todo modelo de dominio nuevo hereda de `apps.tenancy.aislamiento.ModeloDeLaClinica`.** Eso le da la clave ajena `clinic` y un manager `objects` que solo ve la Clínica activa:

```python
from django.db import models
from apps.tenancy.aislamiento import ModeloDeLaClinica

class Paciente(ModeloDeLaClinica):
    nombre = models.CharField(max_length=200)
```

Quién es la Clínica activa lo resuelve el middleware `apps.tenancy.middleware.clinica_del_usuario` a partir del Usuario autenticado, y queda también en `request.clinica`. Fuera de una petición — comandos, tareas, tests — se fija con el gestor de contexto `activar_clinica(clinica)`.

De ahí salen tres reglas prácticas:

- **Las vistas no filtran por Clínica.** `Tutor.objects.all()` y `get_object_or_404(Tutor, pk=pk)` ya están filtrados. Pedir por su identificador un objeto de otra Clínica da **404, nunca 403 con contenido**: la existencia del objeto ya es información.
- **Sin Clínica activa, `objects` no devuelve nada.** Un olvido produce una página vacía, jamás datos de la Clínica de al lado.
- **Cruzar la frontera es explícito.** El manager `de_todas_las_clinicas` existe para lo que de verdad la cruza — el alta de una Clínica, una exportación, las fábricas de test — y su nombre está pensado para saltar a la vista en una revisión.

Que la regla se cumpla no depende de nadie: `apps/tenancy/comprobaciones.py` registra un `check` de Django que recorre los modelos de las apps de dominio y falla si alguno no lleva `clinic` o no filtra por ella. Salta al arrancar, en `manage.py check` y en `tests/test_estructura.py`.

## Estructura

```
config/        configuración de Django, urls y vista raíz
scripts/       utilidades de desarrollo (levantar Postgres)
apps/          las nueve apps del dominio
templates/     plantillas server-rendered
tests/         tests que cruzan apps
locale/        catálogos de gettext
```

Las apps son `tenancy`, `tutors`, `patients`, `records`, `preventive`, `scheduling`, `notices`, `audit` e `imports`. Existen vacías desde el primer día para fijar dónde va cada cosa. Sus dependencias permitidas están en [`CLAUDE.md`](CLAUDE.md): `records` no importa de `scheduling`, y `audit` no importa de ninguna app de dominio.

Los nombres de app siguen el vocabulario de [`CONTEXT.md`](CONTEXT.md), incluidas sus palabras a evitar: la app de Tutores es `tutors` y no `clients`; la del Aviso de cita y los Pendientes es `notices` y no `reminders`.

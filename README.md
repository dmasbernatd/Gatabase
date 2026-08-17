# Gatabase

Gestión clínica y de negocio para clínicas veterinarias en Chile: agenda, historia clínica de los Pacientes y recordatorios sanitarios.

El vocabulario del dominio está en [`CONTEXT.md`](CONTEXT.md); las decisiones estructurales, en [`docs/adr/`](docs/adr/). Léelos antes de tocar tenancy, Consulta, auditoría o mensajería.

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

No hay `django.contrib.admin`: la autenticación la deciden los tickets 02 y 13 — `django-allauth`, roles y segundo factor para admin. El admin de Django sería una segunda puerta de entrada que nadie ha decidido.

## Estructura

```
config/        configuración de Django, urls y vista raíz
scripts/       utilidades de desarrollo (levantar Postgres)
apps/          las nueve apps del dominio, todavía vacías
templates/     plantillas server-rendered
tests/         tests que cruzan apps
locale/        catálogos de gettext
```

Las apps son `tenancy`, `clients`, `patients`, `records`, `preventive`, `scheduling`, `reminders`, `audit` e `imports`. Existen vacías desde el primer día para fijar dónde va cada cosa. Sus dependencias permitidas están en [`CLAUDE.md`](CLAUDE.md): `records` no importa de `scheduling`, y `audit` no importa de ninguna app de dominio.

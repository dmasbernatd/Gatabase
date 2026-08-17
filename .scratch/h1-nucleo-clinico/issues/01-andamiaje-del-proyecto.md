# 01 — Andamiaje del proyecto y primera página verificable

**What to build:** un proyecto Django que arranca contra Postgres, sirve una página y tiene la suite de tests corriendo en verde. Nadie de la clínica ve valor todavía; lo que entrega es la base sobre la que todo lo demás es verificable.

**Blocked by:** None — can start immediately.

**Status:** done

- [x] Proyecto Django con Postgres, arrancable con un comando documentado en el README
- [x] `USE_TZ` activo, hora almacenada en UTC y `TIME_ZONE` en `America/Santiago`
- [x] `USE_I18N` activo, idioma `es-CL`, y todos los textos de plantilla pasando por `gettext` desde el primer día
- [x] `pytest-django` y `factory_boy` configurados; `pytest` corre y pasa
- [x] Un test que comprueba que la página raíz responde
- [x] Un test que comprueba que una fecha guardada y recuperada mantiene el instante correcto al presentarse en `America/Santiago`
- [x] Las nueve apps del spec creadas vacías (`tenancy`, `tutors`, `patients`, `records`, `preventive`, `scheduling`, `notices`, `audit`, `imports`), para fijar la estructura desde el principio

## Comments

Implementado. Notas para los tickets siguientes:

- Postgres de desarrollo en un contenedor por `scripts/db.sh` (podman o docker, **sin compose**: la máquina de desarrollo no tenía proveedor de compose instalado). Se publica en el puerto **5433** del host para no chocar con un Postgres del sistema en el 5432.
- `make dev` es el comando único de arranque; `make test` levanta la base y corre `pytest`.
- El test de zona horaria entra por Postgres de verdad y está parametrizado en verano y en invierno austral, donde el desfase de `America/Santiago` cambia (-03:00 y -04:00). Se comprobó que falla si no hay base de datos, para que no pase en vacío.
- `es-CL` es el idioma de origen: el catálogo `locale/es_CL/LC_MESSAGES/django.po` existe con los `msgstr` vacíos a propósito. Su valor es comprobar que todo texto visible pasa por `gettext`.
- Las nueve apps tienen `AppConfig` con `label` explícito y `models.py` vacío, listos para los tickets 02 en adelante.
- `tests/factories.py` fija la convención de `factory_boy`: una fábrica por modelo de dominio, compartidas ahí, las de un solo test junto a ese test.
- `tests/test_plantillas_en_gettext.py` recorre las plantillas y falla si hay texto visible fuera de `gettext`. Se comprobó en rojo con un `<p>` escrito a mano.
- **Sin `django.contrib.admin`**: sería una segunda puerta de entrada, y la autenticación la deciden los tickets 02 y 13 (allauth, roles, segundo factor).
- Sin `DJANGO_SECRET_KEY` y con `DJANGO_DEBUG=False`, el proyecto no arranca. En desarrollo sigue arrancando sin configurar nada.

Pendiente para el ticket 03: el test estructural de ADR-0003 que recorre los modelos de dominio y falla si a alguno le falta `clinic`. Aquí no había modelos que recorrer.

Nota de vocabulario, **resuelta**: los nombres de app `clients` y `reminders` chocaban con las palabras a evitar de `CONTEXT.md` (`cliente`, `recordatorio`). Renombradas a **`tutors`** y **`notices`** por decisión del usuario, antes de que hubiera modelos ni migraciones. Los specs de H1, H3 y H4 quedan actualizados: donde decían `clients` y `reminders`, ahora dicen `tutors` y `notices`.

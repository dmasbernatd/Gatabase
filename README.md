# Gatabase

Gestión clínica y de negocio para clínicas veterinarias en Chile: agenda, historia clínica de los Pacientes y recordatorios sanitarios.

El vocabulario del dominio está en [`CONTEXT.md`](CONTEXT.md); las decisiones estructurales, en [`docs/adr/`](docs/adr/). Léelos antes de tocar tenancy, Consulta, auditoría o mensajería.

## Estado

En desarrollo activo, con el hito **H1 — Núcleo clínico** en curso.

**Stack:** Python 3.12 · Django 6.1 · PostgreSQL (psycopg 3) · django-allauth · server-rendered.

**Funcionando hoy:**

- **Aislamiento multi-clínica por defecto.** Los modelos de dominio heredan el filtro por Clínica y un `check` de Django falla al arrancar si alguno no lo cumple ([ADR-0003](docs/adr/0003-tenancy-por-clave-ajena-y-manager.md)). La garantía no depende de acordarse de filtrar.
- **Autenticación y roles.** Login por correo, roles `veterinario` / `recepcion` / `admin`, cambio de Sede en sesión, y administración de Usuarios desde el panel. Sin registro abierto: la primera Clínica se crea por comando.
- **Registro de acceso** a datos personales, inalterable y escrito desde las vistas, con consulta filtrable para el admin ([ADR-0004](docs/adr/0004-registro-de-acceso-propio-para-registrar-lecturas.md)).
- **Fichero de Tutores.** Alta, ficha y corrección, con listado buscable, ordenable y paginado, y cada acceso anotado.
- **Fichas de Paciente**, con catálogo cerrado de especies y catálogo de razas por especie que sugiere sin cerrar el paso al texto libre. Un Paciente se registra desde la ficha del Tutor que lo trae, un Paciente puede tener varios Tutores y uno solo de ellos es el responsable. Un Paciente nunca se borra: el que muere o deja de venir cambia de estado, conserva su ficha entera y las listas lo esconden por defecto sin perderlo de vista.
- **i18n es-CL** con un test que falla si aparece texto visible fuera de `gettext`.
- **Fechas en UTC** con presentación en `America/Santiago`, verificado en verano e invierno austral.

**Calidad:** la batería de tests (`pytest` + `pytest-django` + `factory_boy`) entra por la petición HTTP y comprueba lo que el Usuario observa; `make test` dice cuántos son. Las decisiones estructurales están en [`docs/adr/`](docs/adr/).

Esta sección resume lo que hay, no lo que falta: el detalle ticket a ticket vive en el tracker (`.scratch/<hito>/issues/`), que es lo que se actualiza al trabajar. Aquí no se prometen contadores ni listas de campos, porque envejecen sin que nadie se entere.

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

Y la misma frontera desde el otro extremo: **todo formulario de un modelo de dominio hereda de `apps.tenancy.aislamiento.FormularioDeLaClinica`**, que recibe la Clínica de quien lo está rellenando y se la pone al objeto al guardar. Ningún formulario ofrece la Clínica como campo: un `<select>` de Clínicas sería una frontera dibujada en el navegador, y un `clinic` colado en el POST no va a ninguna parte.

Que la regla se cumpla no depende de nadie: `apps/tenancy/comprobaciones.py` registra un `check` de Django que recorre los modelos de las apps de dominio y falla si alguno no lleva `clinic` o no filtra por ella. Salta al arrancar, en `manage.py check` y en `tests/test_estructura.py`.

## Registro de acceso

Cada vez que un Usuario ve o modifica datos personales queda una anotación de quién, qué y cuándo ([ADR-0004](docs/adr/0004-registro-de-acceso-propio-para-registrar-lecturas.md)). Es la evidencia que exige la Ley 21.719, y es la única pieza del sistema que no se puede añadir con efecto retroactivo.

Se escribe **desde las vistas**, no desde señales de modelo: leer no dispara ninguna señal, así que ninguna librería basada en señales puede capturar una lectura.

**Toda vista que sirva datos personales lleva el decorador `deja_constancia`**, por dentro de `login_required`:

```python
from apps.audit.models import Accion
from apps.audit.registro import deja_constancia

@login_required
@deja_constancia(Accion.LECTURA, sobre=Tutor)          # ficha: el `pk` de la URL dice cuál
def ficha(request, pk): ...

@login_required
@deja_constancia(Accion.LECTURA, sobre=Tutor, identificado_por=None)   # listado: el conjunto
def lista(request): ...
```

El decorador anota **después** de que la vista responda, y solo si respondió: un 404 —el Tutor es de otra Clínica— no llegó a servir nada, y anotarlo llenaría de accesos falsos justo la tabla que tiene que valer como prueba. Cuando lo accedido no sale de la URL —un formulario que acaba de guardar, una exportación—, la vista llama a `apps.audit.registro.anotar` con el objeto en la mano.

`audit` no importa de ninguna app de dominio: el tipo del objeto se guarda como texto (`tutors.Tutor`), así que el Registro anota accesos a Pacientes, Adjuntos o Conversaciones sin conocer esas apps. De `tenancy` sí depende, y no puede no depender: su tabla lleva `clinic` como cualquier otra y apunta al Usuario que accedió.

Una anotación no cambia nunca, y eso lo impone Postgres, no la aplicación (ver `apps/audit/migrations/0002_registro_inalterable.py`): se le retiran `UPDATE`, `DELETE` y `TRUNCATE` sobre la tabla al rol de la aplicación, **y** un disparador hace reventar el `UPDATE` y el `DELETE`. Las dos cosas, porque un rol superusuario —el de una máquina de desarrollo— se salta los permisos pero no el disparador. Consecuencia buscada: borrar una Clínica con accesos anotados falla, porque el borrado en cascada tropieza con el disparador; una Clínica que se va se exporta y se cierra, no se borra por debajo, y los datos de desarrollo se rehacen recreando la base.

**Condición de despliegue**: en producción la aplicación se conecta con un rol que **no** es superusuario —si no, se salta los permisos igual que en desarrollo— y, si las migraciones se aplican con un rol distinto del de la aplicación, hay que retirarle a ese otro rol los mismos tres permisos: `REVOKE` los concede por nombre, y la migración solo alcanza al rol que la ejecuta.

Eso no se queda en una nota: `apps/audit/comprobaciones.py` registra un `check` de Django que, con `DEBUG` apagado y fuera de la batería de tests, le pregunta a Postgres por la conexión de la aplicación si ese rol podría tocar la tabla. Un rol superusuario es `audit.E001`; un rol al que nadie le retiró los permisos, `audit.E002`; y si la base no responde, `audit.W001` avisa en vez de reventar. Con `DEBUG=False` la aplicación no arranca hasta que la condición se cumple, así que la garantía deja de depender de que alguien leyera este párrafo.

El admin de la Clínica lo consulta en `/panel/registro/`, filtrando por Usuario, por objeto y por rango de fechas. El rango son días de **Santiago**, no instantes en UTC: quien pide "el 20 de junio" quiere los accesos de ese día en la clínica. Un filtro que no se entiende no devuelve nada, nunca el Registro entero. Esa página no se anota a sí misma —el Registro no contiene datos personales de Tutor ni de Paciente— y es de solo lectura, porque no podría ser otra cosa.

## El fichero de Tutores

Recepción registra un Tutor, lo encuentra en el listado, abre su ficha y la corrige, todo en `/panel/tutores/`: el listado, `nuevo/` para el alta, `<pk>/` para la ficha y `<pk>/corregir/` para la corrección.

En el Tutor viven **solo sus datos personales** —nombre, apellidos, teléfono, correo y dirección—, enumerados en `Tutor.DATOS_PERSONALES`. Los datos clínicos son del Paciente y viven en `patients`. La separación es la que hace posible el ticket 20 (ADR-0004): un Tutor puede exigir la supresión de sus datos personales mientras la Historia clínica de sus Pacientes —de la que es titular el animal, no él— tiene que conservarse, así que anonimizar será vaciar esos campos sin tocar ninguna otra tabla. `tests/test_fichas_de_tutor.py` comprueba que la tabla del Tutor no tiene ningún campo fuera de esa lista: un campo nuevo obliga a decidir si es dato personal, y a decidirlo el día que se escribe.

Solo el nombre es obligatorio. En el mostrador a veces no hay más que un nombre y un teléfono, y exigir el resto empuja a rellenarlo con cualquier cosa, que es peor que un hueco: un dato falso no se distingue de uno verdadero.

Buscar, ordenar y paginar el listado es `apps/tutors/listado.py`, fuera de la vista porque es lo que tiene reglas:

- **Se ordena solo por las columnas que el listado enseña** (`COLUMNAS`). Un `orden` que no se reconoce cae en el de siempre en vez de convertirse en un `ORDER BY` cualquiera escrito desde la URL. Cada columna trae su desempate: sin él, dos Tutores del mismo apellido pueden cambiar de sitio entre una página y la siguiente y salir dos veces o ninguna.
- **Una columna del listado es una `Columna` y una sola edición** (`COLUMNAS`). El mismo objeto sabe su rótulo, por qué campos ordena, qué `aria-sort` anuncia su cabecera y qué celda pinta en cada fila; la plantilla recorre la lista para las cabeceras y para el cuerpo, y el `colspan` de la fila vacía las cuenta. Añadir el RUT (ticket 06) al listado es tocar `COLUMNAS` y nada más.
- **La búsqueda reparte lo escrito entre los campos**: cada palabra tiene que aparecer en alguno, no todas en el mismo, así que «camila rojas» encuentra a quien tiene el nombre en un campo y el apellido en otro. Es la búsqueda del fichero de Tutores; la caja única que además busca Pacientes y microchips, tolerante a tildes, es del ticket 11.
- **El orden y la búsqueda viajan en los enlaces** del paginador y de las cabeceras, y cambiar de orden vuelve a la primera página.

## HTMX

`htmx` está versionado en `static/vendor/` y se sirve desde la propia aplicación, nunca desde un CDN (ver `static/vendor/LEEME.md`): son páginas con datos personales, y un despliegue con la red capada tiene que seguir funcionando.

En el listado de Tutores, buscar, ordenar y pasar de página cambian **solo el listado** (`templates/tutors/listado.html`), que la vista devuelve solo cuando la petición trae la cabecera `HX-Request`. El destino del intercambio se declara una vez en el contenedor y los enlaces de dentro lo heredan.

La caja de búsqueda viaja **dentro** de ese trozo, y no fuera junto al título, porque arrastra el orden actual en un campo oculto: si se quedara fuera de lo que se sustituye, seguiría llevando el orden de antes y la siguiente búsqueda desharía la ordenación recién pedida. Es el tipo de fallo que solo aparece encadenando dos acciones, así que tiene test.

Dos reglas que conviene no perder:

- **Todo sigue funcionando sin JavaScript.** El formulario es un `GET` normal y cada enlace lleva su `href`; htmx solo evita recargar la página entera. Los tests comprueban las dos formas de servir el listado. Que cada enlace lleve a la vez `href` y `hx-get` lo sabe un solo sitio: `templates/tutors/_enlace_del_listado.html`, que usan las cabeceras, Anterior y Siguiente.
- **No se busca a cada tecla.** Cada una de esas peticiones sirve datos personales y por tanto se anota en el Registro de acceso: una búsqueda por pulsación llenaría de ruido justo la tabla que tiene que valer como prueba. Se dispara al enviar la búsqueda y al pulsar una cabecera o una página. La búsqueda incremental del ticket 11 llega junto con la regla que la hace admisible: registrar el acceso al abrir la ficha, no al listar.

## Estructura

```
config/        configuración de Django, urls y vista raíz
scripts/       utilidades de desarrollo (levantar Postgres)
apps/          las nueve apps del dominio
templates/     plantillas server-rendered
static/        estáticos propios y de terceros (htmx), versionados
tests/         tests que cruzan apps
locale/        catálogos de gettext
```

Las apps son `tenancy`, `tutors`, `patients`, `records`, `preventive`, `scheduling`, `notices`, `audit` e `imports`. Existen vacías desde el primer día para fijar dónde va cada cosa. Sus dependencias permitidas están en [`CLAUDE.md`](CLAUDE.md): `records` no importa de `scheduling`, y `audit` no importa de ninguna app de dominio (de `tenancy` sí: la Clínica es la frontera de todo dato y el Usuario es quien accede).

Los nombres de app siguen el vocabulario de [`CONTEXT.md`](CONTEXT.md), incluidas sus palabras a evitar: la app de Tutores es `tutors` y no `clients`; la del Aviso de cita y los Pendientes es `notices` y no `reminders`.

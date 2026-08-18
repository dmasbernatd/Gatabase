# 05 — Fichas de Tutor

**What to build:** recepción registra un Tutor con sus datos de contacto, lo encuentra en un listado, abre su ficha y la corrige. Es el primer punto donde la clínica deja de depender de la planilla para saber quién es su cliente.

**Blocked by:** 03, 04

**Status:** done

- [x] Tutor con nombre, apellidos, teléfono, correo y dirección
- [x] Crear, editar, listar y ver la ficha de un Tutor, con HTMX para los flujos que lo merezcan
- [x] Listado paginado y ordenable, usable con cientos de Tutores
- [x] Los datos personales del Tutor viven en su propio modelo, separados de los datos clínicos del Paciente, para permitir anonimizar después sin tocar la historia
- [x] Abrir o editar una ficha queda en el Registro de acceso
- [x] Un Usuario de otra Clínica no ve ni encuentra estos Tutores
- [x] Los textos de la interfaz pasan por `gettext`

## Comments

**Solo el nombre es obligatorio.** En el mostrador a veces no hay más que un nombre y un teléfono, y exigir apellidos, correo y dirección empujaría a rellenarlos con cualquier cosa. Un hueco se ve; un dato inventado no se distingue de uno verdadero, y estos son justo los datos con los que después se contacta al Tutor.

**`DATOS_PERSONALES` en el modelo**, y un test que comprueba que la tabla del Tutor no tiene ningún campo fuera de esa lista más `id` y `clinic`. Es la casilla de la separación de datos convertida en algo que se rompe solo: la anonimización del ticket 20 será vaciar esos campos sin tocar ninguna otra tabla, y eso solo se sostiene si ningún dato personal se escapa a otro modelo y ningún dato clínico se cuela en este. El día que alguien añada un campo al Tutor, el test le obliga a decidir de cuál de los dos se trata.

**Abrir y editar se anotan distinto** (ADR-0004). La ficha y el listado siguen con el decorador `deja_constancia` del ticket 04. El formulario de corrección no: anota `LECTURA` al servirse —trae los datos del Tutor rellenados, y quien lo abre los ha visto aunque no guarde nada, incluido el reintento tras un error de validación— y `MODIFICACION` solo cuando el guardado ocurre de verdad. El alta anota `CREACION` con el Tutor ya en la mano, que es el camino que el ticket 04 dejó abierto en `anotar`. Un formulario de alta vacío no enseña datos de nadie y no se anota.

**Buscar, ordenar y paginar viven en `apps/tutors/listado.py`**, no en la vista, porque es lo que tiene reglas. Se ordena solo por las columnas que el listado enseña: un `orden` que no se reconoce cae en el de siempre en vez de convertirse en un `ORDER BY` escrito desde la URL. Cada columna trae su desempate hasta el `pk`, porque sin él dos Tutores del mismo apellido pueden cambiar de sitio entre una página y la siguiente y aparecer dos veces o ninguna. La búsqueda reparte cada palabra entre los campos —nombre, apellidos, teléfono y correo—, así que «camila rojas» encuentra a quien tiene el nombre en un campo y el apellido en otro, que es como recepción escribe un nombre.

**HTMX solo donde lo merece**: buscar, ordenar y pasar de página cambian la tabla, no la página entera. No se busca a cada tecla, y no por rendimiento: cada una de esas peticiones sirve datos personales y se anota, y una búsqueda por pulsación llenaría de ruido justo la tabla que tiene que valer como prueba. La búsqueda incremental que pide el ticket 11 llega junto con la regla que la hace admisible —registrar el acceso al abrir la ficha, no al listar—, y esa regla contradice lo que el ticket 04 dejó montado, así que se decide allí y no aquí.

**Todo funciona sin JavaScript**: el formulario es un `GET` normal y cada enlace lleva su `href`; htmx solo evita recargar. Hay test de las dos formas de servir el listado.

**htmx se versiona en `static/vendor/`** y se sirve desde la propia aplicación, nunca desde un CDN: son páginas con datos personales que no tienen por qué pedirle un archivo a un tercero, un despliegue con la red capada tiene que seguir funcionando, y así la versión que se sirve es la que se probó.

**El aislamiento no se comprueba solo al leer**: guardar encima de un Tutor de otra Clínica da 404 y no lo toca, y el formulario no ofrece la Clínica —sale del Usuario—, así que un `clinic` colado en el POST no va a ninguna parte. Los tests están en `tests/test_aislamiento_por_clinica.py`, con los demás de su clase.

**Lo que no entra aquí**: el RUT y la normalización del teléfono son del 06 —el teléfono se guarda tal cual se escribe—, el vínculo con el Paciente del 07, la caja de búsqueda única y tolerante a tildes del 11, y el Consentimiento de contacto del 15.

### De la revisión

**Un fallo de verdad, y encadenado**: la caja de búsqueda estaba fuera del trozo que htmx sustituye, y llevaba el orden actual en un campo oculto. Ordenar y buscar después deshacía la ordenación recién pedida, porque ese campo se había quedado con el valor viejo. La caja se mudó dentro del trozo (`templates/tutors/listado.html`), y hay test: es un fallo que no aparece en ninguna acción suelta, solo al encadenar dos.

**El enlace a la ficha se mudó al nombre.** Estaba en los apellidos, que son opcionales: un Tutor registrado con las prisas del mostrador, sin apellidos, tenía por único enlace un guion. El nombre es el único dato obligatorio, así que es el que siempre se puede pulsar.

**`FormularioDeLaClinica` sale a `apps/tenancy/aislamiento.py`**, y de él heredan `TutorForm` y el `UsuarioForm` que ya existía: los dos repetían literalmente el «la Clínica sale de quien rellena, no del formulario». Va al lado de `ModeloDeLaClinica` porque es la misma frontera de ADR-0003 vista desde el otro extremo — el modelo impide leer fuera de la Clínica; el formulario, escribir fuera de ella.

**El orden dejó de ser un string suelto** (`Orden` en `apps/tutors/listado.py`). El `-` de delante se interpretaba en tres sitios; ahora se interpreta al entrar y lo que circula sabe responder por sus campos, por su `aria-sort` y por la cabecera que lo invierte.

**Se anota después de componer la respuesta**, también en el formulario de corrección: la regla del ticket 04 es que lo que no se llegó a servir no se anota, y anotar antes del `render` la rompía.

**Dos avisos de la revisión que se dejan como están, a propósito:**

- **Buscar por apellidos, teléfono y correo** no lo pide ninguna casilla, pero el listado ya traía caja de búsqueda del ticket 04 —solo por nombre— y ahora enseña esas tres columnas: buscar solo por una de las cuatro columnas visibles sería un fichero que esconde lo que muestra. El 11 conserva lo suyo, que es otra cosa: una caja única que además busca Pacientes y microchips, tolerante a tildes e incremental.
- **El alta anota `CREACION`.** La casilla habla de abrir o editar, pero `Accion.CREACION` existe desde el ticket 04 y el Registro es «qué Usuario vio o modificó qué dato»: dar de alta datos personales de una persona y que no conste sería el único hueco de la tabla.

**Una casilla comprobada a medias, y conviene que conste**: el test de la separación de datos verifica que en el Tutor no hay nada que no sea dato personal suyo. La otra mitad —que ningún dato personal del Tutor viva fuera de su modelo— no se puede comprobar todavía, porque el Paciente aún no existe. Es del ticket 07: el día que el Paciente tenga campos, ahí es donde hay que mirar.

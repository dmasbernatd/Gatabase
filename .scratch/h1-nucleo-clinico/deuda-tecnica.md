# Deuda técnica y cabos sueltos de H1

Lo que se va acumulando y no cabe en ningún ticket concreto. Cada punto dice qué
pasa, por qué importa y cuándo se paga. Si un punto crece hasta merecer trabajo
propio, se convierte en un issue numerado y aquí queda solo el enlace.

## Proceso

**El trabajo terminado se queda en worktrees sin integrar.** El ticket 04 estuvo
completo y con tests verdes en `worktree-04-registro-de-acceso` desde el 17 de
agosto de 2026, y `main` no lo tuvo hasta el 23. Mientras tanto, `main` recibió
dos commits de documentación que describían como "pendiente de integrar" algo ya
hecho. El coste no es el retraso: es que cada día que pasa, la rama y `main`
divergen y la integración deja de ser un `cherry-pick` limpio.
_Cuándo se paga_: al terminar un ticket en un worktree, integrarlo en `main` en
la misma sesión y liberar el worktree.
_Pagado el 23 de agosto de 2026_ en lo que quedaba pendiente: el commit del 05
se rebasó sobre `main`, se integró en avance rápido, y el worktree y su rama
local se liberaron. La regla sigue en pie para el próximo ticket.

**`main` local iba por delante de `origin`**, y la rama remota del worktree
seguía apuntando al commit de antes del rebase.
_Pagado el 23 de agosto de 2026_: `main` empujado en avance rápido y
`origin/worktree-04-registro-de-acceso` borrada, porque ya no tenía nada que no
estuviera en `main`.

## Documentación

**La sección de Estado del README se escribía a mano y envejecía sola.** Trajo
tres errores en un solo commit: un contador de tests obsoleto, un enlace a un
ADR con nombre de archivo inventado, y una descripción del Tutor que
correspondía a tickets aún sin integrar.
_Pagado el 23 de agosto de 2026_: la sección ya no promete contadores ni listas
de campos y remite al tracker, que es lo que se actualiza al trabajar.
_Lo que queda vivo_: el resto del README sí describe mecanismos con nombres de
archivo y de función. Eso envejece igual, pero se nota al leer el código; los
números no.

## Operación

**Borrar una Clínica no es posible** mientras tenga accesos anotados: la cascada
tropieza con el disparador de `audit`. Es la consecuencia buscada, pero
condiciona dos tickets.
_Pagado a medias el 23 de agosto de 2026_: la consecuencia está anotada como
casilla en el **16** (limpiar es rehacer la base, no borrar la Clínica) y en el
**19** (una Clínica que se va se exporta y se cierra). Lo que falta es decidir
**qué significa cerrar una Clínica** — desactivar a sus Usuarios, dejarla sin
acceso, algo más —, y eso se decide al hacer el 19.

## Rendimiento

**«Usable con cientos de Tutores» está afirmado, no sostenido.** Es una casilla
del ticket 05 que se dio por cumplida porque el listado pagina, y paginar no es
lo mismo que aguantar. Debajo hay tres cosas que nadie mide:

- El único índice del Tutor (`tutor_por_apellidos`: `clinic`, `apellidos`,
  `nombre`) sirve al orden por defecto. Ordenar por nombre, RUT, teléfono o
  correo —las otras cuatro cabeceras que el listado ofrece— es recorrer y ordenar
  en memoria toda la Clínica.
- La búsqueda es `icontains`, o sea un `LIKE '%…%'` por cada palabra y cada uno
  de los cinco campos buscables. Con comodín delante, ningún índice normal
  entra: es lectura secuencial de la tabla.
  _Al día del 06_: el RUT es el quinto, y es el único que **sí** tendría índice
  fácil: se guarda normalizado y se busca casi siempre entero, así que un
  `LIKE 'x%'` sobre `(clinic, rut)` bastaría. La restricción de unicidad ya crea
  un índice sobre esa pareja, aunque parcial y con la ordenación de la base: que
  sirva tal cual para un prefijo hay que medirlo, no darlo por hecho. Lo que
  falta en todo caso es que la búsqueda distinga un RUT completo del resto, en
  vez de meterlo en el mismo `%…%` que los demás campos. Se decide en el **11**,
  con el volumen del **16** delante.
- El `Paginator` hace su `COUNT(*)` de la consulta completa en cada petición,
  incluida cada búsqueda.

A cientos de Tutores esto no se nota, y por eso no es un fallo hoy. Lo que falta
no es optimizar a ciegas: es que **nada avise cuando deje de aguantar**. La
batería entra por HTTP y comprueba lo que el Usuario observa, que es lo correcto,
pero no cuenta consultas ni prueba a escala, así que una regresión de rendimiento
—un `N+1` al pintar la tabla, pongamos— pasaría entera y en verde.
_Cuándo se paga_: en el **16**, que es quien trae volumen de verdad. Con datos
mock encima, un `assertNumQueries` sobre el listado y la búsqueda deja de ser
teatro y empieza a defender algo. La decisión sobre índices y sobre buscar en
serio —tolerante a tildes, incremental— es del **11**, y conviene tomarla con
el volumen del 16 delante y no antes.

## Diseño del listado de Tutores

Todo esto son juicios de la revisión del 05, no violaciones de ninguna regla
escrita: nada estaba mal, y el ticket se dio por bueno con razón. Se anotó
porque el 06 añade el RUT, y el RUT es una columna más y un campo buscable más:
la primera vez que este diseño cobraba su peaje.
_Pagado el 23 de agosto de 2026_, antes de empezar el 06 y no durante, para que
el RUT llegue a un listado que ya sabe crecer.

**Añadir una columna al listado era tres ediciones y no fallaba nada si te
dejabas una.** Ahora es una: `COLUMNAS` (`apps/tutors/listado.py`) es una tupla
de `Columna`, y la plantilla la recorre dos veces —para las cabeceras y para el
cuerpo—, así que no hay forma de que una tabla tenga más cabeceras que celdas.
El `colspan` de la fila de «no hay resultados» las cuenta en vez de decir `4`.
Lo sostienen dos tests en `tests/test_fichas_de_tutor.py`
(`test_cada_fila_trae_una_celda_por_cabecera` y
`test_la_fila_de_sin_resultados_ocupa_toda_la_tabla`); verificado además
añadiendo una quinta columna de prueba, que salió entera y cuadrada sin tocar
la plantilla.

**La `Columna` que quería nacer ya nació.** Sabe su rótulo, por qué campos
ordena —su propio campo, su desempate y el `pk`—, qué `aria-sort` anuncia su
cabecera (`sentido_en`, que se llevó de `Orden`: presentación dentro del tipo
que la tiene) y qué celda pinta de cada Tutor. `Orden` ya no circula con la
clave de la columna sino con la `Columna` misma. La `Celda` se trajo de la
plantilla el guion del hueco: es la misma respuesta para toda columna vacía, y
la plantilla ya no sabe cuáles hay.

**Cada enlace del listado repetía su URL dos veces**, en `href` y en `hx-get`.
Los tres enlaces —cabeceras, Anterior y Siguiente— son ahora un
`{% include %}` de `templates/tutors/_enlace_del_listado.html`, que es el único
sitio que sabe que un enlace del listado lleva las dos cosas. El formulario de
búsqueda se queda con su par `action`/`hx-get`: es un `<form>`, no un enlace, y
meterlo en el mismo include sería juntar dos cosas por parecerse.
_Lo que queda vivo_: `PARAMETRO_DE_PAGINA` sigue sin aparecer en la plantilla
porque la plantilla no nombra la página; los otros dos los lee ya del listado
(`CAMPO_DE_BUSQUEDA`, `CAMPO_DE_ORDEN`) en vez de escribir `"q"` y `"orden"` a
mano.

**`crear` y `editar` (`apps/tutors/views.py`) tienen la misma forma**: construir
el formulario, validar, guardar, anotar y redirigir; difieren en la `Accion` y en
que la corrección anota además la lectura. A dos casos es tolerable y sacarlo
ahora sería inventar una abstracción con un solo ejemplo.
_Creció en el 06_: las dos vistas llaman ahora además a
`avisar_del_telefono_compartido` y a `constancia_del_rut_repetido`, en el mismo
sitio y por el mismo motivo.
_Mirado con cuatro ejemplos delante el 23 de agosto de 2026_, al escribir
`crear` y `editar` de Paciente, y **no se extrajo la vista genérica**. Con los
cuatro casos escritos, lo único que comparten es `si POST y válido: guardar y
redirigir; si no, componer la página y anotar` — cuatro líneas. Todo lo demás
difiere: el formulario y sus argumentos, qué hacer después de guardar (nada,
vincular al Tutor que lo trae, avisar del teléfono compartido), qué `Accion` se
anota y sobre qué objetos, la plantilla, el contexto y adónde se redirige. Una
función que recibiera todo eso sería más larga que lo que ahorra, y escondería
detrás de dos `callbacks` justo la parte que un revisor tiene que ver: qué queda
anotado en el Registro.
_Lo que sí se extrajo_ es la regla, que era el verdadero riesgo: `anotando`
(`apps/audit/registro.py`) devuelve la respuesta ya compuesta y anota lo que
enseña, así que el orden que sostiene al Registro —lo que no se llegó a servir no
se anota— dejó de depender de acordarse. Lo usan las cinco vistas que sirven
fichas.
_Cuándo se vuelve a mirar_: cuando aparezca un quinto caso que además se parezca
en lo que hoy difiere. Si no, esta entrada se cierra.

## Pagado

**La condición de despliegue de ADR-0004 ya la comprueba alguien.**
`apps/audit/comprobaciones.py` registra un `check` de Django que, con `DEBUG`
apagado y fuera de la batería de tests, le pregunta a Postgres por la conexión
de la aplicación si su rol podría modificar el Registro de acceso: `audit.E001`
si es superusuario, `audit.E002` si conserva los permisos, `audit.W001` si la
base no responde. Verificado a mano contra un rol no superusuario, con y sin los
permisos retirados. Tests en `tests/test_condicion_de_despliegue.py`.

**Los campos que normalizan lo escrito ya no son de `tutors`.**
`CampoQueNormaliza` —el `CharField` que pasa el valor por su normalizador en
`to_python` y en `get_prep_value`, para que un `save()` sin `full_clean()`
guarde igual que un formulario— era privado de `apps/tutors/campos.py`, y el
microchip del **08** necesitaba exactamente lo mismo por el mismo motivo: sin
normalizar al guardar, «único por Clínica» no significa nada. Vive ahora en
`apps/campos.py`, fuera de las dos apps, porque las dos lo necesitan y ninguna
puede importar de la otra (`CLAUDE.md`); qué es un RUT lo sigue decidiendo
`rut.py` y qué es un chip, `microchip.py`. _Pagado el 23 de agosto de 2026._

## Rendimiento del vínculo

**La lista de Tutores para vincular es un `<select>` con la Clínica entera.**
Hoy es correcto y no se nota, pero es el mismo problema que el listado de
Tutores y con menos excusa: no pagina, no busca y trae todos los nombres a la
página. A cientos de Tutores es una página de cientos de líneas para elegir uno.
_Cuándo se paga_: con la búsqueda del **11** delante, que es la que sabrá
encontrar a un Tutor por nombre, teléfono o RUT sin traerlos a todos; el
desplegable debería acabar siendo esa búsqueda. El volumen para notarlo lo trae
el **16**.

**La ficha del Tutor y la del Paciente anotan una lectura por cada nombre que
enseñan.** Es lo que ADR-0004 pide, y es correcto. Pero un Tutor con seis
Pacientes son siete anotaciones por visita, y el Registro crece con las
visitas, no con los datos. No es un problema hoy —la tabla está indexada por
Clínica y fecha— y no se toca sin medir.
_Cuándo se paga_: cuando el **16** ponga volumen y se pueda contar de verdad
cuánto ocupa un día de mostrador.

## Coincidencias entre fichas

**El 06 dejó media detección de duplicados, y el ticket propio es el 12.** Lo que
hay ahora mira un campo exacto cada vez: el RUT idéntico impide guardar, el
teléfono idéntico avisa. No mira nombres parecidos, ni un RUT tecleado con un
dígito de menos, ni un correo repetido, que es de lo que trata el **12**.
_Por qué importa ahora_: los dos avisos viven repartidos entre `TutorForm`
(quién se parece) y las vistas (qué se hace al respecto). Es poco código y está
en su sitio, pero el 12 traerá la tercera y la cuarta comparación, y ese es el
momento de decidir si «a quién se parece esta ficha» merece un módulo propio en
vez de un método por campo.
_Cuándo se paga_: en el **12**.
_El 07 no lo movió_: `PacienteForm` no compara con nada — el Paciente todavía no
tiene ningún dato que identifique a otro. El primero será el microchip, en el
**08**.
_El 08 lo miró y decidió no extraerlo todavía_ (23 de agosto de 2026). Ya hay
tres comparaciones —RUT, teléfono y microchip— y `clean_microchip` se parece a
`clean_rut` como se esperaba: los dos preguntan a `los_demas()` por un campo
exacto y los dos acaban en un enlace a la ficha que ya existe. Pero el parecido
es de forma, no de decisión: lo que cambia entre ellos —si el duplicado impide
guardar o solo avisa, y qué se le enseña a quien está delante— es justo lo que
un módulo común tendría que recibir por parámetro, y un módulo cuya única razón
de ser es un parámetro no es un módulo. Lo que sí se extrajo fue la mitad que
**no** decide nada, y por eso salió limpia: `CampoQueNormaliza`, en
`apps/campos.py` (ver abajo). La pregunta sigue siendo la del **12**, cuando
haya comparaciones que no sean de campo exacto y el «a quién se parece esta
ficha» tenga por fin algo que decidir de verdad.

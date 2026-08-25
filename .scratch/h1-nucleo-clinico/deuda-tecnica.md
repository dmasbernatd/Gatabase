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
- La búsqueda es `LIKE '%…%'` sobre los campos de texto. Con comodín delante,
  ningún índice normal entra: es lectura secuencial de la tabla.
  _Pagada en el **11** la mitad que se podía pagar_: lo escrito se lee ahora
  entero cuando es un número dictado, así que un RUT completo se busca con `=`
  —lo resuelve el índice de `rut_unico_dentro_de_la_clinica`— y un chip completo
  también —`paciente_por_microchip`—. No hizo falta ningún índice nuevo, y de
  paso un RUT dictado entero deja de traer a quien lo lleva dentro del suyo.
  _Lo que queda vivo_: los nombres siguen siendo un barrido, y ahí no hay índice
  barato — la respuesta sería un GIN de trigramas, que es otra extensión de
  Postgres y por tanto otro `CREATE EXTENSION` que el rol de la aplicación no
  puede correr (ver el **11**). No se toca sin medir, y medir es del **16**.
- El `Paginator` hace su `COUNT(*)` de la consulta completa en cada petición,
  incluida cada búsqueda. Sigue vivo en el listado de Tutores. La caja del
  mostrador del **11** no lo tiene: no pagina ni cuenta, trae veinte y uno de
  más, y con el sobrante sabe que hay más sin haber contado nada. Si el listado
  acaba haciendo lo mismo es decisión del **16**, cuando se pueda ver qué cuesta
  el `COUNT`.

A cientos de Tutores esto no se nota, y por eso no es un fallo hoy. Lo que falta
no es optimizar a ciegas: es que **nada avise cuando deje de aguantar**. La
batería entra por HTTP y comprueba lo que el Usuario observa, que es lo correcto,
pero no cuenta consultas ni prueba a escala, así que una regresión de rendimiento
—un `N+1` al pintar la tabla, pongamos— pasaría entera y en verde.
_Pagado para la caja del **11**_: `tests/test_busqueda.py` cuenta las consultas
de una búsqueda con un resultado y con sesenta y exige que sean las mismas —cada
fila dice quién responde por el animal, que es exactamente el `N+1` que no se
nota con tres Pacientes de prueba—, y busca además sobre una Clínica de
ochocientos. El listado de Tutores sigue sin esa red.
_Cuándo se paga_: en el **16**, que es quien trae volumen de verdad. Con datos
mock encima, contar consultas sobre el listado deja de ser teatro y empieza a
defender algo. La decisión sobre índices y sobre buscar en serio —tolerante a
tildes, incremental— la tomó el **11** con el volumen que pudo fabricarse él
mismo; lo que el 16 aporta es volumen **realista** —nombres que se repiten,
apellidos que colisionan—, que es donde un barrido por nombre se nota de verdad.

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
_Cuándo se paga_: el **11** ya dejó la pieza que hace falta —`condicion` sobre
`Tutor.POR_DONDE_SE_BUSCA` encuentra a un Tutor sin traerlos a todos—, así que
lo que queda es la mitad de interfaz: cambiar el `<select>` por una caja que
busque. No se hizo en el 11 porque el 11 buscaba Pacientes y esto busca Tutores,
y meterlo habría sido dos pantallas en un ticket. El volumen para notarlo lo
trae el **16**.

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
_Pagado el 24 de agosto de 2026, en el **12**._ «A quién se parece esta ficha»
tiene módulo propio: `apps/coincidencias.py`, fuera de las dos apps por lo mismo
que `busqueda.py`. Un `Parecido` dice por qué campo se confunde una ficha con
otra, qué se le dice a quien escribe y si además la base la va a rechazar; cada
formulario declara los suyos (`PARECIDOS`), al lado de `POR_DONDE_SE_BUSCA` y por
el mismo motivo. Lo que el 08 temía —«un módulo cuya única razón de ser es un
parámetro»— dejó de ser el caso cuando el mismo aviso tuvo que decirse en tres
sitios: el hueco que repinta htmx, el error al lado del campo y el aviso que
sobrevive a guardar. Se llevó por delante los dos `enlace_a` copiados y las dos
mitades de `constancia`/`avisar` repetidas en las dos apps.
_Lo que sigue sin haber_: comparaciones que no sean de campo exacto —nombres
parecidos, un RUT con un dígito de menos—. La detección compara por igualdad
sobre el dato ya normalizado, así que el segundo «Rocco» de una casa se
encuentra por la lista de Pacientes de su Tutor y no por parecido. Cuando haga
falta de verdad, entra por `Parecido`: es el único sitio donde hoy se decide qué
significa parecerse.

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

## La caja del mostrador

Lo que el **11** dejó decidido a medias, y por qué se dejó así.

**La caja vive en una página propia y no en la cabecera del panel.** Encontrar al
Paciente son hoy dos gestos desde cualquier otra pantalla: pulsar «Buscar» y
escribir. Una caja en la cabecera lo dejaría en uno, que es lo que se espera de
la funcionalidad que tiene que ganarle al archivador, pero pondría **dos** cajas
en la página de resultados —la de la cabecera y la de la página— y el ticket
pedía una sola. Hacer que la de la cabecera fuera la única obligaría a que su
`hx-target` existiera en todas las páginas del panel, y eso es un contenedor de
resultados escondido en cada una.
_Cuándo se paga_: cuando alguien use esto en un mostrador de verdad y diga si el
gesto de más molesta. No antes: es una decisión de uso, no de código.

**Un Tutor sin Pacientes no sale por la caja.** Lo que se encuentra son
Pacientes, así que quien todavía no ha traído a ningún animal solo aparece en el
fichero de Tutores, que tiene su propia búsqueda. Es raro —un Tutor se registra
casi siempre para registrar a un animal— pero pasa: se dio de alta la ficha y la
consulta era para la semana siguiente.
_Cuándo se paga_: si aparece la queja. La respuesta entonces no es añadir Tutores
a la misma tabla —las cuatro columnas son de un Paciente— sino una segunda
sección de resultados. Se decide con el caso delante.

**Cada búsqueda del mostrador escribe dos filas en el Registro de acceso** —el
conjunto de Pacientes y el de Tutores—, y una búsqueda son una o dos peticiones
según lo que se pare quien escribe. Es la decisión correcta y no sale gratis: es
el mismo crecimiento que ya está anotado más arriba para las fichas —el Registro
crece con las visitas, no con los datos—, solo que aquí el multiplicador es el
teclado. Un día de mostrador con doscientas búsquedas son unas quinientas filas.
_Cuándo se paga_: con el volumen del **16**, midiendo cuánto ocupa un día de
verdad. Si molesta, lo que se toca es el retardo de la caja —250 ms hoy—, no la
regla: dejar de anotar la búsqueda sería una pantalla que enseña veinte nombres
y veinte teléfonos sin dejar rastro.

**Buscar «9» en el fichero de Tutores ya no devuelve nada**, donde antes devolvía
a todo el que tuviera un nueve en el correo. Es consecuencia de que lo escrito se
lea entero como número cuando no trae letras: por debajo del largo mínimo no hay
búsqueda que hacer. Para la caja incremental es lo que se quiere —sigue
escribiendo—, y para el fichero, donde hay que pulsar «Buscar», es un cambio de
comportamiento del **05** que nadie pidió.
_Cuándo se paga_: si alguien lo echa de menos. Nadie busca a una persona por un
dígito suelto, así que se deja hasta que aparezca la queja.

**Hay dos maneras de quitarle las tildes a un texto en el repositorio.**
`apps/busqueda.py` usa una tabla explícita de acentos porque Postgres tiene que
poder hacer lo mismo con `translate`; `apps/patients/catalogo.py` usa
`unicodedata` para decidir si una raza escrita es la del catálogo. Hacen trabajos
distintos —una compara para buscar, la otra para guardar con la ortografía
buena— y la de `catalogo` pliega más, que para su trabajo está bien.
_Cuándo se paga_: si aparece una tercera. Con dos que no se contradicen y cuyos
motivos están escritos, juntarlas sería obligar a una a hacer el trabajo de la
otra.


## La detección de coincidencias

Lo que el **12** dejó decidido a medias, y por qué se dejó así.

**La detección en vivo anota una fila del Registro por petición.** Cada respuesta
nombra de verdad la ficha que enseña, así que anotarla es lo que ADR-0004 pide y
no hay dónde recortar sin dejar de registrar una lectura real. Pero el hueco se
repinta a cada pocas teclas y la petición lleva la ficha entera (`hx-include`),
así que teclear el teléfono después de haber escrito un RUT que ya existe repite
la misma anotación una vez por tecla larga. No es ruido de otra clase que el ya
anotado más arriba —el Registro crece con las visitas, no con los datos—, pero
aquí el multiplicador vuelve a ser el teclado, como en la caja del mostrador.
Deduplicar exigiría preguntarle al Registro en cada tecla qué se anotó ya, que es
cambiar una escritura barata por una lectura en el camino crítico.
_Cuándo se paga_: con el volumen del **16**, midiendo cuánto ocupa un día de
mostrador de verdad. Si molesta, lo que se toca es el retardo o el alcance del
`hx-include`, no la regla.

**Sin JavaScript no hay detección hasta guardar.** El hueco de los avisos llega
vacío y lo llena htmx; quien navegue sin él sigue teniendo la red de siempre —el
RUT y el chip repetidos no se guardan, y el teléfono compartido avisa después de
guardar—, pero pierde justo lo que el 12 venía a dar: enterarse antes. Servir los
avisos ya pintados en la página completa no vale como remedio: en el alta no hay
nada escrito todavía, y en el formulario rechazado diría dos veces lo mismo que
ya está al lado del campo.
_Cuándo se paga_: si aparece un mostrador sin JavaScript. Hoy la caja del **11**
depende de htmx exactamente igual.

**La coincidencia del microchip no mira el estado de identificación.** Un chip
repetido avisa aunque la ficha que ya lo tiene conste `sin chip`, que es una
contradicción que el **08** dejó fuera de la base a propósito. No puede darse hoy
—el formulario no deja guardar esa combinación—, y comprobarlo sería defenderse
de un dato que solo podría entrar por el importador del **18**.
_Cuándo se paga_: en el **18**, si el importador acaba pudiendo escribir fichas
que el formulario no dejaría escribir.

## Sesiones de mostrador y segundo factor

Lo que el **13** dejó decidido a medias, y por qué se dejó así.

**El secreto TOTP se guarda en claro.** El adaptador de `allauth.mfa` cifra con
una función identidad si no se le dice otra cosa, y no se le dijo: cifrarlo con
`SECRET_KEY` guarda la llave al lado de la cerradura —quien lee la base suele
poder leer también el entorno— y cifrarlo de verdad pide una llave aparte, con su
rotación y su custodia, que hoy no existe. Quien pueda leer la tabla
`mfa_authenticator` puede generar los códigos del admin de cualquier Clínica.
_Cuándo se paga_: cuando haya gestión de secretos de despliegue — la misma que
hará falta para el correo saliente y para las claves de mensajería del **H4** —.
Entonces es `MFA_ADAPTER` con `encrypt`/`decrypt` de verdad, y una migración que
recifre lo ya guardado.

**El alta del segundo factor se hace con la contraseña recién tecleada.** Quien
robe la contraseña de un admin que todavía no configuró su segundo factor puede
configurarlo él, y desde ese momento es él quien tiene el segundo factor. Es
inherente a exigir un segundo factor que el propio Usuario da de alta: la
alternativa —entregarlo el admin anterior, o por correo— no existe hasta que
haya correo saliente. Lo que sí protege desde el primer minuto es todo lo que
venga después del alta, que es la ventana larga.
_Cuándo se paga_: con el correo saliente, cambiando el alta por una invitación
que llegue por otro canal.

**No hay códigos de recuperación.** `MFA_SUPPORTED_TYPES` es solo `totp`: los
códigos habría que entregarlos por correo —que no hay— o enseñarlos una vez en
pantalla, y una hoja de códigos junto al computador del mostrador es exactamente
lo que este ticket viene a evitar. El rescate del admin que pierde el teléfono es
`manage.py restablecer_segundo_factor`, que se ejecuta en el servidor.
_Lo que cuesta_: una Clínica sin nadie con acceso al servidor y con un solo admin
que pierde el teléfono se queda sin administración hasta que alguien entre por
ahí. Con dos admins no pasa.
_Cuándo se paga_: si aparece la queja, o con el correo saliente.

**`fido2` se instala y no se usa.** `allauth.mfa` lo importa al envolver
cualquier autenticador, aunque WebAuthn esté apagado en `MFA_SUPPORTED_TYPES`. Es
una dependencia de despliegue —con `cryptography` y `cffi` detrás— que no
ejecuta nada.
_Cuándo se paga_: no se paga. Se anota para que nadie la busque en el código
creyendo que hace algo.

**Sin JavaScript la sesión caduca sin avisar.** El aviso lo saca
`static/sesion.js` contando desde los plazos que la página trae en `data-`; sin
él, el Usuario descubre que caducó al enviar el formulario, que es lo que pasaba
antes de este ticket. Servirlo desde el servidor pediría una petición periódica
solo para preguntar cuánto queda, y esa petición renovaría el plazo que viene a
medir.
_Cuándo se paga_: si aparece un mostrador sin JavaScript. Hoy la caja del **11**
y la detección del **12** dependen de htmx exactamente igual.

**El reloj del aviso no mira la actividad del Usuario, solo las peticiones.**
Se reinicia al cargar la página, al responder htmx y al pulsar «Sigo aquí» —que
es justo cuando el servidor renueva el plazo—, y no al teclear. Es lo correcto:
el servidor tampoco cuenta las teclas. La consecuencia es que quien escribe una
Consulta larga sin enviar nada ve el aviso, que es exactamente para eso.

## Configuración de la Sede

Lo que el **14** dejó decidido a medias, y por qué se dejó así.

**Una franja no puede cruzar la medianoche.** La base exige `hasta > desde`, así
que la Sede que atiende de 20:00 a 02:00 lo declara en dos franjas, una en cada
día. Es lo que ya hace quien escribe el cartel de la puerta, y evita que «de
20:00 a 02:00» signifique dos cosas según quién lo lea. Lo que **no** se puede
declarar de ninguna manera es un día entero seguido: `TimeField` no sabe decir
24:00, así que las 24 horas se escriben de 00:00 a 23:59 y queda un minuto
muerto. Hoy no molesta a nadie —la Sede que atiende siempre lo declara con la
bandera de urgencias, no con su horario—, y en H3 la agenda no da horas a las
23:59.
_Cuándo se paga_: si aparece una Sede que atiende de verdad las veinticuatro
horas y necesita que la agenda le ofrezca ese hueco. Entonces es una bandera
`todo_el_dia` en la Franja, o guardar duraciones en vez de horas de reloj.

**Una fecha con Excepciones no mira la semana, y eso incluye la Excepción a
medio escribir.** Quien declara «el 24 de diciembre de 11:00 a 14:00» y se
equivoca al teclear la fecha cierra sin querer el día que tecleó: no se abre
«además de» su horario, se abre «en lugar de». Es la regla correcta —es lo que
significa una excepción— pero no hay ninguna pantalla que enseñe el efecto antes
de guardar.
_Cuándo se paga_: con la agenda del **H3**, que es donde el horario se ve
dibujado y el error salta a la vista solo.

**No hay historia del horario.** Una Franja se borra cuando el horario cambia, y
lo que la Sede atendía el mes pasado no queda escrito en ninguna parte. Es
deliberado —el horario es lo que la Sede hace hoy, no un hecho del pasado; los
hechos son las Consultas y esas no se tocan—, pero significa que una Cita del
H3 agendada fuera del horario de hoy no podrá explicarse mirando el horario.
_Cuándo se paga_: no se paga, salvo que alguna auditoría llegue a pedir «a qué
hora abría esta Sede el 3 de marzo». Entonces es una tabla de versiones, no un
campo más.

**Las Clínicas de derivación no se comprueban contra nada.** Nombre, teléfono y
dirección los teclea el admin, y una clínica que cerró sigue en la lista hasta
que alguien la quite. No hay forma de saberlo desde aquí: no existe un registro
público de clínicas veterinarias consultable por API.
_Cuándo se paga_: no se paga. Se anota para que nadie espere una validación que
no puede existir.

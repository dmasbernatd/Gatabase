# 08 — Microchip y estado de identificación

**What to build:** recepción registra el microchip del Paciente y ve de un golpe qué le falta al Tutor para cumplir la Ley 21.020. El chip pasa a ser una forma de encontrar al animal.

**Blocked by:** 07

**Status:** done

- [x] Número de microchip **opcional**, de 15 dígitos, validado en formato
- [x] Estado de identificación como campo propio y distinto de "tiene chip": `sin chip`, `chip implantado`, `inscrito en el Registro Nacional`
- [x] Microchip **único dentro de la Clínica**; el intento de repetirlo se rechaza con enlace a la ficha que ya lo tiene
- [x] El microchip **no** es único a nivel global ni se cruza entre Clínicas (ADR-0001). Si el mismo número existe en otra Clínica, es correcto y no se detecta
- [x] La ficha del Paciente muestra el estado de identificación de forma visible, para poder decírselo al Tutor
- [x] Test que comprueba explícitamente que dos Clínicas pueden tener el mismo número de chip sin conflicto

## Comments

**23 de agosto de 2026 — hecho.** Todas las casillas, con la batería en verde
(265 tests, 42 nuevos en `tests/test_microchip_e_identificacion.py`).

Dónde quedó cada cosa:

- **Cómo se lee un chip vive en un módulo propio** (`apps/patients/microchip.py`)
  y no en el modelo ni en el formulario. Se guarda de corrido —quince dígitos y
  nada más—, que es la única forma en que dos chips iguales se parecen entre sí;
  entra como venga —del lector de corrido, del certificado en grupos de tres, del
  carnet con puntos o guiones— y sale igual. De eso depende que «único dentro de
  la Clínica» signifique algo y que la búsqueda por chip del **11** encuentre al
  animal. Se presenta al revés, en grupos de tres, porque quince dígitos seguidos
  no se dictan por teléfono sin perder la cuenta.
- **El largo es lo único que se comprueba, y es lo único comprobable.** El ISO
  11784 con el que se implanta en Chile son quince dígitos y **no** lleva dígito
  verificador: un chip mal tecleado no se delata solo. Atrapar el dígito que se
  cayó al copiarlo es todo lo que se puede hacer desde el mostrador, y el mensaje
  dice cuántos llegaron para que se vea dónde.
- **Un chip ilegible no es un hueco.** Si en la casilla había algo y de ese algo
  no quedan quince dígitos, se rechaza en vez de guardarse vacío. Es lo que
  impide que una nota escrita ahí —«no tiene», «ilegible»— se guarde como si
  fuera un chip, o peor, como si no se hubiera escrito nada.
- **El estado de identificación es un campo aparte** (`EstadoDeIdentificacion`),
  y esa es la mitad del ticket. Tener el número apuntado **no** es estar inscrito
  en el Registro Nacional: la ley se cumple con las dos cosas, y el hueco entre
  una y otra es justo lo que recepción tiene que poder decirle al Tutor. Un test
  se lo pregunta explícitamente: guardar un número no mueve el estado.
- **El blanco significa «nadie lo ha preguntado todavía»**, y no `sin chip`. Es
  el mismo reparto que el Estado sanitario de `CONTEXT.md` —`desconocido` no es
  `vencido`— y por el mismo motivo: lo que nadie ha mirado no puede decírsele a
  un Tutor como si se hubiera comprobado. La ficha lo dice con todas sus letras
  (`identificacion_a_la_vista`), nunca con un guion, porque una casilla en blanco
  se lee como un «no tiene».
- **La única combinación imposible se rechaza, y solo esa**: un número apuntado
  con el estado en «sin chip». Las demás son estados reales del mostrador — un
  chip implantado en otra clínica cuyo número el Tutor no trae es lo más
  corriente que hay, y exigir el número ahí obligaría a inventárselo.
- **Único dentro de la Clínica lo impone la base de datos**: una
  `UniqueConstraint` parcial sobre `(clinic, microchip)` que deja fuera la cadena
  vacía, porque dos Pacientes sin chip no son el mismo animal. Y **solo** dentro
  de la Clínica (ADR-0001): el formulario compara con `los_demas()`, que nunca
  sale del tenant, así que el mismo número en otra Clínica es correcto y ni
  siquiera se ve. Hay un test por cada mitad — uno que lo pregunta a la base de
  datos y otro que registra el mismo chip en dos Clínicas.
- **El aviso de repetido lleva a la ficha que ya existe**, que es a lo que
  recepción venía casi siempre: el chip repetido no suele ser un error de
  tecleo, es el mismo animal ya registrado.
- **La ficha dice qué le falta** (`lo_que_le_falta_a_la_ley`), y depende de la
  especie porque la ley depende de la especie: la 21.020 obliga con perros y
  gatos. Reclamarle a quien trae una iguana que la inscriba sería dar un consejo
  falso desde detrás del mostrador. Qué especies obliga vive en `catalogo.py`,
  junto al catálogo cerrado, porque es lo mismo que la especie ya decide —qué
  papeleo le toca a cada animal— y así una especie nueva obliga a pasar por donde
  hay que decidirlo. Se pregunta y no se guarda, como `raza_del_catalogo`.

Tres cosas que se decidieron por el camino y no estaban en el ticket:

- **`CampoQueNormaliza` bajó a `apps/campos.py`.** Era privado de `tutors`, y el
  microchip necesitaba exactamente lo mismo: normalizar al guardar, pase lo que
  pase, para que «único por Clínica» signifique algo. Está fuera de las dos apps
  porque las dos lo necesitan y ninguna puede importar de la otra — `tutors`
  conoce a `patients` y `patients` no conoce a nadie (`CLAUDE.md`)—, y bajarlo
  ahí es lo que impide que mañana el Paciente importe algo de `tutors` para
  reaprovechar quince líneas. Qué es un RUT lo sigue decidiendo `rut.py`; qué es
  un chip, `microchip.py`. Esta era la extracción que la deuda técnica del 06
  dejaba condicionada al segundo ejemplo.
- **Nombrar al otro Paciente en el aviso queda anotado** en el Registro de
  acceso (`constancia_del_microchip_repetido`). El formulario rechazado no guardó
  nada, pero la página que vuelve dice de qué animal es ya ese chip y enlaza a su
  ficha: recepción la ha visto sin haber abierto nada, y ADR-0004 no distingue
  entre ver una ficha y ver el nombre de quien está en ella. Hay un test que
  comprueba la anotación.
- **La casilla del chip va sin autocompletado del navegador.** Lo que va ahí lo
  dicta un certificado o lo escupe un lector, nunca la memoria del navegador, y
  un chip sugerido de otra ficha es un animal confundido con otro.

Lo que **no** se hizo, a propósito:

- **No se busca por microchip todavía.** El índice `(clinic, microchip)` ya está
  puesto y `digitos_del_microchip` sabe reducir «900 123» a lo comparable, pero
  la caja que busca es del **11**, y montar antes una búsqueda propia del chip
  sería construir el trozo de pantalla que ese ticket va a sustituir.
- **No se comprueba el número contra ningún registro externo.** El Registro
  Nacional no se consulta: el estado es lo que el Tutor cuenta y recepción
  apunta, y la ficha no finge saber más que eso.
- **El estado de identificación no se deduce nunca solo.** Ni al guardar un
  número, ni al borrarlo. Es un dato que alguien preguntó, no un cálculo.

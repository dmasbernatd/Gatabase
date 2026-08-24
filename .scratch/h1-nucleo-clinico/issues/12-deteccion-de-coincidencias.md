# 12 — Detección de coincidencias al crear

**What to build:** cuando recepción va a crear un Tutor o un Paciente que probablemente ya existe, el sistema se lo muestra antes de guardar. Es la prevención barata que evita la mayoría de las fichas duplicadas, dado que la fusión se posterga deliberadamente.

**Blocked by:** 11

**Status:** done

- [x] Al escribir el teléfono de un Tutor nuevo, el sistema muestra los Tutores existentes con ese teléfono
- [x] Al escribir el RUT de un Tutor nuevo, el sistema avisa si ya existe y enlaza a la ficha
- [x] Al escribir el microchip de un Paciente nuevo, el sistema avisa si ya existe en la Clínica y enlaza a la ficha
- [x] Al crear un Paciente para un Tutor que ya tiene Pacientes, el sistema muestra los que ya tiene con nombre y especie
- [x] La coincidencia es un **aviso con enlace**, nunca un bloqueo: dos animales de la misma familia pueden llamarse parecido
- [x] La detección funciona con HTMX mientras se escribe, sin necesidad de guardar
- [x] Tests de los cuatro casos de coincidencia, y de que el aviso no impide guardar cuando el Usuario insiste


## Comments

Hecho. Cuatro coincidencias, una mecánica y **un solo sitio donde se decide a
quién se parece una ficha**: `apps/coincidencias.py`, que es lo que la deuda del
06 y del 08 dejó pendiente de decidir aquí. Un `Parecido` sabe tres cosas —por
qué campo se confunde una ficha con otra, qué se le dice a quien está escribiendo
y si además la base va a rechazarla— y cada formulario declara los suyos
(`PARECIDOS`), como ya declaraba por dónde se le busca (`POR_DONDE_SE_BUSCA`).
El módulo vive fuera de las dos apps por lo mismo que `busqueda.py` y `campos.py`:
las dos lo necesitan y ninguna puede importar de la otra.

**El aviso se escribe una vez y se lee en tres sitios.** Mientras se teclea, en
el hueco que repinta htmx; al lado del campo, cuando el formulario rechaza la
ficha; y como aviso que sobrevive a la redirección, cuando no la rechazó. Antes
había dos redacciones del mismo texto repartidas entre el formulario y la vista,
y la de la pantalla que menos se prueba habría envejecido sola. De paso salieron
sobrando los dos `enlace_a` copiados: el enlace lo compone la coincidencia, y
dónde vive su ficha lo sabe ahora el modelo (`get_absolute_url`).

**La detección en vivo no bloquea nunca, y eso no es lo mismo que decir que todo
se puede guardar.** Es la casilla que hubo que interpretar: el RUT y el microchip
son únicos dentro de la Clínica **en la base de datos** (ADR-0001, ADR-0003, y la
invariante de `CLAUDE.md`), así que la segunda ficha no cabe por mucho que se
insista, y quitar esa restricción para cumplir «nunca un bloqueo» habría sido
deshacer dos tickets. Lo que el 12 cambia es que ya no hace falta llegar a
guardar para enterarse. Donde el «insiste y guarda» sí se ejercita entero es en
lo que de verdad no bloquea: el teléfono de una familia y el Paciente de nombre
parecido, los dos con test.

**El cuarto caso no espera a que se escriba nada.** Los Pacientes de los que ese
Tutor ya responde salen en la página del alta, con nombre y especie, porque de
quién va a ser la ficha se sabe antes de teclear la primera letra —el alta cuelga
de su Tutor— y ningún campo exacto encontraría al segundo «Rocco» de la misma
casa. Salen los de Vínculo abierto, con el fallecido o el inactivo **marcado y no
escondido**, que es la regla del 09 y del 11: el animal que se está a punto de
registrar dos veces puede ser justamente el que consta inactivo.

**Se detecta también al corregir**, y el ticket solo pedía el alta. Es una ruta
más (`<pk>/coincidencias/`) y existe porque el formulario es el mismo en las dos
pantallas: sin el `pk`, corregirle una letra al apellido a un Tutor le avisaría
de que su RUT ya es suyo. Con él, una ficha no se parece a sí misma.

**Cada aviso deja constancia, y no todos los que se encuentran se anotan.** Se
anota lo que la página llegó a enseñar: en la detección en vivo, todo lo que
pinta; en el formulario rechazado, solo lo que impidió guardar, porque el hueco
de los avisos vuelve vacío y el teléfono compartido no se nombra ahí. Lo pilló la
revisión —anotaba de más— y ahora hay un test que falla si se vuelve a anotar
todo. La regla de la caja del mostrador —anotar el conjunto y no cada resultado—
no se aplica aquí a propósito: esto no lista a nadie de paso, nombra exactamente
la ficha que recepción está a punto de duplicar, y solo cuando el dato tecleado
está entero.

Lo que queda anotado en `deuda-tecnica.md`: la detección en vivo anota una fila
por petición, así que teclear el teléfono después del RUT repite la misma
anotación varias veces; y sin JavaScript no hay detección hasta guardar.

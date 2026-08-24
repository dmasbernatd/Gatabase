# 07 — Paciente, catálogos de especie y raza, y vínculo con Tutores

**What to build:** recepción registra el animal y lo vincula a quien responde por él. A partir de aquí el sistema sabe de qué Paciente habla un Tutor cuando llama.

**Blocked by:** 04, 05

**Status:** done

- [x] Paciente con nombre, especie, raza, sexo, fecha de nacimiento, color y observaciones
- [x] Catálogo de **especies cerrado**: de la especie dependen protocolos y formularios, así que no admite texto libre
- [x] Catálogo de **razas por especie** con autocompletado, `mestizo` como entrada de primera clase, y opción `otra` con texto libre
- [x] Vínculo Tutor–Paciente de muchos a muchos: un Paciente puede tener varios Tutores y un Tutor varios Pacientes
- [x] Un Tutor del Paciente marcado como **responsable**; solo uno a la vez
- [x] Desde la ficha del Tutor se ven sus Pacientes, y desde la del Paciente sus Tutores
- [x] La ficha de Paciente y el acceso a ella quedan en el Registro de acceso
- [x] Aislamiento por Clínica verificado por HTTP para Paciente y para el vínculo
- [x] Los datos clínicos del Paciente son independientes de los datos personales del Tutor (ADR-0004)

## Comments

**23 de agosto de 2026 — hecho.** Todas las casillas, con la batería en verde
(222 tests, 45 nuevos).

Dónde quedó cada cosa:

- **El Paciente** (`apps/patients/models.py`) guarda lo del animal y nada de su
  Tutor. Ni un campo copiado ni una clave ajena: quién responde por él es una
  tabla aparte. Es lo que hace posible el ticket 20 — anonimizar al Tutor sin
  tocar la Historia clínica—, y hay dos tests que lo sostienen: uno estructural y
  otro que vacía los datos personales del Tutor y comprueba que la ficha del
  animal sigue entera y sigue sabiendo quién responde.
- **Los dos catálogos viven juntos y tienen reglas opuestas**
  (`apps/patients/catalogo.py`). La especie es cerrada y está en código, no en
  una tabla: de ella dependen protocolos y formularios, así que atender una
  especie nueva tiene que obligar a pasar por el sitio donde después habrá que
  decidir qué protocolo le toca. La raza sugiere y no manda: se ofrece con una
  `<datalist>` y lo que no está en la lista se escribe igual — esa es la opción
  «otra», y no hace falta que sea un valor mágico. Lo escrito se compara sin
  tildes ni mayúsculas contra el catálogo de su especie, así que «bulldog
  frances» se guarda como «Bulldog Francés» y el recuento sigue valiendo.
  `Paciente.raza_del_catalogo` separa una raza que cuenta de una respuesta libre,
  y se pregunta en vez de guardarse: el día que una raza entre en el catálogo,
  las fichas que ya la tenían escrita cuentan.
- **`mestizo` es la primera entrada** del perro, el gato y el conejo, que es
  donde significa algo. En Chile es el caso más frecuente, no la excepción.
- **El Vínculo** (`apps/tutors/models.py`) es el muchos-a-muchos con algo que
  decir: cuál de los Tutores es el responsable. Vive en `tutors` y no en
  `patients` para que la dependencia entre las dos apps vaya en un solo sentido;
  queda anotado en `CLAUDE.md`. Que el responsable sea **uno solo** lo impone una
  `UniqueConstraint` parcial sobre `(paciente)` con `responsable=True`: no
  depende de que nadie abra dos pestañas, y hay un test que se lo pregunta a la
  base de datos.
- **Un Paciente no nace suelto.** Se registra desde la ficha del Tutor que lo
  trae (`patients:crear` cuelga de su identificador) y ese Tutor queda como
  responsable. Es como llega un animal al mostrador, y ahorra el estado
  intermedio de un Paciente del que no responde nadie. La regla vive en
  `Tutor.se_hace_cargo_de` y no en la vista: el primero que aparece se queda con
  el cargo aunque nadie lo haya pedido.
- **Las dos fichas se ven la una a la otra**, y las dos anotan lo que enseñan.
  La del Paciente nombra a sus Tutores —cada nombre es un dato personal— y la del
  Tutor nombra a sus Pacientes, que la ley protege igual porque por ellos se
  llega a él (ADR-0004).

Tres cosas que se decidieron por el camino y no estaban en el ticket:

- **`anotando`** (`apps/audit/registro.py`): devuelve la respuesta ya compuesta y
  anota lo que enseña. Nació porque estas páginas sirven más de una cosa a la vez
  y la regla del Registro —anotar **después** de tener la respuesta— se estaba
  escribiendo a mano en cinco sitios, con una variable intermedia de por medio.
  Ahora el orden lo impone Python.
- **Sumar un Tutor tiene página propia** (`patients:vincular`) en vez de un
  desplegable en la ficha. El desplegable enseña el nombre de todos los Tutores
  de la Clínica, y eso es una lectura del conjunto que no tiene por qué quedar
  anotada cada vez que alguien abre una ficha de Paciente.
- **La fecha de nacimiento no puede ser futura.** Es el error de tecleo más fácil
  de cometer en una casilla de fecha y el más difícil de ver después, cuando lo
  único raro es una edad imposible en una ficha.

Lo que **no** se hizo, a propósito:

- **No hay listado de Pacientes.** A un Paciente se llega hoy por la ficha de su
  Tutor. La caja única que busca por nombre, por teléfono del Tutor y por
  microchip es del **11**, y montar antes un listado propio sería construir la
  pantalla que ese ticket va a sustituir.
- **No se puede cerrar un Vínculo.** Un Tutor se sube y el cargo se pasa, pero
  «este ya no responde por este Paciente, desde esta fecha» es del **10**, que es
  quien trae el cambio de Tutor con su histórico.
- **La especie no tiene entrada «otra».** Cerrado es cerrado: si llega un animal
  que no está, la respuesta es una línea en `catalogo.py` y la decisión de qué
  protocolo le toca, no una casilla de texto que deje esa decisión sin tomar.

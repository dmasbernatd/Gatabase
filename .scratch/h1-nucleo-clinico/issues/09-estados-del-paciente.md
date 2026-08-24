# 09 — Estados del Paciente

**What to build:** cuando un Paciente muere o deja de venir, el sistema lo refleja sin borrar nada. Evita el peor error posible de cara al Tutor: tratar como activo a un animal que ya no está.

**Blocked by:** 07

**Status:** done

- [x] Estados `activo`, `inactivo` y `fallecido`, y fecha en el caso de fallecido
- [x] Un Paciente fallecido conserva **toda** su información en solo lectura; nunca se borra
- [x] La ficha de un Paciente fallecido lo indica de forma inequívoca en la propia página
- [x] Los listados y las búsquedas por defecto muestran solo activos, con filtro para ver el resto
- [x] Marcar como fallecido bloquea cualquier alta futura de Cita (la comprobación se ejercita en H3; aquí queda la regla en el modelo)
- [x] `inactivo` es un estado distinto y reversible, para el animal que dejó de venir sin que se sepa qué pasó
- [x] El cambio de estado queda en el Registro de acceso

## Comments

**23 de agosto de 2026 — hecho.** Todas las casillas, con la batería en verde
(291 tests, 26 nuevos en `tests/test_estados_del_paciente.py`).

Dónde quedó cada cosa:

- **El estado vive en un módulo propio** (`apps/patients/estados.py`), junto con
  lo que el estado decide: qué enseña una lista por defecto. Es el mismo reparto
  que `catalogo.py` —la `Especie` no está en `models.py`— y por el mismo motivo:
  lo que hay que leer para entender la regla cabe en un archivo.
- **Es un estado, no un borrado, y esa es toda la decisión.** La Historia clínica
  es del animal (ADR-0001) y hace falta después: para el Tutor que pregunta qué
  se le puso, para el veterinario que atiende a otro animal de la misma casa,
  para la Ley 21.719 cuando alguien reclame qué se guardó de él. Hay un test que
  lo comprueba de la única forma en que se puede comprobar: la ficha y el Vínculo
  siguen enteros después de marcar el fallecimiento.
- **`fallecido` e `inactivo` son dos porque no son lo mismo.** El primero es un
  hecho del mundo y cierra la ficha; el segundo es lo que la clínica sabe cuando
  no sabe nada —dejó de venir y nadie contó qué pasó— y no cierra nada. Es el
  mismo reparto que el Estado sanitario hace entre `desconocido` y `vencido`:
  dejar de saber no es saber que no. Por eso `inactivo` **sí** admite Citas: que
  un animal lleve dos años sin venir es justamente la razón de citarlo.
- **La fecha de fallecimiento es opcional; la contraria, imposible.** El Tutor
  avisa a veces meses después y no siempre recuerda el día, y exigirla sería
  obligar a inventársela — un fallecido sin fecha es «murió, no consta cuándo»,
  que es verdad. Lo que no puede existir es una fecha de muerte en un animal que
  no consta muerto, y eso no depende de que nadie se acuerde: lo rechaza una
  `CheckConstraint` de la base de datos, con un test que se lo pregunta a ella.
- **Limpiar la fecha al salir de `fallecido` vive en el modelo**
  (`Paciente.cambiar_de_estado`), no en la vista, por lo mismo que
  `hacer_responsable` vive en el Vínculo: es la coherencia de la ficha, no el
  guion de una pantalla. Sin eso, deshacer un fallecimiento marcado por error
  reventaría contra la restricción de arriba, en la cara de recepción.
- **Solo lectura de verdad.** La vista de corregir desvía a la ficha cuando el
  Paciente consta fallecido, y no basta con esconder el enlace: hay un test que
  entra por la URL a pelo, como quien tenía la pestaña abierta de antes.
- **Marcar al animal que no era se puede deshacer.** Es la única excepción a lo
  anterior, y es deliberada: es un error fácil de cometer y grave, y volver
  atrás no puede depender de tocar la base de datos a mano. El cambio de estado
  tiene página propia (`patients:estado`), separada de la corrección de la ficha
  porque no es un dato mal escrito sino un hecho que cambió — y juntarlos
  pondría el fallecimiento a un descuido de distancia del formulario que se abre
  para arreglar una letra del nombre.
- **La ficha lo dice arriba y con todas sus letras**, antes que ningún otro dato
  (`estado_a_la_vista`, con la fecha si la hay). Confundir a un animal muerto con
  uno vivo no puede depender de que alguien repare en una casilla más de una
  lista.
- **La regla de la Cita queda en el Paciente** (`admite_citas` y
  `por_que_no_admite_citas`), que es donde tiene que estar: es un hecho del
  animal, y `records` y la agenda no pueden preguntar al revés (`CLAUDE.md`).
  Se devuelve el motivo y no un `False` a secas para que H3, al tropezar con la
  regla, no tenga que volver a deducir qué decir.
- **La lista de la ficha del Tutor enseña por defecto a los activos**, con
  filtro para pedir el resto (`FiltroPorEstado`, con la misma tolerancia que el
  `Orden` del listado de Tutores: un valor que no se reconoce responde con lo de
  siempre). Y el que ya no está sale **marcado** siempre que se enseñe, porque en
  «Todos» comparte lista con los vivos y ahí el nombre solo no dice a cuál se
  puede citar.
- **El Registro no anota lo que no se sirvió.** Un Paciente filtrado por el
  estado no se enseñó, así que no consta su lectura; hay un test que lo fija,
  porque es la regla que sostiene al Registro (ADR-0004). El cambio de estado sí
  consta como modificación: a quién se dio por muerto, quién lo hizo y cuándo es
  justo lo que habrá que poder demostrar si alguien reclama.

Dos cosas que se decidieron por el camino y no estaban en el ticket:

- **La comprobación de fecha futura se extrajo** (`sin_fechas_futuras`, en
  `apps/patients/forms.py`). Ya eran dos: el nacimiento y el fallecimiento. Es el
  mismo error de tecleo —el año en curso por el anterior— y el mismo remedio, y
  la mitad de arriba del par pedía además la de abajo: **nadie muere antes de
  nacer**, que es el mismo error hacia atrás y solo se puede comprobar mirando
  las dos fechas de la ficha a la vez.
- **`CONTEXT.md` gana el término «Estado del Paciente»**, con `baja`,
  `eliminado` y `archivado` en la lista de lo que hay que evitar. No es
  decoración: «dar de baja» es exactamente la palabra que empuja a borrar.

Lo que **no** se hizo, a propósito:

- **No se filtra por estado en el manager.** `Paciente.objects` sigue viendo a
  todos los de la Clínica, y el filtro es de cada lista. Al revés escondería a
  los fallecidos también del importador, de la exportación del **19** y de los
  derechos del titular del **20**, que es justo donde tienen que aparecer. Y
  redeclarar un manager en `Paciente` movería cuál es el `_default_manager` —el
  primero declarado gana—, que es la garantía de ADR-0003: no se toca por una
  comodidad de listado.
- **La búsqueda no se tocó porque no existe todavía**: es del **11**, y ahí la
  casilla del ticket 09 y la del 11 dicen cosas distintas a propósito. Una lista
  de trabajo esconde a los que ya no están; la caja de búsqueda los **marca** sin
  esconderlos, porque a un fallecido a veces se le busca precisamente a él y
  quien escribe su nombre ya sabe a quién busca. `FiltroPorEstado` está donde el
  **11** lo va a encontrar.
- **No se cierra ningún Vínculo al marcar el fallecimiento.** Que un Paciente
  fallecido o inactivo pueda quedarse sin Tutor responsable es una casilla del
  **10**, y adelantarla aquí sería escribir media regla sin la otra media.
- **No se añadió índice por estado.** El filtro de hoy recorre los Vínculos de un
  Tutor —unos pocos—, no la tabla de Pacientes. Poner un índice antes de que
  exista la consulta que lo usaría sería optimizar a ciegas; se mira en el **11**
  con el volumen del **16** delante.

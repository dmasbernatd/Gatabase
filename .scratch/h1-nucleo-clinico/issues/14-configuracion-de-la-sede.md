# 14 — Configuración de la Sede: Horario de atención y Clínicas de derivación

**What to build:** el admin de la Clínica declara cuándo atiende su Sede, si atiende urgencias, y a qué clínicas derivar cuando no puede. Es configuración que en H1 no hace nada visible, pero de la que dependen la agenda (H3) y la Autorespuesta (H4).

**Blocked by:** 02

**Status:** done

- [x] Horario semanal por Sede, con varias franjas por día
- [x] **Excepciones por fecha**, para festivos y cierres por vacaciones. Deliberadamente no se usa un calendario automático de festivos: los festivos chilenos son irregulares y un cierre por vacaciones no está en ninguna lista
- [x] Bandera de si la Sede atiende urgencias, y teléfono de urgencias propio cuando aplica
- [x] Catálogo de **Clínicas de derivación** con nombre, teléfono y dirección, que mantiene el admin de la Clínica, porque la red de clínicas socias es conocimiento local y cambia
- [x] Una función consultable que responde si una Sede está en horario en un instante dado, con sus excepciones aplicadas
- [x] Tests de la función en horario, fuera de horario, en el borde exacto de una franja, y en una fecha de excepción
- [x] Test en las semanas del cambio de hora de septiembre y de abril, porque el horario se declara en hora local

## Comments

Implementado en `apps/tenancy`. Tres modelos nuevos —`FranjaDeAtencion`,
`ExcepcionDeAtencion` y `ClinicaDeDerivacion`— y dos campos más en la Sede.
La regla vive aparte de las tablas, en `apps/tenancy/horarios.py`, como el
Estado del Paciente vive en `estados.py`.

- **`esta_en_horario(sede, instante)` recibe un instante, no una hora de reloj**,
  y lo traduce a Santiago una sola vez, dentro. Es lo que hace que el horario
  declarado en hora local siga significando lo mismo los dos domingos del año en
  que el reloj se mueve. El test que lo sostiene no compara offsets: pregunta por
  las 12:00 UTC del domingo del cambio y del domingo anterior, que son las 09:00
  y las 08:00 en Santiago, y espera abierto y cerrado. Sin la traducción, las dos
  darían lo mismo.
- **La franja incluye su hora de apertura y no la de cierre.** Es lo que permite
  declarar mañana y tarde sin que las 13:00 caigan en las dos, y es lo que
  significa «cierro a las 13:00» dicho por quien atiende. Los dos bordes tienen
  test, y el formulario deja pegar dos franjas contiguas por lo mismo.
- **Una fecha con Excepciones no mira la semana en absoluto.** Cerrar y abrir
  distinto son el mismo hecho con más o menos datos: sin horas, la Sede cierra;
  con horas, atiende esas. Así el festivo y la víspera de Navidad no son dos
  modelos ni dos banderas.
- **Sin calendario automático de festivos**, como pedía el ticket, y el motivo
  quedó escrito en `horarios.py` para que nadie lo «arregle»: los feriados
  chilenos se mueven, los hay regionales, y un cierre por vacaciones no está en
  ninguna lista.
- **El teléfono se mudó de app.** La Sede de urgencias necesita uno normalizado y
  `tenancy` no puede importar de `tutors` —sería un ciclo: `tutors` importa el
  aislamiento de `tenancy`—, así que la regla bajó a `apps/telefono.py` y el
  campo a `apps/campos.py`, que ya existía por el mismo motivo. `tutors/campos.py`
  sigue nombrando `CampoDeTelefono` porque la migración `0003` lo llama por ese
  camino, y una migración aplicada no se reescribe.
- **La Clínica de derivación cuelga de la Clínica y no de la Sede**: el trato con
  la clínica de al lado lo tiene la organización, y las Sedes ya comparten
  Tutores y Pacientes. La Franja y la Excepción sí son de la Sede, que es lo que
  tiene puerta y horario.
- **Lo que el formulario rechaza con palabras, la base lo rechaza igual**: franja
  invertida, media excepción y teléfono de urgencias en una Sede que no atiende
  urgencias son tres `CheckConstraint`. Al horario también van a escribir el
  importador y los datos mock, donde no hay formulario que se acuerde de nada.
- Tests en `tests/test_configuracion_de_la_sede.py`: la mitad de arriba pregunta a
  la función y la de abajo entra por HTTP como el admin. Se comprobó en rojo
  invirtiendo cinco piezas —la traducción a hora local (caen doce), el borde de la
  franja, las Excepciones, la comprobación de solapes y `solo_admin`—, y cada una
  tumbó los suyos.

Deuda consciente, anotada en `deuda-tecnica.md`: una franja no cruza la
medianoche ni cubre el día entero, una Excepción con la fecha mal tecleada cierra
un día sin avisar, el horario no guarda historia, y la lista de derivación no se
comprueba contra nada.

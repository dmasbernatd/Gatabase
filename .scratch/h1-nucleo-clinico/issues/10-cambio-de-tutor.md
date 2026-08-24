# 10 — Cambio de Tutor de un Paciente

**What to build:** un animal cambia de dueño y el sistema lo refleja sin perder el rastro de quién lo trajo antes. La información del animal sigue al animal.

**Blocked by:** 07

**Status:** done

- [x] Cerrar el vínculo de un Tutor con un Paciente indicando fecha, en lugar de eliminarlo
- [x] Vincular un Tutor nuevo y marcarlo como responsable en el mismo flujo
- [x] La ficha del Paciente muestra los Tutores actuales y los anteriores con sus fechas
- [x] La ficha del Tutor anterior sigue mostrando que ese Paciente fue suyo, y hasta cuándo
- [x] Todo lo registrado sobre el Paciente permanece asociado al Paciente, no al Tutor (ADR-0001)
- [x] Un Paciente no puede quedarse sin ningún Tutor responsable, salvo que esté `inactivo` o `fallecido`
- [x] La operación queda en el Registro de acceso


## Comments

Hecho. Un Vínculo **se cierra con fecha y no se borra**, y de ahí sale todo lo
demás. Borrar la fila dejaría una Historia clínica sin nadie detrás de la mitad
de sus Consultas —y la Historia es del animal (ADR-0001)—, así que «cerrado»
dice lo único que hay que decir: fue verdad hasta ese día. Es una fecha y no una
marca de sí o no porque lo que hará falta después es justamente el día: a quién
se le pregunta por lo que se le hizo al animal en marzo depende de quién lo
tenía en marzo.

- **El cambio de manos es una sola operación**, y por eso tiene módulo propio
  (`apps/tutors/traspaso.py`) y una sola pantalla. Cerrar el Vínculo de quien lo
  tenía y abrir el de quien lo tiene por separado deja, entre una cosa y otra, un
  animal activo del que no responde nadie: una ficha que no dice a quién llamar.
  Van juntas y en la misma transacción — o cambia de manos o no cambia nada. Se
  abre primero el nuevo, que suelta al anterior del cargo al marcarse, y así no
  hay ningún instante con dos responsables ni con ninguno.
- **La regla de que nadie se quede sin responsable tiene dos puertas**, y las dos
  están cerradas: el Vínculo del responsable de un Paciente activo no se cierra
  (`Vinculo.por_que_no_se_puede_cerrar`), y un Paciente sin responsable no vuelve
  a `activo`. La segunda no estaba en el ticket y hace falta: sin ella el
  escenario «se traspasó estando inactivo y después volvió» entra por detrás. La
  excepción del ticket se respeta entera — un inactivo o un fallecido sí puede
  quedarse sin nadie, porque no hay a quién llamar y exigir un responsable
  obligaría a dejar puesto a un Tutor que no tiene nada que ver.
- **Tres restricciones de base de datos, no tres cuidados.** Un Vínculo cerrado
  no puede ser el responsable; el par Tutor–Paciente es único solo entre los
  **abiertos**; el responsable sigue siendo uno solo. La segunda es la que
  permite que un animal vuelva a su Tutor de siempre: son dos tramos con sus dos
  fechas, no una corrección del primero.
- **Traspasar a quien ya era uno de sus Tutores no abre ningún Vínculo nuevo.**
  Una pareja que se separa y uno de los dos se queda con el animal es exactamente
  eso: al que ya tenía se le pasa el cargo. `se_hace_cargo_de` busca antes de
  crear, y solo entre los abiertos.
- **Las dos fichas cuentan las dos mitades.** La del Paciente enseña quién
  responde hoy y quién respondía antes, con la fecha; la del Tutor, de qué
  animales se hace cargo y cuáles fueron suyos y hasta cuándo. Los de antes no se
  mezclan con los de ahora: quien atiende necesita ver de un vistazo a cuál puede
  citar.
- **Todo consta** (ADR-0004): el traspaso como modificación de los dos Tutores y
  del Paciente —a quién se le dejó de cobrar y a quién se le empezó a cobrar es
  lo que habrá que demostrar si alguien reclama— y los nombres que las páginas
  enseñan como lecturas, incluidos los de los Tutores de antes: un nombre servido
  es una lectura aunque el Vínculo esté cerrado.

Dos cosas que se decidieron por el camino:

- **`quienes_responden` pasó a ser presente de verdad**: solo los Vínculos
  abiertos. Los cerrados salen por `quienes_respondieron`. El nombre ya decía
  eso; ahora la consulta también, y con ello el desplegable de «Sumar un Tutor»
  vuelve a ofrecer a quien tuvo al animal y ya no lo tiene.
- **Un test del 09 cambió de escenario**: el fallecido que se desmarca por error
  ahora tiene Tutor, que es como es un fallecido de verdad —marcar la muerte no
  cierra ningún Vínculo, lo decidió el 09—. Sin esa línea el test probaría otra
  cosa: un Paciente sin nadie detrás, que es justo lo que ya no vuelve a activo.

Lo que **no** se hizo, a propósito:

- **No se cierra ningún Vínculo solo porque el Paciente muera.** Sigue siendo lo
  que decidió el 09. Que un fallecido *pueda* quedarse sin responsable no es que
  deba: quién lo traía cuando murió es un dato, y borrarlo por rutina sería
  perderlo.
- **El traspaso no crea Tutores.** Se elige entre los de la Clínica, y quien
  llega nuevo se registra antes desde el fichero de Tutores. Meter un alta dentro
  de esta pantalla mezclaría dos cosas que se validan distinto —el RUT repetido
  del 06, entre otras— dentro de una operación que ya es doble.
- **No se toca la ficha del animal en absoluto.** Es la casilla del ticket sobre
  ADR-0001 y se comprueba con un test: después del cambio de manos el Paciente es
  el mismo, con su microchip y su ficha enteros, y no hay una ficha nueva.
- **No se añadió índice por `fecha_de_cierre`.** Las consultas de hoy recorren
  los Vínculos de un Paciente o de un Tutor —unos pocos—, no la tabla entera.
  Igual que en el 09: se mira en el 11 con el volumen del 16 delante.

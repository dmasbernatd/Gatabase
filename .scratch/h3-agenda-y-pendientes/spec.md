# H3 — Agenda, Aplicaciones y bandeja de Pendientes

Status: ready-for-agent

## Problem Statement

Las horas se apuntan en un cuaderno en el mostrador. Nadie sabe cuántos Tutores no aparecen, así que la clínica no puede reaccionar a las inasistencias, que es dinero perdido en una agenda que parecía llena. Cuando un Tutor llama para cambiar la hora, hay que tachar y reescribir, y el veterinario del box no ve el cambio.

Y la salud preventiva se pierde entera: nadie sabe qué Pacientes tienen el refuerzo antirrábico vencido. La antirrábica es la única vacuna obligatoria por ley en Chile, su periodicidad depende del fabricante de la vacuna aplicada, y la clínica no tiene forma de listar a quién le toca.

## Solution

Una agenda por Sede donde se reserva el tiempo de un veterinario, con estados que hacen visible la inasistencia. Un registro de Aplicaciones de vacunas y antiparasitarios que calcula la próxima fecha al aplicar. Y una bandeja interna de Pendientes por Sede, que recepción trabaja llamando por teléfono y despacha registrando el resultado del contacto.

Al terminar H3 el sistema genera retorno visible: huecos que se recuperan y refuerzos que no se pierden.

## User Stories

1. Como recepción, quiero ver la agenda del día de mi Sede, para saber qué viene.
2. Como recepción, quiero ver la agenda de la semana, para ofrecer horas por teléfono.
3. Como recepción, quiero crear una Cita eligiendo Paciente, veterinario, fecha y tipo, para reservar el tiempo.
4. Como recepción, quiero que la duración se proponga sola según el tipo de Cita, para no calcular a mano que una vacuna son 15 minutos y una cirugía 90.
5. Como recepción, quiero poder ajustar la duración propuesta, porque el caso concreto manda.
6. Como recepción, quiero que el sistema no me deje reservar dos Citas para el mismo veterinario a la misma hora, para no dejar a dos Tutores esperando.
7. Como recepción, quiero registrar una Cita para un Paciente que llegó sin reserva, marcada como espontánea, para que el día refleje la realidad.
8. Como recepción, quiero mover una Cita a otra hora o a otro veterinario, para atender un cambio por teléfono.
9. Como recepción, quiero cancelar una Cita indicando si la canceló la clínica o el Tutor, para saber a quién se le cayó.
10. Como recepción, quiero marcar que un Tutor confirmó su asistencia, para saber con qué cuento.
11. Como recepción, quiero marcar que un Paciente ya está en sala, para que el veterinario sepa que puede llamarlo.
12. Como recepción, quiero marcar una Cita como no asistió, para que quede constancia.
13. Como recepción, quiero ver en la ficha del Tutor cuántas veces no asistió, porque es un dato del Tutor y no del Paciente.
14. Como recepción, quiero que la Cita registre de dónde vino (recepción, teléfono o canal externo), para saber en seis meses qué vía funciona.
15. Como recepción, quiero que la agenda muestre la hora local de Santiago siempre correcta, incluso en las semanas del cambio de hora, para que nadie llegue con una hora de diferencia.
16. Como recepción, quiero que el Horario de atención y las excepciones por fecha de mi Sede se reflejen en la agenda, para no ofrecer una hora en un festivo.
17. Como recepción, quiero que el sistema no me deje agendar a un Paciente fallecido, para no cometer un error doloroso.
18. Como veterinario, quiero ver mi propia agenda del día, para organizarme.
19. Como veterinario, quiero abrir la Consulta desde la Cita, para no buscar el Paciente otra vez.
20. Como admin de Clínica, quiero definir los tipos de Cita con su duración por defecto, para adaptar el sistema a cómo trabaja mi clínica.
21. Como admin de Clínica, quiero mantener un catálogo de Productos sanitarios (vacunas y antiparasitarios) con su periodicidad de refuerzo según el fabricante, porque la ley remite a lo que indica el fabricante.
22. Como veterinario, quiero registrar una Aplicación indicando producto, lote, fecha y que fui yo quien la aplicó, porque el lote es lo que necesito si hay un retiro de lote o una reacción adversa.
23. Como veterinario, quiero que la próxima fecha del refuerzo se calcule al aplicar y quede guardada, para que un cambio futuro del fabricante no reescriba el pasado.
24. Como veterinario, quiero emitir el certificado de vacunación antirrábica con mis datos, porque sin certificado de un médico veterinario la vacunación no tiene validez legal.
25. Como veterinario, quiero ver el historial de Aplicaciones de un Paciente, para saber qué le falta.
26. Como recepción, quiero ver el Estado sanitario de un Paciente como al día, vencido o desconocido, para decirle al Tutor qué le falta.
27. Como recepción, quiero que un Paciente rescatado del que no se sabe nada aparezca como desconocido y no como vencido, porque no es lo mismo y se atiende distinto.
28. Como recepción, quiero una bandeja de Pendientes de mi Sede, para saber a quién hay que llamar hoy.
29. Como recepción, quiero que un refuerzo vencido genere un Pendiente, para no perder al Paciente.
30. Como recepción, quiero que un control posoperatorio indicado en una Consulta genere un Pendiente, para hacer seguimiento del caso.
31. Como recepción, quiero que un Estado sanitario desconocido genere un Pendiente de revisión y no un aviso de refuerzo, porque no sé qué le toca.
32. Como recepción, quiero cerrar un Pendiente registrando el resultado del contacto (contactado, no contesta, reagendado, descartado), para que la bandeja siga siendo creíble.
33. Como recepción, quiero que un Pendiente no se pueda cerrar con un simple visto, porque entonces nadie confía en la bandeja y volvemos al cuaderno.
34. Como recepción, quiero que los Pendientes de un Paciente fallecido desaparezcan de inmediato, para no llamar a un Tutor a ofrecerle la vacuna de su animal muerto.
35. Como recepción, quiero enviar el Aviso de cita al Tutor con un enlace de WhatsApp preparado de un clic, para confirmar asistencia sin depender de ninguna integración.
36. Como recepción, quiero que quede registrado que envié el Aviso de cita y cuándo, para no enviarlo dos veces.
37. Como recepción, quiero que el sistema respete el Consentimiento de contacto del Tutor, para no escribir a quien pidió que no lo hiciéramos.
38. Como admin de Clínica, quiero ver cuántas Citas terminaron en no asistió por mes, para saber si el problema mejora.

## Implementation Decisions

- **Apps nuevas**: `scheduling` (Cita, tipos de Cita, servicio de disponibilidad), `preventive` (Producto sanitario, Aplicación, Estado sanitario, certificado), `notices` (Pendiente, resultado de contacto, Aviso de cita, cola de envío) — se llama `notices` por el Aviso de cita, no `reminders`, porque `CONTEXT.md` evita "recordatorio" tanto para el Pendiente como para el Aviso.
- **Regla de dependencias**: `records` no importa de `scheduling` (ADR de H2). La Cita puede apuntar a la Consulta que generó; nunca al revés.
- **Recurso reservable**: en H3 se reserva el **veterinario**. El modelo queda abierto a recursos adicionales (box, pabellón) sin implementarlos.
- **Servicio de disponibilidad**: el cálculo de huecos libres vive en un **módulo de servicio con firma propia y tests propios**, nunca dentro de una vista ni de una plantilla. Recepción lo necesita de todas formas, y es la pieza que un futuro flujo automático de confirmación reutilizaría tal cual. Recibe Sede, veterinario, tipo de Cita y rango de fechas.
- **Estados de Cita**: `agendada`, `confirmada`, `en sala`, `atendida`, `no asistió`, `cancelada`. La cancelación distingue autor (`clínica` o `tutor`). `confirmada_por` admite el valor `tutor` desde ya, aunque en H3 lo registre recepción a mano.
- **Origen de Cita**: campo `origen` (`recepción`, `teléfono`, `canal externo`) desde H3, para poder medir después si un canal automático aporta.
- **Bandera reservada**: los tipos de Cita llevan `agendable por el Tutor`, aunque en H3 nadie la lea. Coste cero hoy; impide que un flujo futuro pueda agendar una cirugía.
- **Zona horaria**: todo en UTC en base de datos, presentado en `America/Santiago`. La agenda debe ser correcta en las semanas de cambio de hora.
- **Horario de atención**: horario semanal por Sede más **excepciones por fecha**, en lugar de un calendario automático de festivos, porque los festivos chilenos son irregulares y un cierre por vacaciones no está en ninguna lista.
- **Aplicación y Producto sanitario**: entidad `Aplicación` genérica para vacuna y antiparasitario, con producto, lote, fecha, veterinario y `próxima_fecha`. La `próxima_fecha` **se calcula al aplicar y se persiste**, nunca se deriva en tiempo de consulta.
- **Cálculo de próxima fecha**: función pura en su propio módulo, con la periodicidad tomada del Producto sanitario. Regla legal de referencia: primera dosis antirrábica cumplidos los dos meses de edad, primer refuerzo al año, después según la periodicidad del fabricante.
- **Estado sanitario**: `al día`, `vencido`, `desconocido`. `desconocido` genera Pendiente de revisión, **no** aviso de refuerzo.
- **Pendiente** (ADR-0005): interno, por Sede, visible a recepción y admin. **Nunca** produce un mensaje al Tutor por sí solo. Se cierra con un resultado de contacto obligatorio, con fecha y Usuario.
- **Aviso de cita**: único mensaje saliente al Tutor. En H3 se despacha con un enlace `wa.me` preparado, que no necesita permiso de nadie, y el envío se registra. La cola de envío es la abstracción; el canal es un adaptador (H4 enchufa la Cloud API detrás de la misma cola).
- **Token opaco**: cada Aviso de cita lleva un token opaco y caducable que identifica la Cita. En H3 no se usa para nada. Es lo que permitirá, en el futuro, aceptar una confirmación sin identificar a una persona por su número de teléfono (ADR-0005).
- **Consentimiento de contacto**: se comprueba antes de preparar cualquier Aviso de cita.
- **Sin Celery**: los Pendientes se generan con un comando de gestión programado. Una clínica de una sede no justifica una cola de tareas.

## Testing Decisions

- La costura principal sigue siendo la **petición HTTP con el cliente de test de Django**. Se añaden dos costuras de función, porque los casos que importan son impracticables por HTTP:
  - **Servicio de disponibilidad**: se prueba directamente por su firma.
  - **Cálculo de próxima fecha**: función pura, se prueba directamente.
- **Suite obligatoria — agenda y cambio de hora**: Citas que cruzan los cambios de hora de septiembre y de abril en `America/Santiago`, comprobando la hora que ve el Usuario y la duración efectiva. Es el bug silencioso que hace llegar a un Tutor con una hora de diferencia.
- **Suite obligatoria — próxima dosis**: un test por tipo de periodicidad de fabricante, más el caso de la primera dosis a los dos meses y el primer refuerzo al año.
- **Doble reserva**: test que intenta reservar el mismo veterinario a la misma hora y espera rechazo, incluidas dos peticiones concurrentes.
- Tests de estados de Cita por HTTP: transiciones válidas e inválidas, cancelación con autor, `no asistió` reflejado en la ficha del Tutor.
- Tests de que un Paciente fallecido no admite Cita y sus Pendientes desaparecen de inmediato.
- Tests de Pendientes: un refuerzo vencido los genera, un Estado sanitario desconocido genera revisión y no aviso de refuerzo, y un Pendiente no se cierra sin resultado de contacto.
- Test de que no se prepara ningún Aviso de cita para un Tutor sin Consentimiento de contacto.
- Prior art: patrones de H1 y H2 (cliente autenticado, factories por Clínica, aserciones de aislamiento y de Registro de acceso).

## Out of Scope

- Conversaciones entrantes, Autorespuesta y Cloud API de WhatsApp (H4).
- Interpretación automática de la respuesta del Tutor: recepción marca la Confirmación a mano, porque las respuestas reales son ambiguas ("el jueves no puedo, mejor el viernes" no es un sí ni un no).
- Reserva de box y de pabellón: el modelo queda abierto, la implementación no entra.
- Hospitalización, laboratorio, inventario y farmacia con control de existencias. El lote se registra en la Aplicación, pero no hay stock.
- Facturación y cobro de la Cita.
- Lista de espera automática para huecos liberados.
- Portal del Tutor.
- Cola de tareas asíncrona.

## Further Notes

- La antirrábica es la única vacuna obligatoria por ley en Chile (Decreto N°1 de 2014 del MINSAL) y solo vale acreditada con certificado emitido por un médico veterinario. De ahí que el certificado sea funcionalidad y no un extra.
- El lote de la Aplicación no es burocracia: es lo único que permite responder ante un retiro de lote o una reacción adversa.
- El estado `no asistió` es lo que justifica económicamente todo el módulo de Avisos. Conviene poder medirlo desde el primer mes.

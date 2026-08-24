# Gatabase

Gestión clínica y de negocio para clínicas veterinarias en Chile: agenda, historia clínica de los pacientes y recordatorios sanitarios.

## Language

### Personas

**Tutor**:
Persona responsable de un Paciente ante la clínica y ante la ley; es quien paga y quien figura en el Registro Nacional de Mascotas. Un Paciente puede tener varios Tutores, uno de ellos marcado como responsable.
_Avoid_: Dueño, propietario, cliente, usuario

**Vínculo**:
Que un Tutor responde por un Paciente. Uno de los Vínculos de un Paciente lo marca como responsable: a quien se llama y a quien se cobra. Se cierra con fecha cuando el animal cambia de manos, sin borrar quién lo trajo antes.
_Avoid_: Relación, asociación, propiedad, dueño de

**Usuario**:
Persona que accede a la aplicación en el contexto de una Clínica — veterinario, recepción o administración. Un Tutor puede tener una cuenta de Usuario asociada, pero son entidades distintas.
_Avoid_: Cuenta, perfil, cliente

### Atención clínica

**Paciente**:
El animal atendido por la clínica, y el único titular de una Historia clínica.
_Avoid_: Mascota, animal, ficha

**Consulta**:
Un encuentro clínico concreto entre un Paciente y un veterinario, en una fecha determinada.
_Avoid_: Visita, atención, cita (una Cita es la reserva; la Consulta es el encuentro)

**Estado del Paciente**:
Situación del animal ante la clínica: `activo`, `inactivo` o `fallecido`, este último con la fecha si se sabe. Un Paciente nunca se borra: el fallecido conserva su ficha y su Historia clínica en solo lectura y no admite Citas; el `inactivo` —dejó de venir sin que se sepa qué pasó— se deshace con que vuelva.
_Avoid_: Baja, eliminado, archivado, desactivado

**Historia clínica**:
La acumulación ordenada de todas las Consultas y registros sanitarios de un Paciente. Acompaña al Paciente aunque cambie de Tutor.
_Avoid_: Ficha médica, expediente, historial

**Cita**:
Reserva de un espacio de agenda para atender a un Paciente. Puede no llegar a convertirse en Consulta.
_Avoid_: Reserva, turno, hora

**Enmienda**:
Corrección o añadido posterior a una Consulta ya cerrada, con fecha y autor propios. Una Consulta cerrada no se modifica: se enmienda.
_Avoid_: Edición, corrección, actualización

**Adjunto**:
Archivo asociado a una Consulta — radiografía, ecografía, foto o informe de laboratorio. Forma parte de la Historia clínica.
_Avoid_: Documento, imagen, archivo

### Salud preventiva

**Producto sanitario**:
Producto del catálogo que se aplica a un Paciente — vacuna o antiparasitario — con la periodicidad de refuerzo que define su fabricante.
_Avoid_: Medicamento, fármaco, artículo

**Aplicación**:
Acto de administrar un Producto sanitario a un Paciente, con lote, fecha, veterinario responsable y la próxima fecha calculada en ese momento.
_Avoid_: Dosis, vacunación, administración

**Estado sanitario**:
Situación del Paciente respecto a un Producto sanitario: `al día`, `vencido` o `desconocido`. `Desconocido` no es `vencido`: genera revisión, no recordatorio.
_Avoid_: Estado de vacunación, situación

**Pendiente**:
Tarea que la Clínica se debe a sí misma sobre un Paciente: refuerzo vencido, control posoperatorio, Estado sanitario desconocido. Vive en una bandeja interna y nunca sale hacia el Tutor por sí solo.
_Avoid_: Recordatorio, alerta, notificación

**Aviso de cita**:
Único mensaje que la Clínica envía al Tutor: anuncia una Cita agendada y le pide confirmar si asiste.
_Avoid_: Recordatorio, notificación, mensaje

**Confirmación**:
Respuesta del Tutor a un Aviso de cita. Cambia el estado de la Cita y consta quién la registró.
_Avoid_: Respuesta, validación

**Conversación**:
Hilo de mensajes entre un Tutor y la Clínica por un canal externo, conservado dentro del sistema. Recepción la atiende; ningún proceso automático consulta datos del Paciente para responderla.
_Avoid_: Chat, hilo, ticket

**Autorespuesta**:
Mensaje fijo que el sistema envía al recibir un mensaje de un Tutor: acusa recibo e informa de cuándo responderá recepción. No interpreta el contenido ni consulta la base de datos.
_Avoid_: Bot, asistente, chatbot

**Horario de atención**:
Franjas en que una Sede atiende. Determina qué Autorespuesta se envía.
_Avoid_: Horario comercial, disponibilidad

**Clínica de derivación**:
Clínica externa, socia o cercana, con capacidad de urgencias, que la Sede entrega a un Tutor cuando no puede atender.
_Avoid_: Clínica de urgencias, partner, referencia

### Cumplimiento

**Registro de acceso**:
Anotación inalterable de qué Usuario vio o modificó qué dato, y cuándo. Es la evidencia exigible ante la Ley 21.719.
_Avoid_: Log, auditoría, historial de cambios

**Estado de identificación**:
Situación del Paciente ante la Ley 21.020: `sin chip`, `chip implantado` o `inscrito en el Registro Nacional`. No se deduce de tener el número de microchip apuntado — tenerlo no es estar inscrito —, y que esté en blanco significa que nadie lo ha preguntado todavía, que no es `sin chip`. Solo obliga a perros y gatos.
_Avoid_: Tiene chip, chipeado, estado del microchip

**Consentimiento de contacto**:
Autorización del Tutor para recibir Recordatorios por un canal concreto.
_Avoid_: Opt-in, suscripción, permiso

### Organización

**Clínica**:
La organización que contrata el sistema; frontera de aislamiento de todos los datos.
_Avoid_: Tenant, cuenta, organización

**Sede**:
Local físico de una Clínica. Las Sedes de una Clínica comparten Tutores y Pacientes, pero no agenda.
_Avoid_: Sucursal, local, branch

---
status: accepted
---

# La Autorespuesta no consulta datos de Tutor ni de Paciente

La Autorespuesta que contesta a un mensaje entrante de WhatsApp envía **un texto fijo** que depende únicamente del Horario de atención de la Sede: acusa recibo e informa de cuándo contestará recepción, y fuera de horario añade el teléfono de urgencias o las Clínicas de derivación. No interpreta el contenido del mensaje y **no consulta la base de datos**. Las Citas las crea recepción; la Conversación la atiende una persona.

El motivo es que el único identificador disponible en un mensaje entrante es el número de teléfono, y un número no acredita identidad: se roba, se reasigna y se comparte entre miembros de una familia. Cualquier respuesta automática que incluya datos del Paciente o del Tutor entrega datos de salud a quien tenga ese teléfono en la mano. Nada de lo que ganaría un flujo automático compensa eso.

Se descartó también el **triaje de urgencias por palabras clave**. Falla precisamente en el caso grave: "mi gato está raro desde ayer" no contiene ninguna palabra clave. La información de urgencias se envía **siempre** en la respuesta de fuera de horario, sin condiciones.

## Consecuencias

- La Conversación es una entidad del dominio con el canal como adaptador, no un registro del webhook de Meta.
- El acceso a una Conversación se registra en el Registro de acceso igual que el de una ficha.
- Los Pendientes (refuerzo vencido, control posoperatorio, Estado sanitario desconocido) son internos y **nunca** generan un mensaje al Tutor. El único mensaje saliente es el Aviso de cita.
- Si en el futuro se automatiza confirmar y cancelar Citas, debe apoyarse en el **token opaco** que viaja en el Aviso de cita, nunca en una búsqueda por número de teléfono. Un token identifica una Cita concreta sin necesidad de identificar a una persona.

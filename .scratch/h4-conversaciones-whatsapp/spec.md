# H4 — Conversaciones de WhatsApp y Autorespuesta

Status: ready-for-agent
Prerrequisito externo: verificación de negocio en Meta y plantilla de utilidad aprobada. El código es autónomo, pero el hito no se puede desplegar sin el trámite.

## Problem Statement

Los Tutores escriben por WhatsApp al teléfono de la clínica. Nadie contesta hasta que recepción tiene un momento libre, y el Tutor no sabe si su mensaje llegó, así que llama por teléfono e interrumpe la atención. Fuera de horario es peor: alguien con una urgencia escribe a las tres de la mañana, no recibe respuesta, y no sabe adónde acudir.

Además, esas conversaciones viven en el WhatsApp del teléfono del mostrador: sin registro, sin historial cuando esa persona no está, y sin ninguna trazabilidad de quién leyó datos personales de un cliente.

## Solution

Los mensajes entrantes se reciben en el sistema como Conversaciones que recepción atiende desde la app. Al llegar un mensaje, el sistema envía de inmediato una **Autorespuesta** de texto fijo: dentro de horario avisa de que recepción contactará hoy; fuera de horario informa del Horario de atención y entrega el teléfono de urgencias propio, o las Clínicas de derivación si la Sede no atiende urgencias.

El Aviso de cita pasa a enviarse por la misma vía, con plantilla aprobada, en lugar de con el enlace manual de H3.

## User Stories

1. Como Tutor, quiero recibir una respuesta inmediata cuando escribo a la clínica, para saber que mi mensaje llegó.
2. Como Tutor, quiero saber cuándo me van a contestar, para no tener que llamar por teléfono.
3. Como Tutor, quiero saber, si escribo fuera de horario, cuál es el horario de atención, para no esperar en vano.
4. Como Tutor con una urgencia de madrugada, quiero recibir el teléfono de una clínica que atienda ahora, para no perder tiempo buscando.
5. Como recepción, quiero ver en la app todos los mensajes entrantes de mi Sede en una bandeja, para atenderlos por orden.
6. Como recepción, quiero ver el hilo completo de una Conversación, para entender el contexto antes de responder.
7. Como recepción, quiero responder desde la app, para que la conversación quede registrada y no dependa de mi teléfono.
8. Como recepción, quiero ver a qué Tutor corresponde un número conocido cuando yo abro la Conversación, para atenderla con contexto.
9. Como recepción, quiero vincular a mano una Conversación de un número desconocido con un Tutor, o crear el Tutor desde ahí, para no perder al cliente nuevo.
10. Como recepción, quiero marcar una Conversación como atendida, para saber qué queda por hacer.
11. Como recepción, quiero crear una Cita desde la Conversación con la información que el Tutor me dio, para no cambiar de pantalla.
12. Como recepción, quiero enviar el Aviso de cita desde el sistema, para no copiar y pegar en otra aplicación.
13. Como recepción, quiero registrar la Confirmación cuando el Tutor contesta que sí o que no, con un botón sobre la Conversación abierta, para actualizar la agenda en un clic.
14. Como recepción, quiero que al registrar "no asisto" el hueco quede libre, porque es lo que recupera el ingreso.
15. Como recepción, quiero que el silencio del Tutor no cancele su Cita, porque no responder no es cancelar.
16. Como admin de Clínica, quiero configurar los dos textos de Autorespuesta de mi Sede, para que suenen como mi clínica.
17. Como admin de Clínica, quiero que la Autorespuesta use mi Horario de atención y mis excepciones por fecha, para que acierte en un festivo.
18. Como admin de Clínica, quiero que la información de urgencias salga siempre en la respuesta de fuera de horario, para no depender de que un sistema adivine si el caso es grave.
19. Como admin de Clínica, quiero saber quién ha leído cada Conversación, porque contiene datos personales igual que una ficha.
20. Como admin de Clínica, quiero que el sistema no envíe nada a un Tutor que retiró su Consentimiento de contacto, para cumplir la ley.
21. Como responsable de la Clínica, quiero que ninguna respuesta automática mencione datos de mis Pacientes, porque un número de teléfono no acredita identidad.

## Implementation Decisions

- **Apps**: `messaging` (Conversación, Mensaje, Autorespuesta, adaptador de canal). `reminders` gana un adaptador nuevo; la cola de envío de H3 no cambia.
- **Autorespuesta** (ADR-0005): dos textos por Sede, **dentro de horario** y **fuera de horario**. El texto se elige únicamente por el Horario de atención y sus excepciones. **No interpreta el mensaje y no consulta la base de datos** de Tutores ni de Pacientes. Si la Sede atiende urgencias 24/7, solo existe el texto de dentro de horario.
- **Sin triaje por palabras clave** (ADR-0005): la información de urgencias va **siempre** en la respuesta de fuera de horario, sin condiciones. Un filtro de palabras falla justo en el caso grave, y equivocarse ahí es la vida de un animal.
- **Conversación como entidad del dominio**: modelo propio con el canal detrás de un **adaptador**, no un registro del webhook de Meta. Meta cambia sus reglas; el modelo no debe caerse con ellas.
- **Ventana de 24 horas de Meta**: responder a un mensaje entrante cae dentro de la ventana de atención y admite texto libre sin plantilla. Un Aviso de cita es proactivo y fuera de ventana, así que **exige plantilla pre-aprobada** de categoría utilidad. El sistema debe distinguir los dos casos y elegir plantilla o texto libre según si la ventana está abierta.
- **Identificación**: al recibir un mensaje no se busca nada. Cuando **recepción** abre la Conversación, el sistema le muestra el Tutor que corresponde a ese número, si lo hay. La diferencia importa: la búsqueda la hace una persona autenticada y queda en el Registro de acceso.
- **Confirmación manual**: recepción marca confirmar o cancelar sobre la Conversación. No se interpreta la respuesta. "No asisto" libera el hueco y deja la Cita en `cancelada por tutor`; el silencio no cambia nada.
- **Token opaco**: el Aviso de cita sigue llevando el token de H3. En H4 tampoco se automatiza nada con él; queda disponible para el futuro.
- **Registro de acceso** (ADR-0004): leer una Conversación se registra igual que leer una ficha.
- **Consentimiento de contacto**: se comprueba antes de cualquier envío, incluida la Autorespuesta.
- **Fuera de horario y urgencias**: el texto compone el Horario de atención de la Sede más el teléfono de urgencias propio, o el catálogo de Clínicas de derivación que mantiene el admin de la Clínica.

## Testing Decisions

- Costura nueva: el **adaptador de canal**, con una implementación falsa. Ningún test toca la red de Meta ni requiere credenciales.
- La costura principal sigue siendo la **petición HTTP con el cliente de test de Django** para todo lo que hace recepción: bandeja, hilo, respuesta, vinculación de Tutor, Confirmación.
- Tests de selección de Autorespuesta: dentro de horario, fuera de horario, en una excepción por fecha, y en una Sede que atiende urgencias 24/7.
- **Test obligatorio de ADR-0005**: la Autorespuesta enviada no contiene ningún dato de Tutor ni de Paciente, y el proceso de recepción de un mensaje no consulta esas tablas.
- Test de ventana de 24 horas: dentro de ventana se envía texto libre; fuera de ventana se exige plantilla y el envío sin plantilla se rechaza.
- Test de que un mensaje de un número desconocido no dispara ninguna búsqueda en la base de datos.
- Tests de Confirmación: "no asisto" libera el hueco; el silencio deja la Cita en pie.
- Test de que leer una Conversación queda en el Registro de acceso.
- Test de que no se envía nada sin Consentimiento de contacto.
- Test de idempotencia ante webhooks repetidos de Meta: un mismo mensaje entrante entregado dos veces no genera dos Autorespuestas.
- Prior art: patrones de H1 a H3.

## Out of Scope

- Cualquier flujo automático que **agende** Citas. Descartado por decisión del usuario y sostenido por ADR-0005: agendar obliga a identificar al Paciente a partir de un número de teléfono, y un número no acredita identidad.
- Interpretación de lenguaje natural, y en particular cualquier respuesta automática de contenido clínico.
- Triaje automático de urgencias.
- Confirmación automática de Citas a partir de la respuesta del Tutor. Si algún día se hace, será con botones interactivos y sobre el token opaco, nunca con búsqueda por teléfono.
- Otros canales (SMS, correo, Telegram).
- Campañas de marketing por WhatsApp.
- Uso de librerías no oficiales de WhatsApp: incumplen los términos de Meta y arriesgan el bloqueo del número de la clínica.

## Further Notes

- El trámite de Meta (verificación de negocio y aprobación de plantilla) puede tardar semanas y no depende del desarrollo. Debe iniciarse en paralelo a H1. Mientras no esté listo, H3 sigue funcionando con el enlace `wa.me` manual, que no requiere autorización de nadie.
- Una vez desplegado H4, el paso siguiente natural y barato es un Aviso de cita con **botones interactivos** de confirmar y cancelar: elimina toda ambigüedad de interpretación sin necesidad de ningún flujo conversacional. Es aproximadamente una semana de trabajo y es donde está casi todo el valor económico. No entra en H4.
- Un flujo de agendamiento automático completo se estimó en tres a cinco semanas, con el coste concentrado en la máquina de estados del diálogo y en la concurrencia de huecos, no en la integración. Se pospone deliberadamente hasta tener datos reales de cuántos Tutores responden y de qué escriben.

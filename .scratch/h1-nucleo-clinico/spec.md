# H1 — Núcleo clínico: Clínica, Usuarios, Tutores y Pacientes

Status: ready-for-agent

## Problem Statement

Una clínica veterinaria chilena de una sede gestiona hoy sus fichas en planillas Excel y en papel. Nadie sabe con certeza cuántos Pacientes activos tiene, no puede buscar por número de microchip, y cuando un Tutor llama por teléfono, recepción tarda minutos en encontrar de qué animal habla. La información existe pero no es consultable, y cada persona de la clínica guarda una parte distinta en su propio archivo.

Además, la Ley 21.719 de protección de datos personales entra en vigencia el 1 de diciembre de 2026 y la clínica no puede demostrar quién accede a los datos de sus clientes.

## Solution

Un sistema web donde la Clínica registra sus Tutores y sus Pacientes una sola vez, los encuentra en segundos por teléfono, nombre o número de microchip, y donde cada acceso a esos datos queda registrado. Los datos existentes entran mediante un importador de planillas, para que el sistema no arranque vacío.

Al terminar H1, el sistema todavía no sustituye al papel para la atención clínica, pero ya es el único fichero de la clínica.

## User Stories

1. Como administrador de plataforma, quiero dar de alta una Clínica con su primera Sede, para que pueda empezar a operar.
2. Como admin de Clínica, quiero crear Usuarios con rol de veterinario, recepción o admin, para que cada persona entre con su propia cuenta.
3. Como admin de Clínica, quiero asignar a cada Usuario una o varias Sedes, para que solo vea la agenda y la bandeja de su lugar de trabajo.
4. Como admin de Clínica, quiero que mi propio rol exija segundo factor, para que la cuenta que puede exportar toda la base esté más protegida.
5. Como Usuario, quiero iniciar sesión con mi correo y contraseña, para acceder a mi Clínica.
6. Como Usuario, quiero que mi sesión caduque por inactividad, para que la ficha que dejé abierta en el mostrador no quede a la vista de un Tutor.
7. Como Usuario, quiero cambiar de Usuario rápidamente en la tablet del box, para que la Consulta no quede firmada con el nombre de otro veterinario.
8. Como recepción, quiero registrar un Tutor con nombre, teléfono, correo y dirección, para poder contactarlo.
9. Como recepción, quiero registrar el RUT de un Tutor de forma opcional, para poder atender también a extranjeros y a quien no quiera darlo.
10. Como recepción, quiero que el sistema valide el dígito verificador del RUT cuando lo escribo, para no guardar un RUT imposible.
11. Como recepción, quiero que el sistema me avise si el RUT que escribo ya existe en la Clínica, para no crear un Tutor duplicado.
12. Como recepción, quiero que el teléfono se normalice a formato internacional, para que sirva para contactar sin ambigüedad.
13. Como recepción, quiero registrar un Paciente con especie, raza, sexo, fecha de nacimiento y color, para identificarlo.
14. Como recepción, quiero elegir la especie de un catálogo cerrado, para que los protocolos y los formularios se comporten según la especie.
15. Como recepción, quiero elegir la raza de un catálogo por especie con autocompletado, para que las estadísticas sirvan.
16. Como recepción, quiero poder escribir una raza libre cuando no está en el catálogo, para no bloquearme con un caso raro.
17. Como recepción, quiero elegir "mestizo" como una raza normal del catálogo, porque es el caso más frecuente en Chile.
18. Como recepción, quiero registrar el número de microchip de 15 dígitos de un Paciente, para poder identificarlo por ley.
19. Como recepción, quiero registrar el estado de identificación del Paciente (sin chip, chip implantado, inscrito en el Registro Nacional), para saber qué le falta al Tutor para cumplir la ley.
20. Como recepción, quiero que el sistema me impida guardar dos Pacientes con el mismo microchip en mi Clínica, para no duplicar fichas.
21. Como recepción, quiero vincular varios Tutores a un mismo Paciente, para atender familias y parejas separadas.
22. Como recepción, quiero marcar cuál Tutor es el responsable, para saber a quién contactar y a quién cobrar.
23. Como recepción, quiero vincular varios Pacientes a un mismo Tutor, porque casi siempre tiene más de un animal.
24. Como recepción, quiero cerrar el vínculo de un Tutor con un Paciente con fecha, para reflejar que el animal cambió de dueño sin perder el registro de quién lo trajo antes.
25. Como recepción, quiero que la Historia clínica siga al Paciente cuando cambia de Tutor, porque es información del animal.
26. Como recepción, quiero buscar un Paciente por nombre, por teléfono del Tutor o por microchip, para encontrarlo mientras hablo por teléfono.
27. Como recepción, quiero que al crear un Paciente el sistema me muestre coincidencias probables por teléfono y por microchip, para no crear un duplicado.
28. Como recepción, quiero marcar un Paciente como fallecido con fecha, para que no siga apareciendo como activo.
29. Como recepción, quiero que un Paciente fallecido conserve toda su Historia clínica en solo lectura, porque el histórico vale precisamente por esos casos.
30. Como recepción, quiero que un Paciente fallecido no admita nuevas Citas, para no agendar por error.
31. Como recepción, quiero marcar un Paciente como inactivo, para el animal que dejó de venir sin que sepamos si murió.
32. Como admin de Clínica, quiero registrar el Horario de atención de cada Sede, con excepciones por fecha, para reflejar festivos y cierres por vacaciones.
33. Como admin de Clínica, quiero declarar si mi Sede atiende urgencias, para que el sistema sepa qué decir fuera de horario.
34. Como admin de Clínica, quiero mantener un catálogo de Clínicas de derivación con nombre, teléfono y dirección, porque la red de clínicas socias es conocimiento mío y cambia.
35. Como admin de Clínica, quiero importar mis Tutores y Pacientes desde una planilla CSV, para no teclear años de datos.
36. Como admin de Clínica, quiero un informe de errores del importador fila a fila, para corregir la planilla y reintentar.
37. Como admin de Clínica, quiero que el importador no cree duplicados al reintentar, para poder importar por tandas.
38. Como admin de Clínica, quiero exportar todos los datos de mi Clínica, porque la información es de mi clínica, no del proveedor.
39. Como admin de Clínica, quiero exportar los datos personales de un Tutor concreto, para atender su derecho de acceso.
40. Como admin de Clínica, quiero anonimizar los datos personales de un Tutor sin destruir la Historia clínica de sus Pacientes, para atender su derecho de supresión sin incumplir el deber de conservación clínica.
41. Como admin de Clínica, quiero ver quién accedió a la ficha de un Tutor o de un Paciente y cuándo, para responder ante la autoridad.
42. Como responsable de la Clínica, quiero que ningún Usuario de otra Clínica pueda ver mis datos, porque compito con ella.

## Implementation Decisions

- **Stack**: Django con plantillas server-rendered, HTMX y Alpine. Sin SPA, sin API REST. Postgres. `django-allauth` para autenticación. `USE_TZ` activo, hora almacenada en UTC y presentada en `America/Santiago`. `USE_I18N` activo con todos los textos en `gettext`, aunque el único idioma sea `es-CL`.
- **Apps**: `tenancy` (Clínica, Sede, pertenencia de Usuario, Horario de atención, Clínica de derivación), `tutors` (Tutor, vínculo Tutor–Paciente), `patients` (Paciente, identificación, catálogo de especies y razas), `audit` (Registro de acceso), `imports` (importador CSV). Los nombres de app usan el vocabulario de `CONTEXT.md`: `tutors`, no `clients`.
- **Regla de dependencias entre apps**: `audit` no importa de ninguna app de dominio; recibe eventos. Se documenta en `CLAUDE.md`.
- **Tenancy** (ADR-0003): clave ajena `clinic` en todos los modelos de dominio, Clínica resuelta en middleware, manager por defecto que filtra. El acceso sin filtrar existe pero es explícito.
- **Sede**: comparte Tutores y Pacientes con las demás Sedes de la Clínica; no comparte agenda ni bandejas.
- **Identidad de Tutor**: clave primaria interna propia. RUT opcional, normalizado sin puntos ni guion, validado con dígito verificador, único dentro de la Clínica cuando está presente. Teléfono normalizado a E.164, **no** único: se permite compartido con aviso, porque una familia comparte número.
- **Identidad de Paciente**: clave primaria interna propia. Microchip opcional, único dentro de la Clínica, **nunca único a nivel global** (ADR-0001). Estado de identificación como campo propio y distinto de "tiene chip o no".
- **Consentimiento de contacto**: campo por Tutor y por canal desde el primer día, aunque en H1 no se envíe nada.
- **Separación de datos**: datos personales del Tutor y datos clínicos del Paciente en modelos separados, para permitir anonimizar al Tutor conservando la Historia clínica (ADR-0004).
- **Estados de Paciente**: `activo`, `inactivo`, `fallecido` con fecha. `fallecido` bloquea Citas nuevas y, desde H3, detiene todos los Pendientes de inmediato.
- **Catálogos**: especie cerrada; raza por especie con autocompletado más opción `otra` con texto libre; `mestizo` como entrada de primera clase.
- **Registro de acceso** (ADR-0004): tabla propia append-only escrita desde las vistas, porque las lecturas no disparan señales de modelo. Sin `UPDATE` ni `DELETE` a nivel de permisos de base de datos.
- **Sesiones**: caducidad por inactividad de 30 minutos, cambio rápido de Usuario. Segundo factor obligatorio solo para el rol admin.
- **Importador**: CSV de Tutores y Pacientes con validación previa, informe de errores por fila e idempotencia por clave natural, para permitir reintentos por tandas. El histórico clínico **no** se importa.
- **Datos de desarrollo**: juego de datos mock generado por comando de gestión, con volumen realista de una clínica de una sede.

## Testing Decisions

- Un buen test aquí entra por la **petición HTTP con el cliente de test de Django**, autenticado como un Usuario con un rol y una Sede, y comprueba lo que el Usuario observa: qué ve en la página, qué queda guardado, qué se le niega. No comprueba nombres de métodos ni consultas internas.
- Herramientas: `pytest-django` y `factory_boy`. Sin objetivo de cobertura.
- **Suite obligatoria — aislamiento entre Clínicas**: un test estructural que recorre los modelos de dominio y falla si alguno no tiene `clinic`, más tests por HTTP que intentan leer, editar y buscar objetos de otra Clínica y esperan 404.
- **Suite obligatoria — Registro de acceso**: abrir la ficha de un Paciente y de un Tutor por HTTP y comprobar que el acceso quedó registrado con Usuario y momento. Comprobar que el registro no se puede modificar ni borrar.
- Tests de validación de RUT, incluidos dígito verificador correcto e incorrecto, RUT con y sin formato, y ausencia de RUT.
- Tests de normalización de teléfono a E.164 con las formas en que se escribe en Chile.
- Tests del importador: fila válida, fila inválida con su mensaje, reimportación del mismo archivo sin crear duplicados.
- Tests de estados de Paciente: fallecido no admite Cita nueva y conserva la ficha legible.
- Tests de anonimización de Tutor: los datos personales desaparecen y la Historia clínica del Paciente permanece íntegra.
- No hay prior art en el repositorio: H1 establece los patrones que seguirán los hitos siguientes.

## Out of Scope

- Consulta, SOAP, Enmienda y Adjuntos (H2).
- Cita, agenda, Aplicaciones y Pendientes (H3).
- Conversaciones, Autorespuesta y cualquier integración con WhatsApp (H4).
- Facturación, boleta electrónica del SII, inventario, farmacia, hospitalización y laboratorio.
- Portal del Tutor.
- Fusión de fichas duplicadas: en H1 solo hay **prevención** por búsqueda de coincidencias. La fusión se pospone deliberadamente hasta observar cómo se duplican de verdad en la clínica piloto.
- Integración con el Registro Nacional de Mascotas: no consta que exponga API pública; la inscripción la hace el Tutor con su Clave Única.
- Cualquier deduplicación de Pacientes por microchip entre Clínicas: prohibida por ADR-0001.

## Further Notes

- El microchip es obligatorio por Ley 21.020 desde el 12 de febrero de 2019 y es el veterinario quien lo implanta y certifica los datos del animal. Por eso el estado de identificación es información útil para la clínica, no burocracia.
- El criterio de éxito del piloto es de H2, no de H1: cuatro semanas seguidas en que toda Consulta atendida queda registrada el mismo día, sin papel paralelo. Si la clínica sigue usando el cuaderno para algo, **eso** es la siguiente funcionalidad.
- Arrancar el trámite de verificación de negocio con Meta en paralelo a H1, porque es tiempo de espera y no tiempo de trabajo (ver H4).

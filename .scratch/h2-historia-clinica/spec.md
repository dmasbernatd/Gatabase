# H2 — Historia clínica: Consulta, Enmiendas y Adjuntos

Status: ready-for-agent

## Problem Statement

La atención clínica se anota en papel. Cuando un Paciente vuelve seis meses después, el veterinario depende de encontrar la hoja correcta en un archivador, y a menudo no la encuentra o no puede leer la letra de otro colega. La curva de peso de un Paciente crónico, que es el dato que más orienta el tratamiento, no existe: está repartida en anotaciones sueltas.

Peor: no hay forma de saber qué decía la ficha en el momento en que se tomó una decisión clínica. Ante una reclamación, la clínica no puede sostener su versión.

## Solution

La Consulta se registra en el sistema durante la atención, con estructura suficiente para poder explotarla después. Al cerrarla queda firmada e inmutable; toda corrección posterior es una Enmienda fechada y atribuida. Las radiografías y los informes de laboratorio se adjuntan a la Consulta.

Al terminar H2 el sistema **sustituye al papel**. Es el hito que decide si el piloto funciona.

## User Stories

1. Como veterinario, quiero abrir una Consulta para un Paciente, para registrar la atención mientras la hago.
2. Como veterinario, quiero registrar el motivo de la Consulta en palabras del Tutor, para saber por qué vino.
3. Como veterinario, quiero registrar la anamnesis y lo que observo en secciones separadas (subjetivo, objetivo, evaluación, plan), para pensar de forma ordenada y encontrar después lo que busco.
4. Como veterinario, quiero registrar el peso del Paciente como un número, no como texto, para poder ver su evolución.
5. Como veterinario, quiero registrar temperatura, frecuencia cardíaca y frecuencia respiratoria como números con su fecha, para seguir un caso.
6. Como veterinario, quiero ver la curva de peso de un Paciente a lo largo del tiempo, porque es lo que más me orienta en un crónico.
7. Como veterinario, quiero ver el peso de la Consulta anterior mientras registro la actual, para notar una pérdida sin tener que buscarla.
8. Como veterinario, quiero registrar el diagnóstico y el tratamiento indicado, para que quede constancia de mi decisión.
9. Como veterinario, quiero anotar el folio de la receta electrónica que emití en el sistema del SAG, para que la ficha y la receta cuenten lo mismo.
10. Como veterinario, quiero guardar la Consulta sin cerrarla y seguir editándola durante la atención, porque no la escribo de una vez.
11. Como veterinario, quiero cerrar la Consulta con un acto explícito, para saber que ya está firmada.
12. Como veterinario, quiero que una Consulta cerrada no se pueda editar, porque es un documento con valor legal.
13. Como veterinario, quiero añadir una Enmienda a una Consulta cerrada, para corregir o completar lo que haga falta.
14. Como veterinario, quiero que mi Enmienda lleve mi nombre y su fecha, distinta de la de la Consulta original, para que se entienda cuándo se supo cada cosa.
15. Como veterinario, quiero leer una Consulta junto con todas sus Enmiendas en orden cronológico, para entender el caso completo de un vistazo.
16. Como veterinario, quiero ver la Historia clínica completa de un Paciente ordenada por fecha, para ponerme al día antes de entrar al box.
17. Como veterinario, quiero que la Historia clínica sea del Paciente y no del Tutor, para no perderla cuando el animal cambia de dueño.
18. Como veterinario, quiero adjuntar una radiografía, una ecografía o una foto de la lesión a la Consulta, para que la imagen viva con el caso.
19. Como veterinario, quiero adjuntar el PDF del laboratorio, para no buscarlo en el correo.
20. Como veterinario, quiero descargar un Adjunto, para verlo en pantalla grande.
21. Como veterinario, quiero que los Adjuntos no sean accesibles por una dirección pública, porque son datos de salud.
22. Como veterinario, quiero atender a un Paciente que llegó sin Cita y registrar su Consulta, sin que el sistema me obligue a inventar una reserva.
23. Como veterinario, quiero que la Consulta registre quién la atendió y en qué Sede, para saber a quién preguntar después.
24. Como recepción, quiero imprimir o exportar un resumen de la Consulta para el Tutor, para que se lleve las indicaciones por escrito.
25. Como admin de Clínica, quiero saber quién ha visto la Historia clínica de un Paciente y quién ha descargado un Adjunto, para responder ante la autoridad.
26. Como admin de Clínica, quiero que no se pueda borrar una Consulta, para que la historia sea confiable.
27. Como responsable de la Clínica, quiero que ninguna otra Clínica del sistema vea las Historias clínicas de mis Pacientes, aunque atienda al mismo animal.

## Implementation Decisions

- **Apps nuevas**: `records` (Consulta, Enmienda, Adjunto, constantes clínicas).
- **Regla de dependencias**: `records` **no importa** de `scheduling`. La Cita apunta a la Consulta que generó, de forma opcional, nunca al contrario. Sin esta regla, atender a un espontáneo obligaría a inventar una Cita falsa. Se documenta en `CLAUDE.md`.
- **Estructura de la Consulta**: SOAP semiestructurado — cuatro campos de texto (subjetivo, objetivo, evaluación, plan) más motivo, diagnóstico y tratamiento indicado. Las **constantes clínicas** (peso, temperatura, frecuencia cardíaca, frecuencia respiratoria) son campos numéricos tipados con unidad y fecha, no texto libre, porque de eso dependen las curvas.
- **Ciclo de vida** (ADR-0002): la Consulta tiene fase **abierta** (editable por su autor durante la atención) y **cerrada** (inmutable). El cierre es un acto explícito distinto del guardado. La restricción de inmutabilidad vive en el modelo, no en la plantilla ni en el formulario.
- **Enmienda**: entidad propia encadenada a la Consulta, con autor y fecha propios. Es información clínica legible por el veterinario, no metadato de auditoría; se muestra en el mismo hilo que la Consulta.
- **Consulta sin Cita**: la Consulta no requiere Cita. El vínculo es opcional y unidireccional.
- **Receta del SAG**: el sistema **no emite** recetas de antimicrobianos, porque desde el 1 de enero de 2024 esa prescripción es obligatoria por la plataforma del SAG con el veterinario inscrito allí. La Consulta registra el tratamiento indicado y guarda el **folio** de la receta emitida en el SAG como referencia. Sin integración.
- **Adjuntos**: almacenamiento S3-compatible **privado**, acceso mediante URL firmada de vida corta, jamás objetos públicos. Subir, listar y descargar; sin visor DICOM, sin miniaturas, sin edición.
- **Registro de acceso** (ADR-0004): se registra la lectura de la Historia clínica, la apertura de una Consulta y la descarga de cada Adjunto, en el momento de servirlos.
- **Borrado**: no existe borrado de Consulta ni de Enmienda. Un Adjunto subido por error se marca como retirado, no se elimina el registro.
- **Aislamiento** (ADR-0001, ADR-0003): la Historia clínica pertenece a la Clínica que la registró. No hay consulta entre tenants ni deduplicación por microchip.

## Testing Decisions

- La costura sigue siendo la **petición HTTP con el cliente de test de Django**, autenticado como veterinario o como recepción. Se prueba lo que el Usuario observa y lo que el sistema le niega, no la estructura interna del modelo.
- **Suite obligatoria — inmutabilidad**: cerrar una Consulta por HTTP y comprobar que cualquier intento posterior de editarla se rechaza, incluida la petición construida a mano contra la vista de edición. Comprobar que la Enmienda sí se acepta y que aparece en el hilo con su autor y su fecha.
- **Suite obligatoria — Registro de acceso**: leer una Historia clínica y descargar un Adjunto, y comprobar que ambos accesos quedaron registrados con Usuario y momento.
- Tests de aislamiento entre Clínicas por HTTP para Consulta, Enmienda y Adjunto: 404, nunca 403 con contenido.
- Tests de Adjuntos con un almacenamiento falso en memoria: ningún test toca S3. Comprobar que la URL servida caduca y que no existe acceso anónimo.
- Tests de constantes clínicas: la curva de peso devuelve los valores en orden y una Consulta sin peso no rompe la curva.
- Test de que se puede registrar una Consulta sin ninguna Cita asociada.
- Prior art: los patrones de test establecidos en H1 (cliente autenticado, factories por Clínica, aserciones de aislamiento).

## Out of Scope

- Agenda, Cita, Aplicaciones y Pendientes (H3).
- Conversaciones y WhatsApp (H4).
- Emisión de recetas de antimicrobianos: la hace el SAG, no este sistema.
- Integración con la plataforma del SAG: no consta que exponga integración disponible.
- Visor de imagen médica, DICOM, anotación sobre radiografías.
- Plantillas de Consulta por tipo de atención y campos por especie: posible mejora posterior, no en H2.
- Firma electrónica avanzada: el cierre atribuido al Usuario autenticado es suficiente para el piloto.
- Facturación de la Consulta.

## Further Notes

- H2 va **antes** que la agenda aunque la agenda sea más vistosa y más fácil de demostrar. La agenda tiene sustitutos aceptables (un calendario compartido, un cuaderno); la Historia clínica no tiene ninguno. Si el proyecto solo llega a H2, la clínica ya se queda con el sistema.
- La `próxima_fecha` de refuerzos y los Pendientes derivados de una Consulta llegan en H3. En H2, el plan terapéutico se escribe en el campo `plan`.

# 01 — Abrir una Consulta y escribirla durante la atención

**What to build:** el veterinario abre una Consulta desde la ficha del Paciente y la va escribiendo mientras atiende: motivo, subjetivo, objetivo, evaluación, plan, diagnóstico, tratamiento indicado y folio de la receta del SAG. Guarda cuantas veces quiera sin cerrarla. Nace la app `records`, que es donde vivirá toda la Historia clínica.

Es la rebanada más fina que ya sirve: aunque no se cierre ni tenga constantes, una Consulta escrita en el sistema es una hoja menos en el archivador.

**Blocked by:** —

**Status:** done

- [x] Modelo `Consulta` en `apps/records` con `clinic` y el manager que filtra por Clínica (ADR-0003)
- [x] Campos: motivo (en palabras del Tutor), subjetivo, objetivo, evaluación, plan, diagnóstico, tratamiento indicado y folio de la receta del SAG (texto libre, opcional, sin validar contra nada: no hay integración)
- [x] La Consulta registra quién la atendió (el Usuario que la abre) y en qué Sede, y el momento de apertura en UTC, presentado en `America/Santiago`
- [x] La Consulta no requiere Cita: `records` no importa de `scheduling`, y hay un test que abre una Consulta sin ninguna Cita en el sistema
- [x] Botón «Abrir Consulta» en la ficha del Paciente; guardar deja la Consulta abierta y vuelve a ella
- [x] Solo el rol veterinario abre y escribe Consultas; recepción y admin reciben 403 al intentarlo (el decorador va en `apps/tenancy/permisos.py`, junto a `solo_admin`)
- [x] Mientras está abierta, solo su autor la edita; otro veterinario la lee pero no la cambia
- [x] Un Paciente `fallecido` no admite Consultas nuevas (su Historia clínica queda en solo lectura, `CONTEXT.md`)
- [x] No existe borrado de Consulta: ni vista, ni acción de admin; el `Paciente` la protege (`PROTECT`) y un test lo comprueba
- [x] Abrir la página de una Consulta queda en el Registro de acceso (`@deja_constancia`), y guardarla, como modificación
- [x] Aislamiento por HTTP: la Consulta de otra Clínica da 404, nunca 403 con contenido
- [x] Textos en `gettext`

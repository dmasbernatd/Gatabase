# 03 — Enmiendas: corregir o completar una Consulta cerrada

**What to build:** sobre una Consulta cerrada, el veterinario añade una Enmienda con su nombre y su fecha. La Consulta y sus Enmiendas se leen como un solo hilo en orden cronológico, de modo que se entiende qué se sabía en cada momento.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Modelo `Enmienda` encadenado a la Consulta, con `clinic`, autor, momento y texto propios
- [ ] Solo se enmienda una Consulta cerrada; sobre una abierta se edita, no se enmienda
- [ ] Cualquier veterinario de la Clínica puede enmendar, no solo el autor de la Consulta (quien recibe el resultado del laboratorio puede no ser quien atendió)
- [ ] Una Enmienda es inmutable desde que se guarda y no se borra: la misma regla que la Consulta cerrada, en el modelo
- [ ] La página de la Consulta muestra la Consulta original y debajo sus Enmiendas en orden cronológico, cada una con su autor y su fecha, distinguibles a simple vista del texto original
- [ ] **Suite obligatoria — inmutabilidad** (segunda mitad): la Enmienda sí se acepta y aparece en el hilo con su autor y su fecha
- [ ] Añadir una Enmienda queda en el Registro de acceso como modificación de la Consulta
- [ ] Aislamiento por HTTP: enmendar la Consulta de otra Clínica da 404
- [ ] Decidir si la Consulta de un Paciente `fallecido` admite Enmiendas. Propuesta: **sí** —el informe de necropsia o el laboratorio llegan después de la muerte, y una Enmienda no altera lo escrito—, y ajustar la definición de Estado del Paciente en `CONTEXT.md` para que «solo lectura» diga lo que significa

## Agent skills

### Issue tracker

Issues live as markdown files under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five canonical roles, unchanged. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout — `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Reglas del proyecto

Usa el vocabulario de `CONTEXT.md` en código, tests, plantillas y mensajes de commit. Lee `docs/adr/` antes de tocar tenancy, Consulta, auditoría o mensajería.

### Dependencias entre apps

- `records` **no importa** de `scheduling`. Una Cita puede apuntar a la Consulta que generó; nunca al contrario. Si no, atender a un espontáneo obliga a inventar una Cita falsa.
- `audit` no importa de ninguna app de dominio: recibe eventos.
- El cálculo de huecos disponibles vive en un módulo de servicio con firma y tests propios, nunca dentro de una vista ni de una plantilla.

### Invariantes

- Todo modelo de dominio lleva `clinic` y filtra por el manager por defecto (ADR-0003).
- Una Consulta cerrada no se edita: se enmienda (ADR-0002).
- El microchip es único dentro de una Clínica, nunca a nivel global (ADR-0001).
- Toda lectura de datos de Tutor, Paciente, Adjunto o Conversación se registra (ADR-0004).
- La Autorespuesta no consulta datos de Tutor ni de Paciente (ADR-0005).
- Fechas en UTC en base de datos, presentadas en `America/Santiago`. Textos siempre en `gettext`.

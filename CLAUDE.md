## Agent skills

### Issue tracker

Issues live as markdown files under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five canonical roles, unchanged. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout — `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Subagent routing

Tiers and the standing rules live in `~/.claude/CLAUDE.md`. This section says who takes which step of `/code-review` and `/triage`, because neither skill names an agent itself — left alone, every sub-agent it spawns inherits the session model.

The pattern both follow: **cheap models fetch and run; Opus decides.** The saving comes from keeping the diff, the issue bodies and the test output out of an Opus context — never from letting a cheap model form an opinion.

**`/code-review`**

- Steps 1–3 (resolve the fixed point, capture the diff and commit list, fetch the spec, locate standards sources) → `scout`.
- Step 4, both axes → `deep`. Standards is not the cheap axis: the smell baseline is a judgement call by the skill's own wording, and step 5 forbids reranking, so a sub-agent's findings reach the user near-verbatim. A weak reviewer's false positives would be published, not filtered.
- Step 5 (aggregate) stays in the main context — the final call on a finding is never delegated.

**`/triage`**

- Bucketing what needs attention → `scout`.
- Step 1: `scout` gathers candidate existing implementations and `.out-of-scope/` matches; deciding whether it is *the same domain concept* stays here.
- Step 2 (recommend category and state) is interactive — never delegated.
- Step 3 (verify the claim: reproduce the bug, check out the PR, run the tests) → `scout`, reporting output verbatim. Heavy output, binary result.
- Step 4 (grill, domain-modeling) stays here: it writes `CONTEXT.md` and ADRs.
- Step 5: the agent brief → `deep`, since it is the contract a later agent builds from. Closing an issue or writing `.out-of-scope/` touches the tracker — confirm with the maintainer first.

## Reglas del proyecto

Usa el vocabulario de `CONTEXT.md` en código, tests, plantillas y mensajes de commit. Lee `docs/adr/` antes de tocar tenancy, Consulta, auditoría o mensajería.

### Dependencias entre apps

- `records` **no importa** de `scheduling`. Una Cita puede apuntar a la Consulta que generó; nunca al contrario. Si no, atender a un espontáneo obliga a inventar una Cita falsa.
- `tutors` **conoce** a `patients`, y no al revés. El Vínculo Tutor–Paciente vive en `tutors` porque es un hecho del Tutor —de quién se hace cargo— y porque así la dependencia va en un solo sentido: el Paciente sigue siendo el mismo aunque cambie de manos, y no puede depender de quién responde por él.
- `tenancy` **no importa** de ninguna app de dominio, porque todas importan de ella: la Clínica es la frontera de todo dato. Lo que necesiten dos apps que no pueden verse —cómo se normaliza un teléfono, qué es un campo que normaliza— vive en `apps/` a secas (`apps/telefono.py`, `apps/campos.py`).
- `audit` no importa de ninguna app de dominio: recibe eventos y guarda el tipo del objeto como texto (`tutors.Tutor`). De `tenancy` sí depende, y no puede no depender: la Clínica es la frontera de todo dato (ADR-0003) y el Usuario es quien accede.
- El cálculo de huecos disponibles vive en un módulo de servicio con firma y tests propios, nunca dentro de una vista ni de una plantilla.

### Invariantes

- Todo modelo de dominio lleva `clinic` y filtra por el manager por defecto (ADR-0003).
- Una Consulta cerrada no se edita: se enmienda (ADR-0002).
- El microchip es único dentro de una Clínica, nunca a nivel global (ADR-0001).
- Un Paciente tiene como mucho un Tutor responsable a la vez, y lo garantiza la base de datos.
- La especie es un catálogo cerrado en código (`apps/patients/catalogo.py`); la raza sugiere pero admite texto libre.
- Toda lectura de datos de Tutor, Paciente, Adjunto o Conversación se registra (ADR-0004).
- La Autorespuesta no consulta datos de Tutor ni de Paciente (ADR-0005).
- Fechas en UTC en base de datos, presentadas en `America/Santiago`. Textos siempre en `gettext`.

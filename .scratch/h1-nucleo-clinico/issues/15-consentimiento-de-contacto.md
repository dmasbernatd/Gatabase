# 15 — Consentimiento de contacto del Tutor

**What to build:** el Tutor decide por qué canales acepta que la clínica lo contacte, y el sistema lo respeta. En H1 no se envía nada todavía, pero el dato tiene que estar recogido desde el principio: pedirlo retroactivamente a toda la base de clientes es un trabajo que nadie hace.

**Blocked by:** 05

**Status:** done

- [x] Consentimiento por Tutor y por canal (WhatsApp, teléfono, correo), con su fecha
- [x] Recepción lo registra y lo revoca desde la ficha del Tutor
- [x] La ficha muestra el estado actual de forma clara antes de que alguien piense en contactar
- [x] Queda registro de cuándo se otorgó y cuándo se revocó, no solo del valor actual
- [x] Una función consultable que responde si se puede contactar a un Tutor por un canal dado; H3 y H4 la usan antes de cualquier envío
- [x] El cambio de consentimiento queda en el Registro de acceso
- [x] Test de que la función niega el contacto tras una revocación

## Comments

Implementado. Decisiones que no estaban en el ticket y que conviene tener a mano:

- **Cada declaración es una fila, no una columna del Tutor** (`tutors.Consentimiento`).
  Lo exigible ante la Ley 21.719 no es qué acepta hoy, sino desde cuándo lo
  aceptaba el día que se le escribió; un booleano que se sobrescribe deja cada
  mensaje ya enviado sin nada detrás. La última declaración de cada canal es la
  que vale.
- **Tres estados y no dos**: `no consta` —nadie lo preguntó— no es `revocado`.
  Los dos niegan el envío y no dicen lo mismo en el mostrador. Mismo criterio que
  el Estado de identificación y que el Estado sanitario.
- **La pregunta de H3 y H4** es `apps.tutors.consentimiento.se_puede_contactar(tutor, canal)`.
  Niega por defecto y no depende de que haya Clínica activa: la hará una tarea,
  no una petición HTTP.
- **El canal en blanco no es una negativa**: en el formulario significa que de
  ese canal no se habló, y se queda como estaba. Así una visita a la pantalla no
  revoca en silencio los otros dos.
- Volver a decir lo que ya constaba **no** deja una fila nueva, y por eso solo se
  anota en el Registro de acceso cuando algo cambió de verdad.

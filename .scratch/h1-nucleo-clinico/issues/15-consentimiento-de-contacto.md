# 15 — Consentimiento de contacto del Tutor

**What to build:** el Tutor decide por qué canales acepta que la clínica lo contacte, y el sistema lo respeta. En H1 no se envía nada todavía, pero el dato tiene que estar recogido desde el principio: pedirlo retroactivamente a toda la base de clientes es un trabajo que nadie hace.

**Blocked by:** 05

**Status:** ready-for-agent

- [ ] Consentimiento por Tutor y por canal (WhatsApp, teléfono, correo), con su fecha
- [ ] Recepción lo registra y lo revoca desde la ficha del Tutor
- [ ] La ficha muestra el estado actual de forma clara antes de que alguien piense en contactar
- [ ] Queda registro de cuándo se otorgó y cuándo se revocó, no solo del valor actual
- [ ] Una función consultable que responde si se puede contactar a un Tutor por un canal dado; H3 y H4 la usan antes de cualquier envío
- [ ] El cambio de consentimiento queda en el Registro de acceso
- [ ] Test de que la función niega el contacto tras una revocación

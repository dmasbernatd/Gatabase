# 14 — Configuración de la Sede: Horario de atención y Clínicas de derivación

**What to build:** el admin de la Clínica declara cuándo atiende su Sede, si atiende urgencias, y a qué clínicas derivar cuando no puede. Es configuración que en H1 no hace nada visible, pero de la que dependen la agenda (H3) y la Autorespuesta (H4).

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Horario semanal por Sede, con varias franjas por día
- [ ] **Excepciones por fecha**, para festivos y cierres por vacaciones. Deliberadamente no se usa un calendario automático de festivos: los festivos chilenos son irregulares y un cierre por vacaciones no está en ninguna lista
- [ ] Bandera de si la Sede atiende urgencias, y teléfono de urgencias propio cuando aplica
- [ ] Catálogo de **Clínicas de derivación** con nombre, teléfono y dirección, que mantiene el admin de la Clínica, porque la red de clínicas socias es conocimiento local y cambia
- [ ] Una función consultable que responde si una Sede está en horario en un instante dado, con sus excepciones aplicadas
- [ ] Tests de la función en horario, fuera de horario, en el borde exacto de una franja, y en una fecha de excepción
- [ ] Test en las semanas del cambio de hora de septiembre y de abril, porque el horario se declara en hora local

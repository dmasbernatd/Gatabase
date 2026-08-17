# 01 — Andamiaje del proyecto y primera página verificable

**What to build:** un proyecto Django que arranca contra Postgres, sirve una página y tiene la suite de tests corriendo en verde. Nadie de la clínica ve valor todavía; lo que entrega es la base sobre la que todo lo demás es verificable.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Proyecto Django con Postgres, arrancable con un comando documentado en el README
- [ ] `USE_TZ` activo, hora almacenada en UTC y `TIME_ZONE` en `America/Santiago`
- [ ] `USE_I18N` activo, idioma `es-CL`, y todos los textos de plantilla pasando por `gettext` desde el primer día
- [ ] `pytest-django` y `factory_boy` configurados; `pytest` corre y pasa
- [ ] Un test que comprueba que la página raíz responde
- [ ] Un test que comprueba que una fecha guardada y recuperada mantiene el instante correcto al presentarse en `America/Santiago`
- [ ] Las nueve apps del spec creadas vacías (`tenancy`, `clients`, `patients`, `records`, `preventive`, `scheduling`, `reminders`, `audit`, `imports`), para fijar la estructura desde el principio

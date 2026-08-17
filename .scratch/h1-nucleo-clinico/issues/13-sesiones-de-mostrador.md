# 13 — Sesiones de mostrador y segundo factor del admin

**What to build:** el sistema se usa en un computador de mostrador a la vista de los Tutores y en una tablet de box que comparten tres veterinarios. Este ticket hace que eso sea seguro sin volverlo incómodo.

El riesgo real no es un atacante remoto: es que una Consulta quede firmada con el nombre del veterinario equivocado, y esa firma tiene valor legal.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Caducidad de sesión por inactividad, con el plazo configurable y 30 minutos por defecto
- [ ] Aviso al Usuario antes de que caduque, para no perder lo que está escribiendo
- [ ] Cambio rápido de Usuario en pocos clics, pensado para la tablet compartida
- [ ] La página muestra siempre y de forma visible qué Usuario está activo
- [ ] Segundo factor **obligatorio** para el rol admin, que es quien puede exportar toda la base
- [ ] Segundo factor **no exigido** a veterinario ni a recepción, por fricción en mostrador
- [ ] Tests de caducidad por inactividad y de que el admin sin segundo factor configurado no completa el login

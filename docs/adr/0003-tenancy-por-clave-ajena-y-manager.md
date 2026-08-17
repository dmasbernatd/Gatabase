---
status: accepted
---

# Tenancy por clave ajena `clinic` y manager por defecto

Todos los modelos de dominio llevan una clave ajena `clinic`, la Clínica actual se resuelve en un middleware y el manager por defecto de cada modelo filtra por ella. Descartamos **`django-tenants` con un schema de Postgres por Clínica** (complica migraciones, despliegues y cualquier consulta agregada, y el coste crece con cada cliente nuevo) y descartamos **Row Level Security de Postgres como mecanismo principal** (obliga a manejar la conexión y un `SET LOCAL` por request, y pelea con el ORM y con el pool de conexiones).

El riesgo asumido es real y grave: una consulta que olvide el filtro filtra Historias clínicas entre Clínicas en silencio. La defensa no es la disciplina del desarrollador, son dos mecanismos: el manager por defecto que filtra sin que haya que pedirlo, y un test que enumera los modelos de dominio y **falla si alguno no tiene `clinic`**.

## Consecuencias

- Usar `objects` sin filtro debe ser seguro por defecto; el acceso sin filtrar existe pero es explícito y llamativo.
- La Sede es una entidad aparte dentro de la Clínica: comparte Tutores y Pacientes, pero no agenda ni bandeja de Pendientes.
- RLS sigue disponible como red de seguridad a nivel de motor sobre este mismo esquema si algún día se necesita esa garantía. No requiere rediseño.

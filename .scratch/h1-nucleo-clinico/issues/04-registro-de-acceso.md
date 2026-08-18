# 04 — Registro de acceso

**What to build:** cada vez que un Usuario ve o modifica datos personales, queda constancia de quién, qué y cuándo, y el admin de la Clínica puede consultarlo. Implementa ADR-0004.

Va antes de Paciente a propósito: el mecanismo de registro debe existir cuando se escriban las vistas siguientes, para no tener que volver a pasar por todas.

**Blocked by:** 03

**Status:** done

- [x] Modelo de Registro de acceso con Usuario, Clínica, tipo de objeto, identificador, acción y momento
- [x] Registro escrito **desde las vistas**, porque una lectura no dispara señales de modelo
- [x] Mecanismo reutilizable (mixin o decorador de vista) que las vistas posteriores apliquen sin duplicar lógica
- [x] Abrir la ficha de un Tutor queda registrado con Usuario y momento
- [x] La tabla no admite `UPDATE` ni `DELETE`: restringido a nivel de permisos de base de datos, no solo de aplicación
- [x] El admin de la Clínica consulta el registro filtrando por Usuario, por objeto y por rango de fechas
- [x] Test que comprueba que un intento de modificar o borrar una anotación falla
- [x] El registro está aislado por Clínica como cualquier otro dato

## Comments

**Decorador y no mixin**: las vistas de Gatabase son funciones, así que el mecanismo reutilizable es `@deja_constancia(accion, sobre=Modelo)` (`apps/audit/registro.py`). Anota después de que la vista responda y solo si respondió: un 404 —el Tutor es de otra Clínica— no llegó a servir ningún dato, y anotarlo llenaría de accesos falsos la tabla que tiene que valer como prueba. Cuando lo accedido no sale de la URL —un formulario que acaba de guardar, una exportación—, la vista llama a `anotar` con el objeto en la mano.

**El tipo del objeto se guarda como texto** (`tutors.Tutor`), no como clave ajena: así `audit` sigue sin importar de ninguna app de dominio y el Registro sobrevive a que un modelo se renombre o desaparezca.

**Dos cierres, no uno**, para el `UPDATE`/`DELETE` (`apps/audit/migrations/0002_registro_inalterable.py`): se le retiran los permisos al rol de la aplicación —lo que pide el ticket— **y** un disparador hace reventar la operación. Hacen falta los dos porque el rol de desarrollo es superusuario de Postgres y se salta los permisos; el disparador no se lo salta nadie. Ambas mitades tienen test: una intenta la operación, la otra mira el ACL de la tabla, que es lo único que se puede comprobar cuando el rol de test es superusuario.

`TRUNCATE` entra también en el `REVOKE`: vaciar la tabla de un golpe borra tanto como un `DELETE` y el disparador de fila no lo alcanza. No se le pone disparador propio para que las herramientas de test —que corren como superusuario— puedan seguir vaciando la tabla. De ahí la **condición de despliegue** que queda escrita en el README: en producción la aplicación se conecta con un rol que no es superusuario, y si se migra con otro rol hay que retirarle a ese los mismos tres permisos.

**Consecuencia buscada**: borrar una Clínica con accesos anotados falla, porque el borrado en cascada tropieza con el disparador. Una Clínica que se va se exporta y se cierra (ticket 19); no se borra por debajo, y los datos de desarrollo del ticket 16 se rehacen recreando la base. Por lo mismo, `usuario` es `PROTECT`: una anotación sin autor no es evidencia de nada.

**La mitad de "modifica"** del enunciado no tiene todavía vista que la dispare: en el sistema no hay ninguna pantalla que modifique datos de Tutor o de Paciente —llegan con el ticket 05—. El camino existe y está probado: `anotar(usuario, Accion.MODIFICACION, tutor)`, que es por donde entrarán esas vistas.

**El filtro falla cerrado**: una fecha que no se entiende no devuelve nada. Devolver el Registro entero sería la forma de que alguien se lleve la lista completa de accesos creyendo que pidió una búsqueda concreta.

**El listado de Tutores también deja constancia**, con el identificador vacío: lo servido fue el conjunto. La invariante de `CLAUDE.md` habla de toda lectura de datos de Tutor, y un listado enseña nombres y teléfonos.

**La página de consulta no se anota a sí misma**: el Registro no contiene datos personales de Tutor ni de Paciente, y anotarla solo la llenaría de ruido.

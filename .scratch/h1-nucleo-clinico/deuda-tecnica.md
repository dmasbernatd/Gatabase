# Deuda técnica y cabos sueltos de H1

Lo que se va acumulando y no cabe en ningún ticket concreto. Cada punto dice qué
pasa, por qué importa y cuándo se paga. Si un punto crece hasta merecer trabajo
propio, se convierte en un issue numerado y aquí queda solo el enlace.

## Proceso

**El trabajo terminado se queda en worktrees sin integrar.** El ticket 04 estuvo
completo y con tests verdes en `worktree-04-registro-de-acceso` desde el 17 de
agosto de 2026, y `main` no lo tuvo hasta el 23. Mientras tanto, `main` recibió
dos commits de documentación que describían como "pendiente de integrar" algo ya
hecho. El coste no es el retraso: es que cada día que pasa, la rama y `main`
divergen y la integración deja de ser un `cherry-pick` limpio.
_Cuándo se paga_: al terminar un ticket en un worktree, integrarlo en `main` en
la misma sesión y liberar el worktree.

**El ticket 05 cuelga de un commit huérfano.** `cbe66c2` (fichas de Tutor con
listado paginado, ordenable y buscable) está sobre `177eaa3`, que se integró en
`main` como `74214d9` — otro commit, otro sha. Cherry-pickear `cbe66c2` a ciegas
volvería a aplicar cosas que ya están.
_Cuándo se paga_: al empezar el 05. Se **rebasa** la rama sobre `main`, no se
cherry-pickea. El worktree está `locked`; hay que desbloquearlo antes.

**`main` local va por delante de `origin`** en los dos commits de la integración
del 04, sin empujar. La rama del worktree sí está en `origin`.

## Documentación

**La sección de Estado del README se escribe a mano y envejece sola.** Ya trajo
tres errores en un solo commit: un contador de tests obsoleto (50 cuando eran
75), un enlace a un ADR con nombre de archivo inventado, y una descripción del
Tutor con RUT y datos de contacto que corresponde a los tickets 05 y 06 y no
estaba en `main`.
_Cuándo se paga_: o se revisa en cada integración, o el README deja de prometer
números y listas de campos y remite al tracker. Lo segundo es más barato.

## Operación

**La condición de despliegue de ADR-0004 no la comprueba nadie.** La
inalterabilidad del Registro de acceso depende de que la aplicación se conecte
con un rol que **no** sea superusuario de Postgres, y de que, si un despliegue
migra con un rol distinto del de la aplicación, se le retiren a ese otro los
mismos `UPDATE`, `DELETE` y `TRUNCATE`. Hoy eso solo está escrito en el README y
en la migración `audit/0002`. En una máquina de desarrollo el disparador tapa el
agujero; en producción, si el rol es superusuario, la garantía es de papel.
_Cuándo se paga_: cuando exista despliegue. Lo natural es un `check` de Django
que falle con `DEBUG=False` si el rol de la conexión es superusuario.

**Borrar una Clínica ya no es posible** mientras tenga accesos anotados: la
cascada tropieza con el disparador de `audit`. Es la consecuencia buscada, pero
condiciona dos tickets que aún no se han escrito pensando en ella.
_Cuándo se paga_: en el **16** (datos mock: se rehace la base, no se borra la
Clínica por debajo) y en el **19** (una Clínica que se va se exporta y se
cierra, no se borra).

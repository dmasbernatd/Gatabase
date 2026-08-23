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
_Pagado el 23 de agosto de 2026_ en lo que quedaba pendiente: el commit del 05
se rebasó sobre `main`, se integró en avance rápido, y el worktree y su rama
local se liberaron. La regla sigue en pie para el próximo ticket.

**`main` local iba por delante de `origin`**, y la rama remota del worktree
seguía apuntando al commit de antes del rebase.
_Pagado el 23 de agosto de 2026_: `main` empujado en avance rápido y
`origin/worktree-04-registro-de-acceso` borrada, porque ya no tenía nada que no
estuviera en `main`.

## Documentación

**La sección de Estado del README se escribía a mano y envejecía sola.** Trajo
tres errores en un solo commit: un contador de tests obsoleto, un enlace a un
ADR con nombre de archivo inventado, y una descripción del Tutor que
correspondía a tickets aún sin integrar.
_Pagado el 23 de agosto de 2026_: la sección ya no promete contadores ni listas
de campos y remite al tracker, que es lo que se actualiza al trabajar.
_Lo que queda vivo_: el resto del README sí describe mecanismos con nombres de
archivo y de función. Eso envejece igual, pero se nota al leer el código; los
números no.

## Operación

**Borrar una Clínica no es posible** mientras tenga accesos anotados: la cascada
tropieza con el disparador de `audit`. Es la consecuencia buscada, pero
condiciona dos tickets.
_Pagado a medias el 23 de agosto de 2026_: la consecuencia está anotada como
casilla en el **16** (limpiar es rehacer la base, no borrar la Clínica) y en el
**19** (una Clínica que se va se exporta y se cierra). Lo que falta es decidir
**qué significa cerrar una Clínica** — desactivar a sus Usuarios, dejarla sin
acceso, algo más —, y eso se decide al hacer el 19.

## Rendimiento

**«Usable con cientos de Tutores» está afirmado, no sostenido.** Es una casilla
del ticket 05 que se dio por cumplida porque el listado pagina, y paginar no es
lo mismo que aguantar. Debajo hay tres cosas que nadie mide:

- El único índice del Tutor (`tutor_por_apellidos`: `clinic`, `apellidos`,
  `nombre`) sirve al orden por defecto. Ordenar por nombre, teléfono o correo
  —las otras tres cabeceras que el listado ofrece— es recorrer y ordenar en
  memoria toda la Clínica.
- La búsqueda es `icontains`, o sea un `LIKE '%…%'` por cada palabra y cada uno
  de los cuatro campos buscables. Con comodín delante, ningún índice normal
  entra: es lectura secuencial de la tabla.
- El `Paginator` hace su `COUNT(*)` de la consulta completa en cada petición,
  incluida cada búsqueda.

A cientos de Tutores esto no se nota, y por eso no es un fallo hoy. Lo que falta
no es optimizar a ciegas: es que **nada avise cuando deje de aguantar**. La
batería entra por HTTP y comprueba lo que el Usuario observa, que es lo correcto,
pero no cuenta consultas ni prueba a escala, así que una regresión de rendimiento
—un `N+1` al pintar la tabla, pongamos— pasaría entera y en verde.
_Cuándo se paga_: en el **16**, que es quien trae volumen de verdad. Con datos
mock encima, un `assertNumQueries` sobre el listado y la búsqueda deja de ser
teatro y empieza a defender algo. La decisión sobre índices y sobre buscar en
serio —tolerante a tildes, incremental— es del **11**, y conviene tomarla con
el volumen del 16 delante y no antes.

## Pagado

**La condición de despliegue de ADR-0004 ya la comprueba alguien.**
`apps/audit/comprobaciones.py` registra un `check` de Django que, con `DEBUG`
apagado y fuera de la batería de tests, le pregunta a Postgres por la conexión
de la aplicación si su rol podría modificar el Registro de acceso: `audit.E001`
si es superusuario, `audit.E002` si conserva los permisos, `audit.W001` si la
base no responde. Verificado a mano contra un rol no superusuario, con y sin los
permisos retirados. Tests en `tests/test_condicion_de_despliegue.py`.

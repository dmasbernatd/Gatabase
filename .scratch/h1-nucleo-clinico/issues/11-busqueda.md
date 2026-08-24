# 11 — Búsqueda de Tutores y Pacientes

**What to build:** recepción está al teléfono con un Tutor y encuentra al Paciente en segundos, escribiendo lo primero que tenga a mano: un nombre, un teléfono o un número de chip. Es la funcionalidad que hace que el sistema gane al archivador.

**Blocked by:** 06, 07, 08

**Status:** done

- [x] Una única caja de búsqueda que acepta nombre de Paciente, nombre de Tutor, teléfono, RUT o microchip, sin que el Usuario tenga que elegir el campo
- [x] Búsqueda tolerante a tildes y a mayúsculas, y a teléfonos escritos de cualquiera de las formas habituales
- [x] Resultados que muestran Paciente, especie, Tutor responsable y teléfono, para poder confirmar por voz que es el correcto
- [x] Respuesta rápida con el volumen de datos mock de una clínica real
- [x] Resultados incrementales con HTMX mientras se escribe
- [x] Los Pacientes fallecidos e inactivos aparecen marcados, no ocultos, porque a veces se busca precisamente a ellos
- [x] Ningún resultado de otra Clínica, comprobado por test
- [x] La búsqueda no registra un acceso por cada resultado listado; el Registro de acceso se escribe al abrir una ficha


## Comments

Hecho. Una caja en `panel/buscar/` que encuentra **Pacientes** escribiendo lo
primero que haya a mano, y una decisión que la sostiene entera: **lo escrito es
un número dictado o es un nombre, y no las dos cosas.** Lo separa si trae letras
—salvo la `K` con la que puede acabar un RUT—. Un número se lee de la caja
entera, porque sus espacios son puntuación y no separadores: partir «9 8765
4321» o «900 123 456 789 012» por el espacio deja trozos de tres dígitos que no
identifican a nadie. Un nombre se lee palabra a palabra y cada una puede caer en
un campo distinto, que es como recepción escribe «camila rojas».

La mecánica vive en `apps/busqueda.py`, fuera de las dos apps porque las dos la
necesitan y ninguna puede importar de la otra; por dónde se busca a cada uno lo
dice el modelo (`Tutor.POR_DONDE_SE_BUSCA`, `Paciente.POR_DONDE_SE_BUSCA`), al
lado de `DATOS_PERSONALES` y por el mismo motivo: es un hecho suyo, no de una
pantalla. El fichero de Tutores del 05 pasó a leer lo escrito con esa misma
mecánica, así que ganó las tildes de paso y no hay dos definiciones de «cómo se
encuentra a un Tutor».

**Las tildes se pliegan con `translate` y no con la extensión `unaccent`**, que
sería lo idiomático en Postgres. No es gusto: `CREATE EXTENSION` pide
superusuario y el rol de la aplicación no lo es a propósito —ADR-0004 monta un
`check` que **falla** si lo fuera—, así que esa migración no correría en
producción. La tabla de acentos está escrita una vez y la usan los dos lados,
Python y SQL, para que el plegado sea el mismo en los dos.

**Un RUT o un chip que llegan enteros se buscan por igualdad**, y eso era lo que
la deuda del 05 pedía decidir aquí: la igualdad usa los índices que ya existían
—`rut_unico_dentro_de_la_clinica`, `paciente_por_microchip`— y no hizo falta
ninguno nuevo. Además distingue: dictado entero, «1234567-4» trae a esa persona
y no a quien lo lleva dentro de un RUT de ocho dígitos. Un trozo suelto sigue
siendo un barrido, y eso se mide en el **16**, no antes.

**Lo que se encuentra son Pacientes**, aunque se escriba el nombre de una
persona: la pregunta del mostrador es de qué animal habla quien llama. Y se
busca entre quienes responden **hoy** — un Vínculo cerrado no encuentra al
Paciente, porque la fila diría un Tutor responsable que no es el que se acaba de
teclear.

**No se pagina y no se cuenta.** La lista se repinta cada 250 ms mientras se
escribe, así que un `COUNT(*)` de la consulta completa se pagaría en cada tecla
para enseñar un número que nadie mira. Se traen veinte y uno de más: con el
sobrante se sabe que hay más sin haber contado nada.

**El Registro anota el conjunto, no cada resultado.** Es la misma regla que ya
seguía el listado de Tutores, y aquí importa más: anotar los veinte nombres que
pasan por delante mientras alguien escribe dejaría un Registro donde no se
distingue a quién se consultó de verdad. La lectura de una persona se anota al
abrir su ficha. La página con la caja vacía no anota nada, porque no sirvió dato
de nadie.

**La casilla del volumen está cumplida solo hasta donde se puede hoy.** No hay
datos mock —son del **16**—, así que lo que hay es volumen fabricado por el
propio test: ochocientos Pacientes con sus Tutores, y la exigencia de que buscar
con uno y con sesenta resultados cueste las mismas consultas, que es la red
contra el `N+1` de pintar quién responde por cada animal. Lo que **no** hay es
una medida de tiempo ni nombres que colisionen entre sí, y eso llega con el 16.

El orden de los resultados es alfabético y no sabe de estados. Lo primero que se
escribió fue «los activos delante», que suena razonable y era un fallo: como la
lista se corta en veinte, poner detrás a los fallecidos es esconderlos en toda
búsqueda amplia, que es exactamente lo que la casilla de «marcados, no ocultos»
prohíbe. Lo pilló la revisión y ahora hay un test con más coincidencias de las
que caben.

Lo que queda anotado en `deuda-tecnica.md`: la caja vive en una página propia y
no en la cabecera del panel; un Tutor sin Pacientes no sale por ella; cada
búsqueda escribe dos filas en el Registro; buscar un dígito suelto en el fichero
de Tutores ya no devuelve a nadie; y la medida de verdad del rendimiento sigue
esperando al **16**.

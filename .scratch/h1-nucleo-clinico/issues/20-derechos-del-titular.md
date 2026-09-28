# 20 — Derechos del titular: acceso y supresión de un Tutor

**What to build:** un Tutor pide sus datos, o pide que los borren, y la clínica puede atenderlo sin destruir información clínica que tiene deber de conservar. Es la obligación que la Ley 21.719 hace exigible desde el 1 de diciembre de 2026.

La tensión que este ticket resuelve: el derecho de supresión alcanza a los datos personales del Tutor, no a la información clínica del Paciente, que es de otro titular y tiene que conservarse.

**Blocked by:** 19

**Status:** done

- [x] Exportación de los datos personales de **un** Tutor concreto, en formato legible, para atender su derecho de acceso
- [x] La exportación individual incluye el Registro de acceso a sus propios datos: quién los vio y cuándo
- [x] Anonimización de un Tutor: sus datos personales identificativos se sustituyen de forma irreversible
- [x] Tras anonimizar, el Paciente **permanece íntegro** con toda su información y sus vínculos, atribuido a un Tutor anonimizado
- [x] La anonimización no rompe ningún listado, búsqueda ni ficha de Paciente
- [x] La operación exige confirmación explícita y queda registrada con quién la ejecutó y cuándo, porque es irreversible
- [x] Solo el rol admin puede ejecutarla
- [x] Test que anonimiza un Tutor con dos Pacientes y comprueba que los datos personales desaparecieron y que ambos Pacientes siguen completos y consultables
- [x] Test de que el Registro de acceso del propio Tutor sobrevive a su anonimización, porque es la evidencia del tratamiento

## Comments

**Hecho el 28 de septiembre de 2026.** Las dos operaciones viven en
`apps/tutors/derechos.py` y la página que las ofrece cuelga de la ficha del
Tutor (`/panel/tutores/<pk>/derechos/`), solo para el admin.

**Qué significa anonimizar.** Vaciar `Tutor.DATOS_PERSONALES` y anotar desde
cuándo en `Tutor.anonimizado`, en una transacción con la anotación del Registro,
que usa una acción propia —`anonimización`— para que se pueda encontrar sola.
Se quedan los Vínculos (quién trajo al animal es Historia del Paciente) y los
Consentimientos (evidencia de los mensajes que ya salieron; sin nombre ni
teléfono no identifican a nadie). Un Tutor anonimizado se presenta como «Tutor
anonimizado» en ficha, fichero, mostrador y ficha de Paciente; no se corrige, no
se le toma el consentimiento, no se le suma ni se le traspasa ningún animal y
`se_puede_contactar` le dice que no a todo. Se confirma escribiendo su nombre,
como el cierre de la Clínica.

**El documento del titular es un HTML autocontenido**, no un zip de planillas:
lo lee la persona que pidió sus datos, no el Excel de otro sistema, y un
navegador lo abre, lo imprime y lo guarda como PDF. Va por POST y no queda en
ninguna parte, igual que la exportación del **19**. Trae los accesos anotados
sobre su ficha y dice que los del conjunto no se le atribuyen (ver
`deuda-tecnica.md`).

**Lo que destapó un test:** el aviso de «se han suprimido los datos de Fulano»
guardaba el nombre en la sesión, que vive en la base. El aviso ya no nombra a
nadie.

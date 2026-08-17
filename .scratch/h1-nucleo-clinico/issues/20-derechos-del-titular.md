# 20 — Derechos del titular: acceso y supresión de un Tutor

**What to build:** un Tutor pide sus datos, o pide que los borren, y la clínica puede atenderlo sin destruir información clínica que tiene deber de conservar. Es la obligación que la Ley 21.719 hace exigible desde el 1 de diciembre de 2026.

La tensión que este ticket resuelve: el derecho de supresión alcanza a los datos personales del Tutor, no a la información clínica del Paciente, que es de otro titular y tiene que conservarse.

**Blocked by:** 19

**Status:** ready-for-agent

- [ ] Exportación de los datos personales de **un** Tutor concreto, en formato legible, para atender su derecho de acceso
- [ ] La exportación individual incluye el Registro de acceso a sus propios datos: quién los vio y cuándo
- [ ] Anonimización de un Tutor: sus datos personales identificativos se sustituyen de forma irreversible
- [ ] Tras anonimizar, el Paciente **permanece íntegro** con toda su información y sus vínculos, atribuido a un Tutor anonimizado
- [ ] La anonimización no rompe ningún listado, búsqueda ni ficha de Paciente
- [ ] La operación exige confirmación explícita y queda registrada con quién la ejecutó y cuándo, porque es irreversible
- [ ] Solo el rol admin puede ejecutarla
- [ ] Test que anonimiza un Tutor con dos Pacientes y comprueba que los datos personales desaparecieron y que ambos Pacientes siguen completos y consultables
- [ ] Test de que el Registro de acceso del propio Tutor sobrevive a su anonimización, porque es la evidencia del tratamiento

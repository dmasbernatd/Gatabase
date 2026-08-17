# 08 — Microchip y estado de identificación

**What to build:** recepción registra el microchip del Paciente y ve de un golpe qué le falta al Tutor para cumplir la Ley 21.020. El chip pasa a ser una forma de encontrar al animal.

**Blocked by:** 07

**Status:** ready-for-agent

- [ ] Número de microchip **opcional**, de 15 dígitos, validado en formato
- [ ] Estado de identificación como campo propio y distinto de "tiene chip": `sin chip`, `chip implantado`, `inscrito en el Registro Nacional`
- [ ] Microchip **único dentro de la Clínica**; el intento de repetirlo se rechaza con enlace a la ficha que ya lo tiene
- [ ] El microchip **no** es único a nivel global ni se cruza entre Clínicas (ADR-0001). Si el mismo número existe en otra Clínica, es correcto y no se detecta
- [ ] La ficha del Paciente muestra el estado de identificación de forma visible, para poder decírselo al Tutor
- [ ] Test que comprueba explícitamente que dos Clínicas pueden tener el mismo número de chip sin conflicto

# 18 — Importador CSV de Pacientes con vínculo a Tutores

**What to build:** el admin sube su planilla de animales y el sistema los vincula a los Tutores ya importados. Es la parte difícil de la migración: la planilla real identifica al dueño por un nombre escrito a mano, no por un identificador.

**Blocked by:** 08, 17

**Status:** done

- [x] Subida de un CSV de Pacientes con nombre, especie, raza, sexo, fecha de nacimiento, color, microchip e identificación del Tutor
- [x] Resolución del Tutor por RUT, o por teléfono, o por nombre; cuando la coincidencia es ambigua, la fila se rechaza con un mensaje que dice entre qué Tutores dudó
- [x] Especie no reconocida: la fila se rechaza indicando las especies válidas, porque el catálogo es cerrado por diseño
- [x] Raza no reconocida: se importa como `otra` con el texto original conservado, en lugar de rechazar la fila
- [x] Microchip repetido dentro de la Clínica: la fila se rechaza indicando qué Paciente ya lo tiene
- [x] Fecha de nacimiento en varios formatos habituales de planilla, y ausente sin que rompa
- [x] Vista previa antes de confirmar e informe de errores fila a fila, igual que en el ticket 17
- [x] Reimportar el mismo archivo no duplica Pacientes ni vínculos
- [x] La importación queda en el Registro de acceso
- [x] **El histórico clínico no se importa** y el sistema no ofrece hacerlo: migrar historias en texto libre es un pozo sin fondo, y la digitalización empieza en la primera Consulta nueva
- [x] Tests de resolución de Tutor por cada vía, de ambigüedad, de especie inválida, de raza desconocida y de reimportación

## Comments

**Hecho el 25 de agosto de 2026.** El importador de Pacientes salió de dividir el
del 17 por donde ya estaba partido: `planilla.py` e `informe.py` no sabían de
Tutores, y ahora tampoco saben de Pacientes. Lo nuevo es `pacientes.py` —qué se
lee de cada fila y qué se guarda— y `importadores.py`, que es el contrato que
declaran los dos módulos para que la vista previa, el informe y la confirmación
sean las **mismas tres páginas** para las dos planillas. La alternativa era
copiar las vistas y las plantillas cambiando las palabras, y la copia envejece
de a una.

**Lo difícil no era el animal: era de quién es.** El Tutor se resuelve por RUT,
por teléfono o por nombre, y las dos últimas se **acumulan** en vez de turnarse:
una familia comparte número —tres Tutores con el mismo teléfono es lo corriente—
y el nombre es lo que desempata. El nombre se compara plegado y con sus palabras
ordenadas, porque una planilla escribe «Rojas Camila» tan a menudo como «Camila
Rojas». Lo que **no** se hace es partirlo en trozos y buscar el que más se
parezca: un «Rojas» a secas se parece a media clínica.

**Cuando quedan dos, la fila no entra**, y el motivo lleva el RUT de cada
candidato al lado — dos personas del mismo nombre no se distinguen por el
nombre, que es justo lo que las hizo dudosas. Elegir la primera sería el error
que nadie ve: el animal colgado de la persona equivocada, y quien lo descubre es
el veterinario que llama a un número que no contesta.

**El RUT decide solo, y si no es de nadie la fila se rechaza** en vez de caer al
nombre: un RUT que no cuadra es un dato mal tecleado, y resolverlo por parecido
sería inventar.

**Un chip que ya es de otro Paciente no es una fila repetida.** Es el mismo
número en dos animales, que la base tampoco admite (ADR-0001) y que nadie puede
resolver desde aquí sin adivinar cuál lo lleva puesto: se rechaza nombrando al
Paciente que ya lo tiene. Cuando el chip es de un animal que **sí** se llama
igual, es la misma ficha y se salta sin molestar a nadie, que es lo que sostiene
la reimportación.

**El Vínculo lo escribe el Tutor** (`se_hace_cargo_de`), una consulta por fila, y
no un `bulk_create`: quién responde por un Paciente es una regla del dominio, y
escribirla otra vez aquí para ahorrar consultas dejaría dos definiciones de lo
que es hacerse cargo de un animal.

**Los dos archivos de ejemplo se importan uno detrás de otro**, porque el de
Pacientes apunta a los Tutores del de Tutores por RUT y por nombre. El test los
importa en ese orden, que es el de una migración de verdad, y de paso comprueba
que las tres vías de resolución están documentadas y funcionan.

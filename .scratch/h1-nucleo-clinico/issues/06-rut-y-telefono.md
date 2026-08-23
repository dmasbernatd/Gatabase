# 06 — RUT validado y teléfono normalizado

**What to build:** recepción escribe el RUT como se lo dicten y el sistema lo guarda de una sola forma, avisando si está mal o si ya existe. El teléfono queda en un formato con el que después se pueda contactar sin ambigüedad.

**Blocked by:** 05

**Status:** done

- [x] RUT **opcional**: se puede registrar un Tutor extranjero o que no quiere darlo
- [x] Validación del dígito verificador al guardar, con mensaje claro cuando falla
- [x] Almacenamiento normalizado sin puntos ni guion, y presentación con formato chileno
- [x] RUT único dentro de la Clínica cuando está presente; aviso si ya existe, con enlace a la ficha existente
- [x] Teléfono normalizado a E.164 aceptando las formas en que se escribe en Chile (con y sin `+56`, con y sin `9`, con espacios)
- [x] Teléfono **no único**: se permite compartido entre Tutores de una familia, con aviso al guardar
- [x] Tests de dígito verificador correcto, incorrecto, con `K`, y de ausencia de RUT
- [x] Tests de normalización de teléfono para cada forma de escritura habitual

## Comments

**23 de agosto de 2026 — hecho.** Todas las casillas, con la batería en verde
(176 tests).

Dónde quedó cada cosa:

- Leer un RUT y un teléfono escritos como se dictan es de `apps/tutors/rut.py` y
  `apps/tutors/telefono.py`: funciones puras, con sus tests en
  `tests/test_rut_y_telefono.py`. Nada de esto vive en una vista ni en una
  plantilla, y el importador del **17** lo va a reutilizar tal cual.
- Normalizar no es validar: son **campos de modelo** (`apps/tutors/campos.py`),
  no validadores. Un validador corre cuando el valor ya está puesto, así que
  dejaría entrar «12.345.678-5» y «123456785» como dos cosas distintas y las dos
  válidas, y el RUT único por Clínica no significaría nada. Puestos en el modelo,
  la normalización ocurre venga el dato del formulario, de un comando o de una
  fábrica.
- El RUT es único dentro de la Clínica con una `UniqueConstraint` condicionada a
  `rut != ""`: dos Tutores sin RUT no son el mismo Tutor. Nunca a nivel global
  (ADR-0003), y hay un test que registra el mismo RUT en dos Clínicas.
- Los dos avisos acaban distinto a propósito: **el RUT repetido no deja
  guardar** —con enlace a la ficha que ya existe, que es a lo que recepción
  venía— y **el teléfono compartido sí**, porque una familia comparte número.
  Ese se avisa después de guardar, con `django.contrib.messages`, que hasta ahora
  no se usaba: los avisos se pintan en `templates/base.html`.
- Los dos avisos dicen el nombre del otro Tutor, y decirlo es enseñar un dato
  personal: los dos dejan constancia en el Registro de acceso como si se hubiera
  abierto su ficha (ADR-0004). Es la primera lectura del sistema que no viene de
  abrir una página.

Dos cosas que se decidieron por el camino y no estaban en el ticket:

- **Buscar por RUT y por teléfono con la puntuación con que se teclean.**
  `CAMPOS_BUSCABLES` pasó de tupla a diccionario: cada campo dice cómo hay que
  leer lo escrito para buscar en él. Sin eso, buscar «12.345.678» no encontraría
  nunca al Tutor cuyo RUT se guardó de corrido. Un campo se salta cuando la
  palabra, leída a su manera, se queda en nada — si no, buscar «camila» pediría
  `telefono__icontains=""` y traería a toda la Clínica.
- **`FormularioDeLaClinica.los_demas()`** (`apps/tenancy/aislamiento.py`): los
  objetos que ya hay en la Clínica menos el que se está editando. Es lo que
  necesitan las dos comprobaciones, y es lo que va a necesitar el microchip del
  **08**.

Lo que **no** se hizo, a propósito: el teléfono se presenta tal cual, en E.164.
Ya es inequívoco, y darle formato solo añadiría una segunda forma de escribirlo
en la pantalla.

**Efecto colateral:** `tests/test_registro_de_acceso.py` comparaba
identificadores «111» y «999» contra la página entera, y las Clínicas y Sedes de
las fábricas se numeran por secuencia. Con los tests nuevos por delante, la
secuencia llegó a 111 y el test falló por una «Clínica Veterinaria 111» que no
tenía nada que ver. Ahora son `pk-111` y `pk-999`, que no se pueden confundir con
un número de escenario.

# 16 — Datos mock por comando de gestión

**What to build:** un comando que llena el sistema con datos verosímiles de una clínica chilena de una sede, para poder desarrollar contra volumen real, medir si la búsqueda es rápida y demostrarle el sistema a la clínica piloto sin usar datos de clientes reales.

**Blocked by:** 08

**Status:** done

- [x] Comando de gestión que genera dos Clínicas con Sedes, Usuarios de los tres roles, Tutores y Pacientes
- [x] **Dos** Clínicas y no una: es lo que permite comprobar el aislamiento a mano, además de por test
- [x] Volumen realista de una clínica de una sede, suficiente para que un listado y una búsqueda lentos se noten
- [x] Nombres, teléfonos y RUT verosímiles para Chile, con dígito verificador válido
- [x] Mezcla realista de especies con predominio de caninos y felinos, razas del catálogo con mayoría de `mestizo`, y algunos exóticos
- [x] Casos límite incluidos a propósito: Paciente sin chip, Paciente fallecido, Tutor sin RUT, Tutor extranjero, dos Tutores con el mismo teléfono, Paciente con dos Tutores
- [x] El comando es idempotente o limpia lo anterior, para poder ejecutarlo repetidamente. **Limpiar no es borrar la Clínica**: el Registro de acceso no admite `DELETE`, así que el borrado en cascada de una Clínica con accesos anotados falla (ADR-0004, migración `audit/0002`). Se rehace la base — `dropdb`/`migrate`, o el contenedor de `scripts/db.sh` de nuevo — y se vuelve a poblar.
- [x] El comando se niega a ejecutarse contra una base de producción

## Comments

Implementado en `apps/imports/mock.py` (quién inventa los datos) y
`apps/imports/management/commands/datos_mock.py` (la puerta). Decisiones que no
estaban en el ticket y que conviene tener a mano:

- **Vive en `imports` y no en `tenancy`.** El comando escribe Tutores y
  Pacientes, y `tenancy` no importa de ninguna app de dominio (`CLAUDE.md`): todas
  importan de ella. De las que sí pueden verlo todo, `imports` es la que mueve
  datos en bloque hacia dentro y hacia fuera de una Clínica, que es lo que aquí
  se hace. Los tickets 17, 18 y 19 caen al lado.

- **Los casos límite se ponen a propósito, no se esperan del azar.** Van en los
  índices fijos de las primeras fichas de cada Clínica (`CASO_SIN_RUT` y los
  demás, todos juntos al principio del módulo), porque el comando tiene que dar
  lo mismo con `--tutores 20` que con 3000 — y con 20 el azar no produce un
  Tutor extranjero. El resumen final dice **en qué ficha** quedó cada uno: sin
  eso hay que ir a buscarlos, y en una demostración no se buscan.
  Se añadieron dos que el ticket no pedía y que la ficha enseña distinto: el
  Tutor que se desdijo del contacto y aquel del que no consta nada (ticket 15).

- **La semilla lleva el nombre de la Clínica** (`f"{semilla}:{plantilla.nombre}"`),
  así que las dos no salen calcadas. Dos copias idénticas no servirían para lo
  único que justifica que sean dos: mirar el aislamiento a mano.

- **Rehace en vez de borrar la Clínica**, como el ticket adelantaba. `limpiar`
  borra los Tutores y los Pacientes —los Vínculos y los Consentimientos van en
  cascada detrás— y deja en pie la Clínica, su Sede y sus Usuarios. Además de
  esquivar el `DELETE` que el Registro de acceso no admite (ADR-0004), tiene un
  efecto que se agradece: las contraseñas de la demostración siguen sirviendo
  entre una ejecución y la siguiente.

- **La negativa contra producción acabó siendo más estrecha de lo previsto**, y
  el motivo salió de correrla: una base de desarrollo tiene siempre Clínicas
  hechas a mano —«Clínica de humo», «Veterinaria Ñuñoa»—, así que negarse por su
  presencia habría convertido el aviso en un estorbo diario, que es como se
  acaban desactivando. Queda así: con `DEBUG` encendido corre sin preguntar y no
  toca esas Clínicas; con `DEBUG` apagado se niega, y si además hay Clínicas
  ajenas se niega sin apelación —eso es una base con clientes—. El despliegue de
  la demostración se pide con `--aunque-no-sea-desarrollo`.

- **Volumen**: 3000 Tutores y ~4600 Pacientes en la Clínica grande, 600 y ~900
  en la pequeña. Tarda unos 5 segundos en escribirlo todo (`bulk_create` por
  lotes de 500). Es el tamaño de una clínica de una sede con unos años de
  historia, elegido para que un listado o una búsqueda mal resueltos se noten al
  abrirlos.

- **La batería de tests corre con `DEBUG` apagado**, así que los tests lo
  encienden con la *fixture* `settings`. No se añadió un rodeo del tipo
  `en_la_bateria_de_tests` a propósito: la negativa es justo lo que hay que
  probar, y un atajo para los tests la dejaría sin probar de verdad.

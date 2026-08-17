---
status: accepted
---

# Registro de acceso propio, porque hay que registrar lecturas

El Registro de acceso se implementa como una tabla propia, append-only, escrita desde las vistas. Descartamos `django-auditlog` y `django-simple-history` como mecanismo principal por un motivo concreto: registran **modificaciones** mediante señales de modelo, y la Ley 21.719 obliga a poder demostrar **quién vio** un dato personal. Leer no dispara ninguna señal, así que ninguna librería basada en señales puede capturar una lectura.

Vigente desde el 1 de diciembre de 2026, la ley exige atender derechos de acceso, notificar brechas en 72 horas y mantener registro de las actividades de tratamiento. Nada de eso se puede reconstruir a posteriori: es la única pieza del sistema que, si no está desde el primer día, no se puede añadir con efecto retroactivo.

## Consecuencias

- El acceso a una ficha de Paciente, a los datos de un Tutor, a un Adjunto o a una Conversación se registra en el momento de servirlo.
- La tabla no admite `UPDATE` ni `DELETE`; se restringe a nivel de permisos de base de datos, no solo de aplicación.
- Los datos del Tutor y los datos clínicos del Paciente se modelan separados, porque un Tutor puede exigir la supresión de sus datos personales mientras la Historia clínica del Paciente debe conservarse.
- `django-auditlog` puede añadirse encima para el diff campo a campo de las escrituras. Es complementario, no sustituto.

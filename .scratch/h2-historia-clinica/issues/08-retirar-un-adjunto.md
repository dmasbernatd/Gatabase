# 08 — Retirar un Adjunto subido por error

**What to build:** quien se equivocó de archivo lo retira. No se borra el registro: el Adjunto queda marcado como retirado, con quién y cuándo, y deja de ofrecerse para descargar.

**Blocked by:** 07

**Status:** ready-for-agent

- [ ] Retirar marca el Adjunto con momento, Usuario y motivo; el registro no se elimina
- [ ] El hilo de la Consulta sigue mostrando que hubo un Adjunto retirado, sin enlace de descarga
- [ ] Un Adjunto retirado no se descarga: la vista da 404 aunque se conozca su dirección
- [ ] Quién puede retirar se decide aquí (propuesta: quien lo subió, y el admin)
- [ ] Decidir si el objeto se borra del almacenamiento o solo se deja de servir, y anotarlo: retirar una radiografía de otro animal subida por error puede ser justamente lo que exige la protección de datos
- [ ] Retirar queda en el Registro de acceso como modificación
- [ ] Aislamiento por HTTP: retirar el Adjunto de otra Clínica da 404

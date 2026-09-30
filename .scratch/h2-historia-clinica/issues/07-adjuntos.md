# 07 — Adjuntos: subir, listar y descargar, en almacenamiento privado

**What to build:** el veterinario adjunta a la Consulta una radiografía, una ecografía, una foto de la lesión o el PDF del laboratorio, y lo descarga para verlo en grande. Los archivos son datos de salud: viven en un almacenamiento S3-compatible privado y solo se sirven con una URL firmada de vida corta.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Modelo `Adjunto` con `clinic`, Consulta, nombre original, tipo, tamaño, quién lo subió y cuándo
- [ ] Almacenamiento S3-compatible privado configurado por entorno (`STORAGES`); ningún objeto público, y la clave del objeto no es adivinable ni lleva datos del Paciente
- [ ] Almacenamiento falso en memoria para tests: **ningún test toca S3**
- [ ] Descargar pasa por una vista de Gatabase que comprueba Clínica y rol, anota y redirige a una URL firmada de vida corta; test de que la URL caduca y de que no hay acceso anónimo
- [ ] Tipos admitidos (imágenes, PDF) y tamaño máximo decididos aquí; lo demás se rechaza con un mensaje claro. Sin visor DICOM, sin miniaturas, sin edición
- [ ] Se adjunta a una Consulta abierta; a una **cerrada** también, porque el laboratorio llega días después: el Adjunto entra con su autor y su fecha en el hilo, igual que una Enmienda, y no altera lo escrito
- [ ] La Consulta lista sus Adjuntos en el hilo
- [ ] **Suite obligatoria — Registro de acceso**, segunda mitad: descargar un Adjunto queda registrado con Usuario y momento
- [ ] Aislamiento por HTTP: descargar el Adjunto de otra Clínica da 404
- [ ] Condición de despliegue escrita en el README (bucket, credenciales, que el bucket no tenga política pública) y, si se puede comprobar, un `check` de Django como el de `audit`

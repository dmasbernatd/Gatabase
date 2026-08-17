# 17 — Importador CSV de Tutores

**What to build:** el admin sube su planilla de clientes, ve qué filas están mal antes de que se guarde nada, corrige la planilla y vuelve a subirla sin que se dupliquen las que ya entraron. Sin esto, el sistema arranca vacío y compite con un archivador que sí tiene los datos.

**Blocked by:** 06, 16

**Status:** ready-for-agent

- [ ] Subida de un CSV de Tutores con nombre, apellidos, teléfono, correo, RUT y dirección
- [ ] Formato de planilla documentado, con un archivo de ejemplo descargable
- [ ] **Vista previa antes de confirmar**: cuántas filas se crearían, cuántas se saltarían y por qué
- [ ] Informe de errores **fila a fila** con el número de línea y el motivo, exportable para corregir la planilla
- [ ] Reutiliza la validación de RUT y la normalización de teléfono del ticket 06; no duplica reglas
- [ ] Una fila inválida no impide importar las válidas
- [ ] **Idempotencia**: reimportar el mismo archivo no crea duplicados, para poder importar por tandas
- [ ] La importación queda en el Registro de acceso, con quién importó, cuándo y cuántas filas
- [ ] Todo lo importado pertenece a la Clínica del Usuario que importa, sin posibilidad de indicar otra
- [ ] Tests de fila válida, fila con RUT inválido, fila con teléfono ilegible, fila duplicada dentro del propio archivo, y reimportación completa

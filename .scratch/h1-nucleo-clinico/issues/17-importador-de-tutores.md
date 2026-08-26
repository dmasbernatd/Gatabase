# 17 — Importador CSV de Tutores

**What to build:** el admin sube su planilla de clientes, ve qué filas están mal antes de que se guarde nada, corrige la planilla y vuelve a subirla sin que se dupliquen las que ya entraron. Sin esto, el sistema arranca vacío y compite con un archivador que sí tiene los datos.

**Blocked by:** 06, 16

**Status:** done

- [x] Subida de un CSV de Tutores con nombre, apellidos, teléfono, correo, RUT y dirección
- [x] Formato de planilla documentado, con un archivo de ejemplo descargable
- [x] **Vista previa antes de confirmar**: cuántas filas se crearían, cuántas se saltarían y por qué
- [x] Informe de errores **fila a fila** con el número de línea y el motivo, exportable para corregir la planilla
- [x] Reutiliza la validación de RUT y la normalización de teléfono del ticket 06; no duplica reglas
- [x] Una fila inválida no impide importar las válidas
- [x] **Idempotencia**: reimportar el mismo archivo no crea duplicados, para poder importar por tandas
- [x] La importación queda en el Registro de acceso, con quién importó, cuándo y cuántas filas
- [x] Todo lo importado pertenece a la Clínica del Usuario que importa, sin posibilidad de indicar otra
- [x] Tests de fila válida, fila con RUT inválido, fila con teléfono ilegible, fila duplicada dentro del propio archivo, y reimportación completa

## Comments

**Hecho el 25 de agosto de 2026.** La importación son dos páginas —subir y vista
previa— y cuatro módulos en `apps/imports/`, repartidos por lo que cada uno sabe:

- `planilla.py` lee bytes y devuelve filas con su número de línea. No sabe de
  Tutores: adivina el separador, la codificación y cómo se llamó cada columna,
  que es lo que cambia entre el Excel de una clínica y el de otra. El **18** lee
  su planilla de Pacientes por aquí.
- `informe.py` cuenta qué pasaría con cada fila y lo escribe como planilla
  descargable. Tampoco sabe de dominio.
- `tutores.py` decide lo único que es del dominio: qué hace de dos filas la misma
  persona, y qué se rechaza. La validación del RUT y del teléfono no se toca —
  entra por `FilaDeTutorForm`, que son los campos del Tutor sin la detección de
  coincidencias.
- `almacen.py` guarda la planilla entre las dos páginas, en disco y colgada de la
  sesión.

**La decisión incómoda: una fila sin RUT y sin teléfono se rechaza.** No es una
ficha mala —el mostrador registra a diario Tutores de los que solo se sabe el
nombre— pero no hay manera de reconocerla en una segunda subida, y aceptarla
sería prometer idempotencia y no cumplirla en silencio. Se rechaza diciéndolo.

**El informe de errores no se guarda.** No hace falta: reimportar la misma
planilla vuelve a decir exactamente qué falta y por qué, sin duplicar lo que ya
entró. Un informe guardado sería una segunda copia de datos personales
envejeciendo en el disco para responder algo que se puede volver a preguntar.

**El Registro de acceso anota una fila y no tres mil**, apuntando a un modelo
`Importacion` que lleva las cuentas. El Registro no sabe guardar «ciento veinte
filas», y una anotación por Tutor enterraría en ruido la tabla que tiene que
valer como prueba.

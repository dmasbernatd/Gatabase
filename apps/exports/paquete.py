"""El archivo que se descarga: un zip de planillas, escrito por trozos.

Dos decisiones, y las dos vienen de casillas del ticket.

**Un zip de CSV, y no un archivo propio.** «Formato abierto y legible por una
planilla» no admite un volcado del sistema: lo que se descarga se abre con dos
clics en el mismo Excel con el que la clínica llevaba su archivador antes. El zip
está ahí porque son varias tablas —Tutores, Pacientes, Vínculos, catálogos— y
juntarlas en una sola planilla obligaría a repetir cada Tutor una vez por animal.
Las planillas de dentro se escriben con las manías del Excel chileno —punto y
coma, saltos de Windows, marca de orden de bytes— y esa decisión no se toma aquí:
está en `apps/imports/planilla.py`, que es donde ya estaba para leerlas.

**Se escribe por trozos y no se guarda en ninguna parte.** Con los tres mil
Tutores de una clínica de verdad, armar el zip entero antes de mandarlo son
decenas de megas en memoria por cada admin que le dé al botón. Aquí no se junta
nunca: `zipfile` escribe sobre una cinta que solo recuerda lo último escrito, y
cada vez que la cinta pasa de `TROZO` se suelta lo que lleva y se sigue. Lo que
el proceso tiene a la vez es un trozo, una tanda de filas y el índice del zip.

Que `zipfile` sepa escribir así no es casualidad ni truco: cuando el archivo de
salida no se puede recorrer hacia atrás —y una cinta no puede—, el formato zip
manda escribir el tamaño de cada entrada **detrás** de sus datos, en un
descriptor. `zipfile` lo hace solo en cuanto descubre que no hay `tell()`, y por
eso la cinta no lo tiene: dárselo lo convencería de que puede volver atrás.

**Y por eso la descarga no tiene dirección.** No hay archivo en el disco ni fila
en la base: los bytes se componen mientras salen hacia el navegador de quien
pulsó el botón. La casilla del ticket —«no queda accesible por una dirección
adivinable ni permanente»— no se cumple con un nombre difícil de acertar, que
seguiría siendo acertable; se cumple porque no hay nada que pedir.
"""

import zipfile

from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext as _

from apps.imports.planilla import escrita_como_la_lee_un_excel

# Cuánto se deja acumular antes de soltarlo hacia el navegador. Suficiente para
# que no sea una escritura por fila, poco para que el proceso no note la
# diferencia entre exportar veinte Tutores y exportar tres mil.
TROZO = 64 * 1024

# Cómo se llama el archivo que explica el archivo.
LEEME = "LEEME.txt"

# Cómo se llama la descarga. Con el nombre de la Clínica y la fecha porque va a
# quedar en la carpeta de descargas de alguien al lado de otras diez cosas.
NOMBRE = "gatabase-%(clinica)s-%(fecha)s.zip"


class _Cinta:
    """Un archivo de solo escribir que únicamente recuerda lo último escrito.

    Es lo que `zipfile` toma por su archivo de salida. Deliberadamente **no**
    tiene `tell()` ni `seek()`: sin ellos, `zipfile` se da cuenta de que no puede
    volver atrás y escribe el zip de corrido (ver el docstring del módulo).
    """

    def __init__(self):
        self._trozos = []
        self.pesa = 0

    def write(self, datos):
        self._trozos.append(datos)
        self.pesa += len(datos)
        return len(datos)

    def flush(self):
        """No hay adónde vaciar: lo escrito se lo lleva quien recorre la cinta."""

    def arrancar(self):
        """Lo escrito desde la última vez, y deja la cinta limpia."""
        trozos, self._trozos, self.pesa = self._trozos, [], 0
        return b"".join(trozos)


def se_llama(clinica, momento):
    """Cómo se llama la descarga en la carpeta de quien la pidió.

    Con la fecha de la clínica y no la de la base: las horas se guardan en UTC y
    se presentan en `America/Santiago` (`CLAUDE.md`), y una exportación de las
    nueve y media de la noche se guardaría con la fecha de mañana.
    """
    return NOMBRE % {
        "clinica": slugify(clinica.nombre) or "clinica",
        "fecha": timezone.localdate(momento).isoformat(),
    }


def _leeme(clinica, momento, hojas):
    """Qué es esto y qué hay dentro, en un archivo de texto.

    Va dentro del zip porque el zip va a viajar solo: lo abre dentro de un año
    quien esté migrando la clínica a otro sistema, sin esta aplicación delante y
    sin nadie a quien preguntarle qué es `vinculos.csv`.
    """
    lineas = [
        _("Exportación de los datos de la Clínica %(clinica)s") % {"clinica": clinica.nombre},
        # En hora de la clínica, que es la que reconocerá quien lo abra: en UTC
        # la exportación de una tarde de Santiago consta hecha de madrugada.
        _("Hecha el %(momento)s.")
        % {"momento": timezone.localtime(momento).isoformat(timespec="seconds")},
        "",
        _(
            "Cada archivo es una planilla CSV separada por punto y coma, escrita en "
            "UTF-8 con marca de orden de bytes: se abre haciendo doble clic desde "
            "Excel o LibreOffice. La primera fila es la cabecera."
        ),
        "",
        _("Los archivos que van dentro:"),
    ]
    lineas += [f"  {hoja.nombre}: {', '.join(str(columna) for columna in hoja.cabecera)}" for hoja in hojas]
    lineas += [
        "",
        _(
            "Los Tutores y los Pacientes se cruzan por la columna «id», que es la que "
            "usa vinculos.csv para decir quién responde por qué animal. Un Vínculo con "
            "fecha en la columna «hasta» es el Tutor que tuvo al animal hasta ese día."
        ),
        _(
            "Las columnas de especie, sexo, estado y estado de identificación traen el "
            "código tal como se guarda; especies.csv dice cuáles hay y cómo se llaman."
        ),
        "",
    ]
    return "\n".join(lineas)


def como_un_zip(hojas, clinica, momento, trozo=TROZO):
    """Va soltando el zip de esa Clínica, un trozo cada vez.

    `trozo` se puede bajar desde fuera, y lo hacen los tests: es la única manera
    de comprobar con pocos datos lo que la casilla del ticket promete con
    muchos —que el archivo sale por partes y no de una vez—, y una promesa que
    solo se pudiera comprobar poblando una clínica entera no se comprobaría.
    """
    cinta = _Cinta()
    with zipfile.ZipFile(cinta, "w", zipfile.ZIP_DEFLATED) as paquete:
        paquete.writestr(LEEME, _leeme(clinica, momento, hojas))
        for hoja in hojas:
            with paquete.open(hoja.nombre, "w") as dentro:
                for planilla in escrita_como_la_lee_un_excel(hoja.filas(clinica)):
                    dentro.write(planilla.encode("utf-8"))
                    if cinta.pesa >= trozo:
                        yield cinta.arrancar()
            if cinta.pesa:
                yield cinta.arrancar()
    # Lo que `zipfile` escribe al cerrar: el índice de lo que va dentro. Sin esto
    # el archivo llega entero y ningún programa lo sabe abrir.
    if cinta.pesa:
        yield cinta.arrancar()

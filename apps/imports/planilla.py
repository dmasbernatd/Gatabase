"""La planilla: de los bytes que sube el admin a filas con su número de línea.

Es la mitad del importador que no sabe de Tutores ni de Pacientes, y por eso está
aparte: lo que aquí se decide —qué codificación, qué separador, cómo se llama
cada columna— no depende de qué se esté importando, sino de qué programa escribió
el archivo. El ticket 18 lee su planilla de Pacientes por aquí mismo.

Lo que llega no es un CSV canónico: es lo que exporta el Excel de una clínica, y
eso significa tres cosas que hay que adivinar y una que no se adivina.

**El separador**, porque un Excel en español escribe punto y coma y uno en inglés
escribe coma. Se cuenta cuál aparece más veces en la cabecera en vez de usar
`csv.Sniffer`: el Sniffer mira toda la muestra y se confunde con una dirección
—«Av. Providencia 1234, depto. 52»— en una planilla por punto y coma, que es
justo la combinación que más llega.

**La codificación**, porque un Excel que no guarda en UTF-8 guarda en `cp1252` y
no deja ninguna marca que lo anuncie. Se intenta UTF-8 primero, con `utf-8-sig`
para que la marca de orden de bytes no se cuele dentro del nombre de la primera
columna, y si no cuadra se lee como `cp1252`, que nunca falla. Adivinar mal aquí
no rompe nada: deja una `Ã±` donde iba una `ñ`, y eso se ve en la vista previa
antes de guardar nada.

**Cómo se llama cada columna**, porque la escribió una persona: «Teléfono»,
«fono», «TELEFONO». El nombre se pliega igual que lo que se teclea en una caja de
búsqueda (`apps/busqueda.sin_tildes`) y se busca en el mapa que le pasa quien
lee. Lo que no está en el mapa se ignora en silencio: una planilla de clínica
trae columnas que aquí no significan nada —«observaciones», «saldo»— y rechazarla
por eso sería obligar a recortarla antes de subirla.

Y lo que **no** se adivina es qué columnas tiene que haber. Eso lo dice quien
lee, con una `Columna` por cada una, y sin ellas la planilla no se lee: importar
media planilla porque el nombre se llamaba de otra manera es peor que no importar
nada, porque quedan fichas mudas que alguien tendrá que borrar a mano.

La `Columna` vive aquí y no en cada importador porque es la misma definición para
todos —cómo se llama, de cuántas maneras se la puede haber escrito, si hace
falta— y porque de ella salen a la vez tres cosas que tienen que coincidir: el
reconocimiento de la cabecera, la tabla que documenta el formato en la página y
el archivo de ejemplo que se descarga.

El número de fila es el de la línea del archivo, contando la cabecera como la
uno. No es un contador de filas válidas: es lo que hay que teclear en el Excel
para ir a corregirla, y por eso una línea en blanco gasta su número, y una
dirección con un salto de línea dentro se anuncia por la línea donde empieza y
no por donde acaba.
"""

import csv
import io
from dataclasses import dataclass

from django.utils.translation import gettext as _

from apps.busqueda import sin_tildes

# Los separadores que puede haber escrito quien exportó la planilla, en el orden
# en que se prefieren cuando empatan: la coma es la del formato y gana los
# empates, incluido el de una planilla de una sola columna, donde no hay ninguno.
SEPARADORES = (",", ";", "\t", "|")

# Cómo se lee lo que llega. `utf-8-sig` primero —y no `utf-8` a secas— para que
# la marca de orden de bytes que escribe Excel no acabe dentro del nombre de la
# primera columna. `cp1252` detrás porque es lo que escribe un Excel en español
# que no guarda en UTF-8, y no deja ninguna marca que lo anuncie. Casi nunca
# falla —solo cinco bytes no significan nada en él—, y cuando falla lo que hay
# no es una planilla.
CODIFICACIONES = ("utf-8-sig", "cp1252")

# Con qué se escribe una planilla que va a abrir el mismo Excel que exportó la
# original: punto y coma, saltos de Windows y marca de orden de bytes delante.
# Con coma y sin marca, ese Excel enseña una sola columna y con las tildes rotas.
SEPARADOR_DE_EXCEL = ";"
SALTO_DE_EXCEL = "\r\n"
MARCA_DE_ORDEN = "\ufeff"

# La línea donde va la cabecera. No es configurable a propósito: una planilla con
# el título de la clínica en la primera fila es una planilla que hay que
# recortar, y adivinar dónde empiezan los datos de verdad acabaría importando un
# rótulo como si fuera un Tutor.
LINEA_DE_LA_CABECERA = 1


@dataclass(frozen=True)
class Columna:
    """Una columna de la planilla: cómo se llama, qué dato trae y cómo se ve.

    Lo sabe todo de sí misma para que la documentación del formato, el archivo de
    ejemplo y el reconocimiento de la cabecera salgan del mismo sitio. Si no,
    documentar una columna que el lector no reconoce es un error que nadie ve
    hasta que alguien se descarga el ejemplo y no le entra.

    El rótulo no se escribe cuando el dato es de un modelo: sale del campo, que
    es quien sabe cómo se llama ese dato en el dominio. Se escribe —`rotulo`—
    solo para las columnas que no son un campo de nadie, como la que dice de
    quién es el animal en la planilla de Pacientes.
    """

    nombre: str
    dato: str
    ejemplos: tuple
    obligatoria: bool = False
    # Cómo más lo puede haber escrito quien exportó la planilla. Ya plegados como
    # los pliega este módulo: en minúsculas, sin tildes y con guion bajo.
    alias: tuple = ()
    # De qué modelo es el dato, para sacar de él el rótulo.
    modelo: object = None
    rotulo: str = ""
    # Cuando el dato se puede dar de varias maneras y basta con una, todas las
    # que valen llevan aquí el mismo nombre de grupo: la planilla se lee si trae
    # alguna, y no se lee si no trae ninguna. Es lo que separa «falta una
    # columna» de «esta planilla no dice de quién es cada animal».
    alguna_de: str = ""

    @property
    def etiqueta(self):
        return self.rotulo or self.modelo._meta.get_field(self.dato).verbose_name

    @property
    def como_se_puede_llamar(self):
        return (self.nombre, *self.alias)


def _mapa_de(columnas):
    """De cada nombre con que se pueda haber escrito una columna, qué dato trae."""
    return {
        como_se_llame: columna.dato
        for columna in columnas
        for como_se_llame in columna.como_se_puede_llamar
    }


def _lo_que_falta(columnas, cabecera):
    """Los nombres de las columnas sin las cuales la planilla no significa nada.

    Dos maneras de faltar, y las dos son del archivo entero y no de una fila: la
    columna obligatoria que no está, y el grupo del que no llegó ninguna.
    """
    faltan = [
        [columna.nombre]
        for columna in columnas
        if columna.obligatoria and columna.dato not in cabecera
    ]
    grupos = {columna.alguna_de for columna in columnas if columna.alguna_de}
    for grupo in sorted(grupos):
        cuales = [columna for columna in columnas if columna.alguna_de == grupo]
        if not any(columna.dato in cabecera for columna in cuales):
            faltan.append([columna.nombre for columna in cuales])
    return faltan


class PlanillaIlegible(Exception):
    """La planilla no se deja leer entera, así que no se lee ninguna fila.

    Es lo que separa un problema del archivo de un problema de una fila: una fila
    mala se salta y las demás entran (ticket 17), pero una cabecera que no se
    entiende deja sin sentido a todas.
    """


@dataclass(frozen=True)
class Fila:
    """Una línea de datos de la planilla, con el número que se ve en el Excel."""

    numero: int
    valores: dict


def _texto(contenido):
    """Los bytes leídos como texto, adivinando con qué los escribieron."""
    for codificacion in CODIFICACIONES:
        try:
            return contenido.decode(codificacion)
        except UnicodeDecodeError:
            continue
    raise PlanillaIlegible(_("No se entiende con qué codificación está escrita la planilla."))


def _separador(cabecera):
    """Con qué se separan las columnas, contándolos en la cabecera.

    Solo en la cabecera: es la línea que seguro no lleva texto libre dentro, y
    contar sobre el archivo entero es lo que confunde a `csv.Sniffer` cuando una
    dirección trae comas y la planilla va por punto y coma.
    """
    return max(SEPARADORES, key=cabecera.count)


def _como_se_llama(columna):
    """El nombre de una columna plegado como se teclea: sin tildes ni espacios.

    Se pliega con el mismo `sin_tildes` que la búsqueda del mostrador, para que
    «Teléfono» y «telefono» sean la misma columna sin que haya en el repositorio
    una segunda idea de qué es una tilde.
    """
    return sin_tildes(columna).strip().replace(" ", "_")


class Planilla:
    """Las filas de datos de un archivo subido, ya con sus columnas reconocidas."""

    def __init__(self, filas):
        self._filas = filas

    def __iter__(self):
        return iter(self._filas)

    @classmethod
    def leer(cls, contenido, *, columnas):
        """Lee los bytes subidos, o dice por qué no se puede leer ninguna fila.

        `columnas` es la definición del formato: las `Columna` que quien lee sabe
        reconocer, con cuáles hacen falta. Se pasa entera y no partida en un mapa
        y una lista de obligatorias porque es una sola cosa —cómo es esa
        planilla—, y partirla dejaba a quien llama componiendo dos veces lo mismo.
        """
        # `newline=""` y no `splitlines()`: las líneas conservan su salto, que es
        # lo que `csv` necesita para reconstruir una dirección escrita entre
        # comillas y con un salto dentro. Partirlas antes se la pega de corrido.
        papel = io.StringIO(_texto(contenido), newline="")
        primera = papel.readline()
        if not primera.strip():
            raise PlanillaIlegible(_("La planilla está vacía: no trae ni siquiera la cabecera."))

        papel.seek(0)
        lector = csv.reader(papel, delimiter=_separador(primera))
        mapa = _mapa_de(columnas)
        cabecera = [mapa.get(_como_se_llama(celda)) for celda in next(lector)]

        faltan = _lo_que_falta(columnas, cabecera)
        if faltan:
            raise PlanillaIlegible(
                _("A la planilla le falta la columna %(cuales)s.")
                % {"cuales": "; ".join(" o ".join(grupo) for grupo in faltan)}
            )

        filas = []
        # `line_num` es la **última** línea leída, y una fila puede ocupar varias.
        # Lo que hay que teclear en el Excel para llegar a ella es la primera, que
        # es la siguiente a donde acabó la anterior.
        acabo_la_anterior = lector.line_num
        for celdas in lector:
            empieza = acabo_la_anterior + 1
            acabo_la_anterior = lector.line_num
            if any(celda.strip() for celda in celdas):
                filas.append(Fila(numero=empieza, valores=_reunir(cabecera, celdas)))
        return cls(filas)


def _reunir(cabecera, celdas):
    """Los datos de una fila, por el nombre del dato y no por su posición.

    La fila corta rellena con vacíos —le faltan datos, no columnas— y la larga
    pierde el sobrante: son dos maneras de que un Excel escriba la misma fila, y
    ninguna de las dos es motivo para rechazarla sin haberla mirado.
    """
    valores = {columna: "" for columna in cabecera if columna}
    for columna, celda in zip(cabecera, celdas):
        if columna:
            valores[columna] = celda.strip()
    return valores


def como_la_lee_un_excel(filas):
    """Esas filas escritas como la planilla que el admin va a abrir con su Excel.

    Vive aquí y no en quien la escribe porque es la misma decisión que la de
    arriba vista del revés —qué formato entiende un Excel chileno— y porque la
    escriben dos: el informe de errores y el archivo de ejemplo. Copiada en los
    dos sitios, cambiar de idea en uno dejaría al otro abriéndose torcido.
    """
    papel = io.StringIO()
    planilla = csv.writer(papel, delimiter=SEPARADOR_DE_EXCEL, lineterminator=SALTO_DE_EXCEL)
    planilla.writerows(filas)
    return MARCA_DE_ORDEN + papel.getvalue()


def ejemplo_de(columnas):
    """El archivo de ejemplo de ese formato, escrito desde la misma definición.

    Se genera y no se guarda como archivo suelto para que no pueda envejecer: una
    columna que se añada a la definición sale documentada, reconocida y en el
    ejemplo a la vez. Cada importador comprueba en sus tests que su ejemplo entra
    entero, que es lo que hace que la promesa valga.
    """
    return como_la_lee_un_excel([
        [columna.nombre for columna in columnas],
        *(
            [columna.ejemplos[cual] for columna in columnas]
            for cual in range(len(columnas[0].ejemplos))
        ),
    ])

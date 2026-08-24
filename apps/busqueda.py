"""Cómo se lee lo que alguien escribe en una caja de búsqueda, y en qué se traduce.

Aquí vive solo la mecánica. Por dónde se busca a un Tutor o a un Paciente lo
dice cada modelo (`POR_DONDE_SE_BUSCA`), y qué es un RUT, un teléfono o un
microchip lo siguen decidiendo sus módulos. Este no sabe de ninguno de los tres,
por lo mismo que `apps/campos.py` no sabe: lo necesitan las dos apps de dominio y
ninguna puede importar de la otra (`CLAUDE.md`).

Son tres decisiones, y las tres salen de mirar a recepción escribir:

**Las tildes no se teclean.** Nadie escribe «Muñoz» ni «Íñigo» con el teclado a
las siete de la tarde y con el Tutor al teléfono, y una ficha que no aparece
porque le falta un acento es una ficha perdida. Así que los dos lados de la
comparación —lo guardado y lo escrito— pasan por la misma tabla de acentos, uno
en SQL y otro en Python.

**Lo escrito puede ser un dato entero o un trozo de uno.** Un RUT dictado por
teléfono llega completo y con su dígito verificador; un chip lo trae el lector de
un tirón. Los dos se pueden buscar **por igualdad**, que es lo que sabe usar el
índice que ya existe (`rut_unico_dentro_de_la_clinica`,
`paciente_por_microchip`). Media docena de dígitos sueltos, no: eso es un trozo,
y un trozo se busca por dentro y se paga con un barrido. Distinguirlos es lo que
hace que la búsqueda rápida sea rápida de verdad, y no cuesta ningún índice
nuevo.

**Un espacio no siempre separa dos palabras.** «camila rojas» son dos cosas que
pueden estar en dos campos distintos; «9 8765 4321» y «900 123 456 789 012» son
una sola, y partirlas por el espacio deja trozos de tres dígitos que no
identifican a nadie. Así que lo escrito se lee de una de dos maneras, y lo
que decide cuál es si trae letras: sin ninguna —salvo la `K` con la que puede
acabar un RUT— es **un número dictado**, y se lee entero; con ellas es **un
nombre**, y se lee palabra a palabra. No se intentan las dos: ningún campo por
el que se busca guarda números en el nombre, así que buscar «9 8765 4321»
también por dentro de los nombres solo traería al Tutor cuyo correo lleva un
nueve.

Y una palabra que no cabe en ningún campo descarta el campo, no la búsqueda: de
«camila» no quedan dígitos, y buscarla en el teléfono como cadena vacía haría
coincidir a toda la Clínica.
"""

from collections import namedtuple

from django.core.exceptions import ValidationError
from django.db.models import CharField, Q, Transform

# Las letras acentuadas que se escriben en Chile y en qué se convierten. Es una
# lista explícita y no `unicodedata`, y esa es la razón de que exista: Postgres
# tiene que poder hacer lo mismo sobre lo guardado, y `translate` necesita las
# dos cadenas escritas. Que la tabla sea una sola es lo que garantiza que el
# lado de Python y el de SQL plieguen exactamente lo mismo — si Python plegara
# de más, buscar una letra que SQL deja intacta no encontraría nada.
#
# La `ñ` entra a propósito: quien busca «munoz» busca a Muñoz, y en una caja de
# búsqueda eso es un acierto y no una confusión. Guardar sí distingue las dos,
# que es lo que importa.
ACENTOS = "áàäâãéèëêíìïîóòöôõúùüûñç"
SIN_ACENTOS = "aaaaaeeeeiiiiooooouuuunc"

_SIN_TILDES = str.maketrans(ACENTOS, SIN_ACENTOS)

# Cuántos caracteres tiene que traer un trozo de RUT, de teléfono o de chip para
# que buscarlo signifique algo. Con menos, «9» traería a la Clínica entera: no es
# una búsqueda, es la tabla.
TROZO_MINIMO = 3


def sin_tildes(escrito):
    """Lo escrito plegado: en minúsculas y sin acentos. Es el lado de Python.

    `lower` y no `casefold` a propósito: el otro lado es el `lower()` de
    Postgres, y los dos tienen que dar lo mismo.
    """
    return (escrito or "").lower().translate(_SIN_TILDES)


class SinTildes(Transform):
    """El mismo plegado, hecho por Postgres sobre lo guardado.

    Se registra sobre `CharField`, así que lo heredan también el correo y los
    campos que normalizan (`apps/campos.py`). Se escribe
    `nombre__sin_tildes__contains`, y lo que llega tiene que venir ya plegado por
    `sin_tildes`.

    Es `translate` y no la extensión `unaccent`, que sería lo idiomático en
    Postgres, por una razón de despliegue y no de gusto: `CREATE EXTENSION
    unaccent` pide superusuario, y el rol de la aplicación no lo es a propósito
    —ADR-0004 monta un `check` que **falla** si lo fuera—, así que la migración
    que la instalara no correría en producción. `translate` no pide nada.
    """

    lookup_name = "sin_tildes"
    output_field = CharField()

    def as_sql(self, compilador, conexion):
        sql, parametros = compilador.compile(self.lhs)
        return f"translate(lower({sql}), %s, %s)", (*parametros, ACENTOS, SIN_ACENTOS)


# Al importar este módulo, y no dentro de un `AppConfig.ready`: quienes declaran
# los campos buscables son `Tutor` y `Paciente`, que importan de aquí, y Django
# carga todos los modelos al arrancar. El registro es por tanto tan seguro como
# que existan los modelos que lo usan, y vive al lado del `Transform` que
# registra en vez de en un archivo aparte que hay que acordarse de mirar.
CharField.register_lookup(SinTildes)


# Qué comparación le toca a una palabra en un campo: el sufijo del lookup y el
# valor ya leído. Es un par con nombre y no una tupla suelta porque los dos
# viajan juntos hasta el `Q` y se leen mal al revés.
Lectura = namedtuple("Lectura", "lookup valor")


def _trozo(como_se_busca, palabra):
    """Lo escrito leído como un pedazo de ese campo, o `None` si no llega a nada.

    Es el final común de los dos campos que guardan un número: por debajo del
    largo mínimo no hay búsqueda que hacer.
    """
    trozo = como_se_busca(palabra)
    return Lectura("contains", trozo) if len(trozo) >= TROZO_MINIMO else None


class Campo:
    """Un campo por el que se busca, y cómo hay que leer para él lo escrito.

    Los tres constructores son los tres tipos de campo que hay en el fichero, y
    no hay un cuarto: un nombre, unos dígitos sueltos, o un dato que se guarda
    normalizado y que a veces llega entero.
    """

    def __init__(self, nombre, lee, dictado):
        self.nombre = nombre
        # `palabra -> Lectura`, o `None` si esa palabra no dice nada aquí.
        self.lee = lee
        # Si lo que guarda es un número que se dicta —y entonces se lee de la
        # caja entera, espacios incluidos— o texto, que se lee palabra a palabra.
        self.dictado = dictado

    @classmethod
    def de_texto(cls, nombre):
        """Un nombre o un correo: se busca por dentro y sin tildes."""
        return cls(
            nombre,
            lambda palabra: Lectura("sin_tildes__contains", sin_tildes(palabra)),
            dictado=False,
        )

    @classmethod
    def de_digitos(cls, nombre, como_se_busca):
        """Un campo que se guarda normalizado y del que solo se busca un trozo.

        El teléfono: se guarda en E.164 y se teclea de seis maneras, y lo que
        queda en común entre todas ellas son sus últimos dígitos.
        """

        return cls(nombre, lambda palabra: _trozo(como_se_busca, palabra), dictado=True)

    @classmethod
    def normalizado(cls, nombre, normalizado, como_se_busca):
        """Un campo que se guarda normalizado y que a veces llega entero.

        El RUT y el microchip. Si lo escrito se deja leer entero —el RUT cuadra
        con su dígito verificador, el chip trae sus quince dígitos— se busca por
        igualdad, que es lo que el índice sabe resolver y lo que además no
        confunde a un Tutor con otro que lleve su RUT dentro del suyo. Si no, es
        un trozo y se busca como tal.
        """

        def lee(palabra):
            try:
                entero = normalizado(palabra)
            except ValidationError:
                entero = ""
            return Lectura("exact", entero) if entero else _trozo(como_se_busca, palabra)

        return cls(nombre, lee, dictado=True)

    def coincide_con(self, palabra):
        """La condición que esa palabra impone en este campo, o `None` si ninguna."""
        lectura = self.lee(palabra)
        return Q(**{f"{self.nombre}__{lectura.lookup}": lectura.valor}) if lectura else None


def parece_un_numero(escrito):
    """Si lo escrito puede ser un número dictado, y no un nombre.

    Lleva algún dígito y ninguna letra, salvo la `K` con la que puede acabar un
    RUT. Es lo que decide si tiene sentido leer la caja entera como un solo dato:
    en «camila 12345678» los dígitos son de otra cosa, y leerlos como un RUT
    traería al Tutor que lo tiene aunque no se llame Camila.
    """
    sin_verificador = escrito[:-1] if escrito[-1:].upper() == "K" else escrito
    return any(caracter.isdigit() for caracter in escrito) and not any(
        caracter.isalpha() for caracter in sin_verificador
    )


def en_algun_campo(campos, palabra):
    """La condición de que la palabra aparezca en alguno de esos campos.

    `None` cuando la palabra no dice nada en ninguno: no es «todo vale», es que
    por ahí no se la puede encontrar.
    """
    condicion = None
    for campo in campos:
        if (suya := campo.coincide_con(palabra)) is not None:
            condicion = suya if condicion is None else condicion | suya
    return condicion


def _como_un_nombre(campos, escrito):
    """Todas las palabras, cada una en algún campo de texto.

    Cada una en alguno, no todas en el mismo: así «camila rojas» encuentra a
    quien tiene el nombre en un campo y el apellido en otro, que es como
    recepción escribe un nombre.
    """
    todas = Q()
    for palabra in escrito.split():
        alguna = en_algun_campo(campos, palabra)
        if alguna is None:
            return None
        todas &= alguna
    return todas


def condicion(campos, escrito):
    """La condición que impone lo escrito sobre estos campos, o `None`.

    Devuelve `None` cuando no hay manera de que lo escrito coincida por aquí, y
    eso no es lo mismo que no imponer condición: quien llame tiene que responder
    con un conjunto vacío, no con todo. Pasa con la caja vacía, y pasa con media
    docena de dígitos que no llegan a identificar nada.
    """
    escrito = (escrito or "").strip()
    if not escrito:
        return None
    if parece_un_numero(escrito):
        return en_algun_campo([campo for campo in campos if campo.dictado], escrito)
    return _como_un_nombre([campo for campo in campos if not campo.dictado], escrito)

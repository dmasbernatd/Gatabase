"""Cómo se busca, se ordena y se pagina el fichero de Tutores.

Vive fuera de la vista porque es lo que tiene reglas: qué columnas se pueden
ordenar, cómo se reparte lo que recepción escribe en la caja de búsqueda entre
los campos del Tutor, y qué enlace lleva a la página siguiente sin perder ni el
orden ni la búsqueda. La vista se limita a construir un `ListadoDeTutores` y
pasárselo a la plantilla.

Esta búsqueda es la del fichero de Tutores: sirve para encontrar a alguien por su
nombre, su apellido, su RUT, su teléfono o su correo, y por dónde se le busca lo
dice el Tutor mismo (`Tutor.POR_DONDE_SE_BUSCA`). La caja única del mostrador
—la que además encuentra Pacientes y microchips— es otra pantalla y vive en
`mostrador.py`, pero lee lo escrito con la misma mecánica (`apps/busqueda.py`) y
busca a los Tutores por los mismos campos: dos definiciones de «cómo se encuentra
a un Tutor» acabarían diciendo cosas distintas.
"""

from django.core.paginator import Paginator
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _

from apps.busqueda import condicion
from apps.tutors.rut import formateado

TUTORES_POR_PAGINA = 25

PARAMETRO_DE_BUSQUEDA = "q"
PARAMETRO_DE_ORDEN = "orden"
PARAMETRO_DE_PAGINA = "pagina"

DESCENDENTE = "-"


class Columna:
    """Una columna del listado: cómo se rotula, por qué campos ordena y qué
    celda pinta en cada fila.

    Existe para que añadir una columna sea una sola edición. Antes la cabecera
    salía de aquí y la celda estaba escrita a mano en la plantilla, así que
    olvidarse de la segunda no rompía nada: dejaba la tabla descuadrada.

    Cada una trae ya decidido su desempate hasta el `pk`: sin él, dos Tutores
    del mismo apellido pueden cambiar de sitio entre una página y la siguiente y
    salir dos veces o ninguna.
    """

    def __init__(self, clave, etiqueta, desempata_por=(), enlaza_a_la_ficha=False, presenta=str):
        self.clave = clave
        self.etiqueta = etiqueta
        # La columna ordena primero por su propio campo; lo demás es desempate.
        self.campos = [clave, *desempata_por, "pk"]
        self.enlaza_a_la_ficha = enlaza_a_la_ficha
        # Cómo se lee lo guardado. Casi siempre tal cual; el RUT, no: se guarda
        # de corrido y se lee con puntos y guion.
        self.presenta = presenta

    def celda_de(self, tutor):
        """La celda de este Tutor en esta columna."""
        valor = getattr(tutor, self.clave)
        return Celda(
            self.presenta(valor) if valor else valor,
            tutor.pk if self.enlaza_a_la_ficha else None,
        )

    def sentido_en(self, orden):
        """El valor de `aria-sort` de su cabecera, que es lo que anuncia un
        lector de pantalla. Va en inglés porque es vocabulario de HTML, no
        texto de la interfaz."""
        if orden.columna is not self:
            return "none"
        return "descending" if orden.descendente else "ascending"


class Celda:
    """Lo que una columna enseña de un Tutor: un texto, y si lleva a su ficha.

    El guion del hueco vive aquí y no en la plantilla porque es la misma
    respuesta para toda columna vacía, y la plantilla ya no sabe cuáles hay.
    """

    HUECO = "—"

    def __init__(self, valor, ficha=None):
        self.texto = str(valor) if valor else self.HUECO
        self.ficha = ficha


# Ordenar por lo que traiga la URL sería dejar que quien la escribe elija el
# `ORDER BY`. Se ordena solo por estas columnas, que son las que el listado
# enseña, y en este orden salen en la tabla.
#
# El enlace a la ficha va en el nombre, que es el único dato obligatorio: un
# Tutor registrado con las prisas del mostrador, sin apellidos, tiene que poder
# abrirse igual.
COLUMNAS = (
    Columna("apellidos", _("Apellidos"), desempata_por=["nombre"]),
    Columna("nombre", _("Nombre"), desempata_por=["apellidos"], enlaza_a_la_ficha=True),
    Columna("rut", _("RUT"), desempata_por=["apellidos", "nombre"], presenta=formateado),
    Columna("telefono", _("Teléfono"), desempata_por=["apellidos", "nombre"]),
    Columna("email", _("Correo"), desempata_por=["apellidos", "nombre"]),
)
COLUMNAS_POR_CLAVE = {columna.clave: columna for columna in COLUMNAS}

ORDEN_POR_DEFECTO = COLUMNAS_POR_CLAVE["apellidos"]


class Orden:
    """Por qué Columna y en qué sentido se ordena el listado.

    Es un tipo y no el string de la URL porque el string hay que interpretarlo
    —el `-` de delante— y se interpretaba en tres sitios. Aquí se interpreta una
    vez, al entrar, y lo que circula ya es la Columna misma. Se escribe de vuelta
    como vino (`-apellidos`), así que sigue valiendo tal cual en una URL o en un
    campo de formulario.
    """

    def __init__(self, columna, descendente=False):
        self.columna = columna
        self.descendente = descendente

    @classmethod
    def desde_la_url(cls, parametro):
        """El orden que pide la URL, o el de siempre si no se reconoce.

        Un orden que no existe no es un error que merezca una página de fallo:
        se ordena por lo de siempre, que es lo que el Usuario esperaba ver.
        """
        descendente = parametro.startswith(DESCENDENTE)
        clave = parametro[1:] if descendente else parametro
        if clave not in COLUMNAS_POR_CLAVE:
            return cls(ORDEN_POR_DEFECTO)
        return cls(COLUMNAS_POR_CLAVE[clave], descendente)

    def __str__(self):
        return (DESCENDENTE if self.descendente else "") + self.columna.clave

    @property
    def campos(self):
        """Los campos del `order_by` que le corresponden."""
        campos = self.columna.campos
        return [DESCENDENTE + campo for campo in campos] if self.descendente else campos

    def al_pulsar(self, columna):
        """El orden al que lleva pulsar esa cabecera.

        La de la Columna por la que ya se ordena lleva al orden contrario; la de
        cualquier otra, a ordenar por ella de la A a la Z.
        """
        if columna is self.columna:
            return Orden(columna, not self.descendente)
        return Orden(columna)


def buscar(tutores, buscado):
    """Los Tutores que casan con lo escrito en la caja de búsqueda.

    Cómo se lee lo escrito —entero, como un RUT o un teléfono dictado, o palabra
    a palabra, como un nombre repartido entre dos campos— lo decide
    `apps/busqueda.py`; por dónde se busca a un Tutor lo dice él mismo.

    Cuando lo escrito no cabe en ningún campo no quedan Tutores, y eso hay que
    decirlo aquí: la condición vacía significaría lo contrario —traerlos a todos—
    y una búsqueda que no encuentra nada no puede devolver la Clínica entera.
    """
    if not buscado.strip():
        return tutores
    coincide = condicion(tutores.model.POR_DONDE_SE_BUSCA, buscado)
    return tutores.filter(coincide) if coincide is not None else tutores.none()


class ListadoDeTutores:
    """El fichero de Tutores tal y como lo mira recepción: buscado, ordenado y paginado.

    Recibe los Tutores ya acotados a la Clínica —de eso se encarga el manager
    por defecto (ADR-0003)— y los parámetros de la URL.
    """

    # Con qué nombre viajan los campos del formulario de búsqueda. La plantilla
    # los lee de aquí: escribir "q" a mano allí dejaba la constante sin
    # proteger nada, y renombrar el parámetro rompía la búsqueda en silencio.
    CAMPO_DE_BUSQUEDA = PARAMETRO_DE_BUSQUEDA
    CAMPO_DE_ORDEN = PARAMETRO_DE_ORDEN

    def __init__(self, tutores, parametros):
        self.buscado = parametros.get(PARAMETRO_DE_BUSQUEDA, "").strip()
        self.orden = Orden.desde_la_url(parametros.get(PARAMETRO_DE_ORDEN, ""))
        encontrados = buscar(tutores, self.buscado).order_by(*self.orden.campos)
        self.pagina = Paginator(encontrados, TUTORES_POR_PAGINA).get_page(
            parametros.get(PARAMETRO_DE_PAGINA)
        )

    def _consulta(self, orden=None, pagina=None):
        """La consulta de la URL conservando lo que no cambia.

        Cambiar de orden vuelve a la primera página: la página 7 del orden
        anterior no enseña a los mismos Tutores en el nuevo.
        """
        parametros = {
            PARAMETRO_DE_BUSQUEDA: self.buscado,
            PARAMETRO_DE_ORDEN: str(orden or self.orden),
            PARAMETRO_DE_PAGINA: pagina,
        }
        return urlencode({clave: valor for clave, valor in parametros.items() if valor})

    @property
    def columnas(self):
        """Las cabeceras ordenables: su rótulo, adónde lleva y cómo está ordenada.

        Salen de `COLUMNAS` y en su orden, igual que las celdas de cada fila: no
        hay forma de que una tabla tenga más cabeceras que celdas.
        """
        return [
            {
                "etiqueta": columna.etiqueta,
                "enlace": self._consulta(orden=self.orden.al_pulsar(columna)),
                "aria": columna.sentido_en(self.orden),
            }
            for columna in COLUMNAS
        ]

    @property
    def filas(self):
        """Los Tutores de la página, ya repartidos en celdas."""
        return [[columna.celda_de(tutor) for columna in COLUMNAS] for tutor in self.pagina]

    @property
    def ancho(self):
        """Cuántas columnas tiene la tabla, para el `colspan` de la fila vacía."""
        return len(COLUMNAS)

    @property
    def enlace_anterior(self):
        if not self.pagina.has_previous():
            return ""
        return self._consulta(pagina=self.pagina.previous_page_number())

    @property
    def enlace_siguiente(self):
        if not self.pagina.has_next():
            return ""
        return self._consulta(pagina=self.pagina.next_page_number())

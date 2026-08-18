"""Cómo se busca, se ordena y se pagina el fichero de Tutores.

Vive fuera de la vista porque es lo que tiene reglas: qué columnas se pueden
ordenar, cómo se reparte lo que recepción escribe en la caja de búsqueda entre
los campos del Tutor, y qué enlace lleva a la página siguiente sin perder ni el
orden ni la búsqueda. La vista se limita a construir un `ListadoDeTutores` y
pasárselo a la plantilla.

Esta búsqueda es la del fichero de Tutores: sirve para encontrar a alguien por su
nombre, su apellido, su teléfono o su correo. La caja única que además busca
Pacientes y microchips, tolerante a tildes, es del ticket 11.
"""

from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _

TUTORES_POR_PAGINA = 25

PARAMETRO_DE_BUSQUEDA = "q"
PARAMETRO_DE_ORDEN = "orden"
PARAMETRO_DE_PAGINA = "pagina"

DESCENDENTE = "-"

# Ordenar por lo que traiga la URL sería dejar que quien la escribe elija el
# `ORDER BY`. Se ordena solo por estas columnas, que son las que el listado
# enseña, y cada una trae ya decidido su desempate hasta el `pk`: sin él, dos
# Tutores del mismo apellido pueden cambiar de sitio entre una página y la
# siguiente y salir dos veces o ninguna.
COLUMNAS = {
    "apellidos": {"etiqueta": _("Apellidos"), "campos": ["apellidos", "nombre", "pk"]},
    "nombre": {"etiqueta": _("Nombre"), "campos": ["nombre", "apellidos", "pk"]},
    "telefono": {"etiqueta": _("Teléfono"), "campos": ["telefono", "apellidos", "nombre", "pk"]},
    "email": {"etiqueta": _("Correo"), "campos": ["email", "apellidos", "nombre", "pk"]},
}
ORDEN_POR_DEFECTO = "apellidos"

# Por dónde se busca a un Tutor: cómo se llama y por dónde se le contacta. La
# dirección queda fuera a propósito — nadie llama preguntando por una calle — y
# meterla solo traería coincidencias que estorban.
CAMPOS_BUSCABLES = ("nombre", "apellidos", "telefono", "email")


class Orden:
    """Por qué columna y en qué sentido se ordena el listado.

    Es un tipo y no el string de la URL porque el string hay que interpretarlo
    —el `-` de delante— y se interpretaba en tres sitios. Aquí se interpreta una
    vez, al entrar, y lo que circula ya sabe responder por sus campos y por la
    cabecera que lo invierte. Se escribe de vuelta como vino (`-apellidos`), así
    que sigue valiendo tal cual en una URL o en un campo de formulario.
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
        columna = parametro[1:] if descendente else parametro
        if columna not in COLUMNAS:
            return cls(ORDEN_POR_DEFECTO)
        return cls(columna, descendente)

    def __str__(self):
        return (DESCENDENTE if self.descendente else "") + self.columna

    @property
    def campos(self):
        """Los campos del `order_by` que le corresponden."""
        campos = COLUMNAS[self.columna]["campos"]
        return [DESCENDENTE + campo for campo in campos] if self.descendente else campos

    def al_pulsar(self, columna):
        """El orden al que lleva pulsar esa cabecera.

        La de la columna por la que ya se ordena lleva al orden contrario; la de
        cualquier otra, a ordenar por ella de la A a la Z.
        """
        if columna == self.columna:
            return Orden(columna, not self.descendente)
        return Orden(columna)

    def sentido_de(self, columna):
        """El valor de `aria-sort` de esa cabecera, que es lo que anuncia un
        lector de pantalla. Va en inglés porque es vocabulario de HTML, no
        texto de la interfaz."""
        if columna != self.columna:
            return "none"
        return "descending" if self.descendente else "ascending"


def buscar(tutores, buscado):
    """Los Tutores que casan con lo escrito en la caja de búsqueda.

    Cada palabra tiene que aparecer en alguno de los campos, no todas en el
    mismo: así «camila rojas» encuentra a quien tiene el nombre en un campo y el
    apellido en otro, que es como recepción escribe un nombre.
    """
    for palabra in buscado.split():
        coincide = Q()
        for campo in CAMPOS_BUSCABLES:
            coincide |= Q(**{f"{campo}__icontains": palabra})
        tutores = tutores.filter(coincide)
    return tutores


class ListadoDeTutores:
    """El fichero de Tutores tal y como lo mira recepción: buscado, ordenado y paginado.

    Recibe los Tutores ya acotados a la Clínica —de eso se encarga el manager
    por defecto (ADR-0003)— y los parámetros de la URL.
    """

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

        La plantilla las recorre en este orden, y las celdas de cada fila van en
        el mismo: una columna nueva aquí es una celda nueva allí.
        """
        return [
            {
                "etiqueta": columna["etiqueta"],
                "enlace": self._consulta(orden=self.orden.al_pulsar(clave)),
                "aria": self.orden.sentido_de(clave),
            }
            for clave, columna in COLUMNAS.items()
        ]

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

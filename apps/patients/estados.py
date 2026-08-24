"""En qué situación está el Paciente ante la clínica: activo, inactivo o fallecido.

Es un estado y no un borrado, y esa es toda la decisión. Un animal que muere o
que deja de venir **no** desaparece: su Historia clínica es del animal (ADR-0001)
y sigue haciendo falta después —para el Tutor que pregunta por lo que se le
puso, para el veterinario que atiende a otro animal de la misma casa, para la
Ley 21.719 cuando alguien reclame qué se guardó de él—. Lo que hay que evitar es
el peor error posible de cara al Tutor: llamar, citar o tratar como activo a un
animal que ya no está.

`fallecido` e `inactivo` no son lo mismo y por eso son dos:

- **`fallecido`** es un hecho del mundo, y se sabe. Cierra la ficha: no se
  corrige más, y la agenda no la admite (`Paciente.admite_citas`).
- **`inactivo`** es lo que la clínica sabe cuando no sabe nada: el animal dejó
  de venir y nadie llegó a contar qué pasó. Se deshace solo con que vuelva, y
  por eso no cierra nada — un animal que reaparece a los dos años se atiende.

La diferencia es la misma que el Estado sanitario hace entre `desconocido` y
`vencido` (`CONTEXT.md`): dejar de saber no es saber que no.

Aquí vive además **qué enseña un listado por defecto**, que es lo otro que el
estado decide. Recepción mira una lista para saber a quién atender hoy, así que
por defecto salen los activos y el resto se pide. Esto vale para listas de
trabajo; la caja de búsqueda del ticket 11 hará lo contrario a propósito —marcar
en vez de esconder—, porque a un Paciente fallecido a veces se le busca
precisamente a él, y quien escribe su nombre ya sabe a quién busca.
"""

from django.db import models
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _


class EstadoDelPaciente(models.TextChoices):
    """Situación del Paciente ante la clínica. Ver el módulo."""

    ACTIVO = "activo", _("activo")
    INACTIVO = "inactivo", _("inactivo")
    FALLECIDO = "fallecido", _("fallecido")


# Con qué estado nace un Paciente. Se registra porque está delante del
# mostrador: no hay un cuarto valor para «no se sabe», como sí lo hay en el
# Estado de identificación, porque aquí nadie tiene que preguntar nada.
POR_DEFECTO = EstadoDelPaciente.ACTIVO

PARAMETRO_DE_ESTADO = "estado"


class Filtro:
    """Un grupo de estados con nombre: lo que una de las opciones enseña.

    Sin estados no filtra nada, que es la opción «todos». Se dice así y no con
    un `None` suelto porque lo que la distingue de las demás es justamente que
    su grupo está vacío.
    """

    def __init__(self, clave, etiqueta, estados=()):
        self.clave = clave
        self.etiqueta = etiqueta
        self.estados = estados

    def aplicado_a(self, pacientes):
        return pacientes.filter(estado__in=self.estados) if self.estados else pacientes


# Lo que se puede pedir ver, y en este orden salen las opciones. El primero es
# el de siempre: quien no pide nada está trabajando, y quien trabaja atiende a
# los que vienen.
FILTROS = (
    Filtro("activos", _("Activos"), (EstadoDelPaciente.ACTIVO,)),
    Filtro("inactivos", _("Inactivos"), (EstadoDelPaciente.INACTIVO,)),
    Filtro("fallecidos", _("Fallecidos"), (EstadoDelPaciente.FALLECIDO,)),
    Filtro("todos", _("Todos")),
)
FILTROS_POR_CLAVE = {filtro.clave: filtro for filtro in FILTROS}

FILTRO_POR_DEFECTO = FILTROS[0]


class FiltroPorEstado:
    """Qué Pacientes enseña una lista, según lo que pida la URL.

    Un valor que no se reconoce no es un error que merezca una página de fallo
    —es una URL escrita a mano— y se responde con lo de siempre: los activos,
    que es lo que quien miraba esperaba ver. Mismo criterio que el `Orden` del
    listado de Tutores.
    """

    # La plantilla lee de aquí con qué nombre viaja el parámetro, en vez de
    # escribir "estado" a mano: renombrarlo rompería el filtro en silencio.
    CAMPO = PARAMETRO_DE_ESTADO

    def __init__(self, parametros):
        self.filtro = FILTROS_POR_CLAVE.get(
            parametros.get(PARAMETRO_DE_ESTADO, ""), FILTRO_POR_DEFECTO
        )

    def aplicado_a(self, pacientes):
        """Los Pacientes que quedan tras aplicar lo pedido."""
        return self.filtro.aplicado_a(pacientes)

    @property
    def opciones(self):
        """Las opciones que se ofrecen: su rótulo, su consulta y cuál está puesta."""
        return [
            {
                "etiqueta": filtro.etiqueta,
                "consulta": urlencode({PARAMETRO_DE_ESTADO: filtro.clave}),
                "actual": filtro is self.filtro,
            }
            for filtro in FILTROS
        ]

"""Elegir a un Tutor sin traerse el fichero entero a la página.

Sumarle un Tutor a un Paciente, o pasárselo a otro, era elegir en un desplegable
con todos los de la Clínica: a cientos de Tutores, cientos de líneas para elegir
uno, y todos los nombres servidos cada vez que alguien abría la página. Ahora se
busca primero, como en el mostrador, y solo se ofrecen los que casan con lo
escrito.

Quién se puede elegir no lo decide este módulo: lo decide cada formulario, que
sabe si sobra quien ya responde por el animal o solo el responsable. Aquí se
recibe ese conjunto y se busca **dentro** de él, así que la frontera de la
Clínica y la de los anonimizados las sigue dibujando quien las dibujaba. Cómo se
lee lo escrito lo decide `apps/busqueda.py`, y por dónde se busca a un Tutor, el
Tutor mismo (`POR_DONDE_SE_BUSCA`): es la misma caja que la del fichero.

Como en el mostrador, **no se pagina y no se cuenta**: se traen unos pocos y uno
de más, y con ese sobrante se sabe que hay que afinar.
"""

from django.utils.translation import gettext_lazy as _

from apps.busqueda import condicion
from apps.tutors.models import Tutor

PARAMETRO_DE_BUSQUEDA = "q"

# Menos que en el mostrador: aquí ya se sabe a quién se busca —está delante,
# o al teléfono— y la lista es para marcar a uno, no para leerla.
RESULTADOS = 10


class EleccionDeTutor:
    """Lo que se escribió para encontrar al Tutor y a quiénes se encontró."""

    # Con qué nombre viaja la caja. La plantilla lo lee de aquí en vez de
    # escribir "q" a mano, igual que en el mostrador.
    CAMPO = PARAMETRO_DE_BUSQUEDA

    HAY_MAS = _("Hay más de los que caben: afine la búsqueda.")

    def __init__(self, ofrecidos, buscado):
        self.buscado = (buscado or "").strip()
        coincide = condicion(Tutor.POR_DONDE_SE_BUSCA, self.buscado)
        # `None` es «nadie», no «todos»: con la caja vacía, o con unos dígitos
        # que no identifican a nadie, no se ofrece a ningún Tutor.
        traidos = (
            list(ofrecidos.filter(coincide).order_by("apellidos", "nombre", "pk")[: RESULTADOS + 1])
            if coincide is not None
            else []
        )
        self.hay_mas = len(traidos) > RESULTADOS
        self.resultados = traidos[:RESULTADOS]

    @property
    def vacia(self):
        """Si no se llegó a buscar nada, y por tanto no se sirvió ningún nombre."""
        return not self.buscado


def como_se_ofrece(tutor):
    """El rótulo de un Tutor en la lista: su nombre y por dónde se le llama.

    El teléfono va al lado porque dos Camila Rojas en la misma Clínica son
    normales, y es lo que recepción puede preguntar para saber cuál de las dos.
    """
    return f"{tutor} — {tutor.telefono}" if tutor.telefono else str(tutor)

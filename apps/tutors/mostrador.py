"""La caja única del mostrador: encontrar al Paciente con lo primero que haya a mano.

Recepción está al teléfono y escribe lo que tiene delante — el nombre del animal,
el de quien llama, un teléfono, un RUT o los quince dígitos que acaba de leer el
lector de chips — sin decidir antes en qué campo busca. Cómo se lee cada palabra
y en qué comparación se traduce lo decide `apps/busqueda.py`; por dónde se busca
a cada uno lo dicen los modelos (`POR_DONDE_SE_BUSCA`). Aquí vive lo que solo se
puede decidir viendo a los dos a la vez.

**Lo que se encuentra son Pacientes**, aunque se haya escrito el nombre de una
persona. Es la pregunta del mostrador: quién llama importa para saber de qué
animal habla. Un Tutor sin Pacientes no sale por aquí y no se pierde — está en su
fichero, que sigue teniendo su propia búsqueda (`listado.py`).

**Se busca entre quienes responden hoy.** Un Vínculo cerrado no encuentra al
Paciente: la fila diría un Tutor responsable que no es el que se acaba de
teclear, y quien llama es siempre el de ahora. De quién fue antes no se pierde
nada — lo dicen las dos fichas.

Este módulo vive en `tutors` y no en `patients` porque atraviesa el Vínculo, y el
Vínculo vive aquí por la misma razón que él: `tutors` conoce a `patients` y
`patients` no conoce a nadie (`CLAUDE.md`).

**No se pagina y no se cuenta.** La lista se repinta a cada pocas teclas, así que
un `COUNT(*)` de la consulta completa se pagaría entero en cada una de ellas para
enseñar un número que nadie mira mientras escribe. Se traen unos pocos resultados
y uno de más: con ese sobrante se sabe que hay más sin haber contado nada.
"""

from django.db.models import Prefetch, Q
from django.utils.translation import gettext_lazy as _

from apps.busqueda import condicion
from apps.patients.models import Paciente
from apps.tutors.models import Tutor, Vinculo

PARAMETRO_DE_BUSQUEDA = "q"

# Cuántos resultados se enseñan. Es un puñado a propósito: quien busca en el
# mostrador tiene delante a alguien esperando, y si su animal no está entre los
# primeros lo que hace falta es escribir otra palabra, no bajar por una lista.
RESULTADOS = 20

# Cómo se llaman los Vínculos ya traídos en cada Paciente. Es un atributo propio
# y no la relación de siempre porque `Paciente.quienes_responden` vuelve a
# preguntar a la base por cada ficha, y aquí hay veinte: sería el `N+1` que la
# tabla de resultados no puede permitirse.
RESPONSABLES = "responsables"

HUECO = "—"


class Resultado:
    """Una fila de resultados: el animal y lo que hace falta para confirmarlo por voz.

    Recepción lee en voz alta lo que ve — «¿Rocco, el gato de Camila Rojas?» —, y
    de eso salen las cuatro cosas que trae: el Paciente, su especie, quien
    responde por él y por dónde se le llama.
    """

    def __init__(self, paciente):
        self.paciente = paciente
        # Sin corchetes de rescate a propósito: un `Resultado` solo tiene
        # sentido sobre lo que devuelve `encontrados`, que trae ya los Vínculos.
        # Un `getattr` con valor por defecto convertiría el olvido del
        # `prefetch` en veinte filas sin Tutor responsable, que es un error que
        # se lee como un dato.
        vinculos = getattr(paciente, RESPONSABLES)
        self.vinculo = vinculos[0] if vinculos else None

    @property
    def responsable(self):
        """El Tutor que responde por él, o `None`.

        Puede no haberlo: un Paciente inactivo o fallecido se queda sin nadie
        cuando el animal cambió de manos o ya no está.
        """
        return self.vinculo.tutor if self.vinculo else None

    @property
    def especie(self):
        return self.paciente.get_especie_display()

    @property
    def telefono(self):
        return (self.responsable.telefono if self.responsable else "") or HUECO

    @property
    def quien_responde(self):
        return str(self.responsable) if self.responsable else HUECO

    @property
    def marca(self):
        """Lo que hay que decir de este animal antes de hablar de él, o nada.

        Del activo no hay nada que advertir. Marcados y no escondidos, que es lo
        contrario de lo que hace una lista de trabajo y por el motivo que
        explica `apps/patients/estados.py`.
        """
        return None if self.paciente.esta_activo else self.paciente.estado_a_la_vista


def encontrados(buscado):
    """Los Pacientes de la Clínica activa que casan con lo escrito.

    Dos maneras de llegar al mismo animal, y basta con una: que lo escrito esté
    en su propia ficha —su nombre, su chip— o que esté en la de alguien que
    responde por él hoy.

    Las dos se preguntan por separado y se unen aquí, y no en un solo filtro
    sobre los campos de los dos: con las palabras repartidas entre las dos fichas
    a la vez, «camila rojas» encontraría al animal de Camila que además tiene
    otro Tutor apellidado Rojas, que no es lo que nadie quiso preguntar.
    """
    del_paciente = condicion(Paciente.POR_DONDE_SE_BUSCA, buscado)
    del_tutor = condicion(Tutor.POR_DONDE_SE_BUSCA, buscado)

    # Ninguna condición es «nadie», no «todos»: una palabra que no cabe en
    # ningún campo de una ficha significa que por esa ficha no se llega.
    coincide = Q(pk__in=())
    if del_paciente is not None:
        coincide |= del_paciente
    if del_tutor is not None:
        # `Tutor.objects` ya está acotado a la Clínica activa, igual que los
        # Pacientes: la frontera se cruza dos veces y ninguna se dibuja aquí.
        coincide |= Q(
            vinculos__tutor__in=Tutor.objects.filter(del_tutor),
            vinculos__fecha_de_cierre__isnull=True,
        )

    return (
        Paciente.objects.filter(coincide)
        .distinct()
        # Por nombre y nada más. Ordenar primero por estado —los vivos delante—
        # parece de sentido común y es justo lo contrario: como la lista se
        # corta en `RESULTADOS`, poner detrás a los fallecidos es esconderlos
        # cada vez que la búsqueda es amplia, que es lo que el mostrador no
        # puede hacer. Salen marcados y en su sitio alfabético.
        .order_by("nombre", "pk")
        .prefetch_related(
            Prefetch(
                "vinculos",
                # Solo el del responsable: es el único Tutor que la fila nombra.
                # Por el manager sin filtro, como en `Paciente.quienes_responden`
                # y por lo mismo — un Vínculo nunca cruza la frontera de la
                # Clínica, y al Paciente ya se llegó por el manager filtrado.
                queryset=Vinculo.de_todas_las_clinicas.filter(responsable=True).select_related(
                    "tutor"
                ),
                to_attr=RESPONSABLES,
            )
        )
    )


class BusquedaDelMostrador:
    """Lo que recepción escribió y lo que se encontró con ello.

    Se resuelve al construirse, y la vista pregunta después si sirvió algo: lo
    que no se llegó a servir no se anota en el Registro de acceso, y eso incluye
    la página que se abre con la caja todavía vacía.
    """

    # Con qué nombre viaja el campo. La plantilla lo lee de aquí en vez de
    # escribir "q" a mano, igual que en el listado de Tutores.
    CAMPO = PARAMETRO_DE_BUSQUEDA

    # Lo que se dice cuando la caja está a medio escribir y coincide media
    # Clínica. Vive aquí y no en la plantilla porque es la otra mitad de
    # `RESULTADOS`: cambiar el tope sin decirlo dejaría una lista cortada en
    # silencio.
    HAY_MAS = _("Hay más de los que caben: afine la búsqueda.")

    def __init__(self, parametros):
        self.buscado = parametros.get(PARAMETRO_DE_BUSQUEDA, "").strip()
        # Uno de más: con él se sabe que hay más sin contar cuántos.
        traidos = list(encontrados(self.buscado)[: RESULTADOS + 1]) if self.buscado else []
        self.hay_mas = len(traidos) > RESULTADOS
        self.resultados = [Resultado(paciente) for paciente in traidos[:RESULTADOS]]

    @property
    def vacia(self):
        """Si no se llegó a buscar nada, y por tanto no se sirvió ningún dato."""
        return not self.buscado

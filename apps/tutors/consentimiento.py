"""Consentimiento de contacto: por qué canales acepta el Tutor que se le escriba.

Aquí viven el catálogo de canales, la pregunta que hará todo envío
—`se_puede_contactar`— y cómo se enseña lo que consta. El modelo que guarda cada
declaración está en `models.py`, al lado del Tutor de quien es; este módulo es
la puerta por la que se pregunta, y la única que H3 y H4 tienen que conocer.

Es una función y no una columna del Tutor porque **el valor de hoy no es el
dato**: lo que hay que poder enseñar es cuándo dijo que sí y cuándo se desdijo, y
eso son filas, no un booleano. Cada declaración se guarda entera y la última es
la que vale, igual que un Vínculo no se borra sino que se cierra con fecha.

Tres estados y no dos, por lo mismo que el Estado de identificación (`CONTEXT.md`):
**no consta** —nadie se lo ha preguntado— no es lo mismo que **revocado**. Los
dos niegan el envío, y no dicen lo mismo en el mostrador: uno es una pregunta
pendiente y el otro una respuesta que hay que respetar.

Y niega por defecto, que es la decisión que sostiene el resto: un canal del que
no consta nada no autoriza a nadie. Cualquier otro criterio convertiría un olvido
de recepción en un mensaje no consentido.

La regla —cuándo se puede contactar— se escribe **una sola vez**, en
`EstadoDelConsentimiento.se_puede_contactar`. Todo lo demás pasa por ahí, incluida
la función que preguntan H3 y H4: una regla de consentimiento repetida en dos
sitios es una regla que dentro de un año dice dos cosas distintas.
"""

from django.db import models
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _


class Canal(models.TextChoices):
    """Por dónde puede la clínica dirigirse a un Tutor.

    Catálogo cerrado en código y no tabla: un canal nuevo no es un dato que
    recepción dé de alta, es código que hay que escribir —quién lo envía, cómo
    se acusa recibo— antes de que signifique nada.
    """

    WHATSAPP = "whatsapp", _("WhatsApp")
    TELEFONO = "telefono", _("teléfono")
    CORREO = "correo", _("correo")


class LoQueDijo(models.TextChoices):
    """Lo que un Tutor puede haber contestado de un canal.

    Catálogo y no dos cadenas sueltas, por lo mismo que `Canal`: es lo que viaja
    en el formulario y lo que se lee en la historia, y con un rótulo propio se
    escribe una vez y no se traduce en cada plantilla.

    Dos opciones y no tres: **no consta** no se ofrece porque a no haberlo
    preguntado no se vuelve. Se llega a ese estado por no haber preguntado, y se
    sale de él contestando; lo que consta se deshace diciendo otra cosa, nunca
    borrándolo.
    """

    SI = "si", _("Sí, autoriza")
    NO = "no", _("No autoriza")


def lo_que_diria(otorgado):
    """Cómo se dice en voz alta lo que la fila guarda como sí o no."""
    return LoQueDijo.SI if otorgado else LoQueDijo.NO


def lo_ultimo_que_dijo(tutor, canal):
    """La última declaración del Tutor sobre ese canal, o `None` si no consta.

    Por el manager sin filtro, y no por descuido: esto lo pregunta el envío, que
    corre en una tarea y no dentro de una petición HTTP, así que no hay Clínica
    activa que valga. Volver a filtrar por ella no protegería nada —una
    declaración nunca cruza la frontera de la Clínica, porque sale del Tutor— y
    sí haría que fuera de una petición no constara nunca nada y no saliera nunca
    ningún mensaje. Es el mismo caso que `Tutor.de_quienes_se_hace_cargo`.
    """
    return tutor.consentimientos(manager="de_todas_las_clinicas").filter(canal=canal).first()


class EstadoDelConsentimiento:
    """Lo que consta de un canal, listo para preguntarlo o para enseñarlo.

    Envuelve a la última declaración —que puede no existir— y es justamente el
    hueco lo que justifica la clase: el canal del que nadie preguntó nada no
    tiene fila que responda por él, y sin este envoltorio cada pantalla y cada
    envío tendrían que acordarse de tratar ese `None`. Aquí se trata una vez, y
    de ahí sale también la regla que consulta todo el sistema.
    """

    def __init__(self, canal, ultima):
        canal = Canal(canal)
        self.canal = canal.value
        self.etiqueta = canal.label
        self.ultima = ultima

    @property
    def consta(self):
        """Si alguien llegó a preguntárselo al Tutor."""
        return self.ultima is not None

    @property
    def se_puede_contactar(self):
        """**La** regla: si la clínica puede dirigirse al Tutor por este canal.

        Niega cuando no consta nada. Ver el módulo.
        """
        return self.consta and self.ultima.otorgado

    @property
    def fecha(self):
        """Desde cuándo es verdad lo que consta, o `None` si no consta nada."""
        return self.ultima.fecha if self.consta else None

    @property
    def lo_que_dijo(self):
        """Lo que el formulario trae puesto: lo último, o el hueco si no consta."""
        return lo_que_diria(self.ultima.otorgado) if self.consta else ""

    @property
    def a_la_vista(self):
        """La frase que lee quien está a punto de contactar a este Tutor.

        Las tres dicen la fecha o dicen que no hay ninguna, porque un
        consentimiento sin fecha no es evidencia de nada ante la Ley 21.719.
        """
        if not self.consta:
            return _("No consta: nadie se lo ha preguntado todavía.")
        # La fecha se compone aquí y no en la plantilla porque va dentro de la
        # frase: partirla en dos dejaría media traducción en cada sitio.
        cuando = {"fecha": date_format(self.fecha)}
        if self.ultima.otorgado:
            return _("Autorizado el %(fecha)s.") % cuando
        return _("Revocado el %(fecha)s.") % cuando


def como_esta_el_canal(tutor, canal):
    """Lo que consta de un canal concreto de este Tutor."""
    return EstadoDelConsentimiento(canal, lo_ultimo_que_dijo(tutor, canal))


def se_puede_contactar(tutor, canal):
    """Si la clínica puede dirigirse a este Tutor por ese canal. **La** pregunta.

    H3 y H4 la hacen antes de cada envío, y por eso es una función con nombre y
    tests propios y no una condición suelta dentro de la vista que manda: una
    regla de consentimiento repetida en tres sitios es una regla que dentro de un
    año dice tres cosas distintas. La regla misma vive en
    `EstadoDelConsentimiento`; esto es la puerta por la que se llama.
    """
    return como_esta_el_canal(tutor, canal).se_puede_contactar


def como_esta(tutor):
    """Lo que consta de **cada** canal, en el orden del catálogo.

    Los tres siempre, conste algo o no: el canal del que no se sabe nada es
    justamente el que hay que preguntar, y esconderlo hasta que alguien lo
    rellene es lo que deja la pregunta sin hacer para siempre.

    De una consulta sola, y no una por canal: la ficha del Tutor la pinta cada
    vez que recepción la abre.
    """
    ultima_por_canal = {}
    # Ordenadas de lo más reciente a lo más antiguo por el `Meta` del modelo, así
    # que la primera de cada canal es la que vale y las siguientes no la pisan.
    for dicho in tutor.consentimientos(manager="de_todas_las_clinicas").all():
        ultima_por_canal.setdefault(dicho.canal, dicho)
    return [EstadoDelConsentimiento(canal, ultima_por_canal.get(canal.value)) for canal in Canal]

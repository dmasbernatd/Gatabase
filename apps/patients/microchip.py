"""El microchip: cómo se lee lo que trae el lector y cómo se guarda y se presenta.

Se guarda **de corrido**, quince dígitos y nada más — «900123456789012» —, que
es la única forma en que dos chips iguales se parecen entre sí. Nadie lo escribe
así: el lector lo escupe de corrido, el certificado del implantador lo trae en
grupos de tres y recepción lo teclea del carnet con puntos o con guiones. Todas
esas formas entran por `normalizado` y salen iguales, y de eso depende que
«único dentro de la Clínica» signifique algo y que buscar por chip (ticket 11)
encuentre al animal.

Se presenta al revés, con `formateado`: en grupos de tres, que es como se dicta
por teléfono y como se compara con un certificado a ojo. Quince dígitos de
corrido no se leen en voz alta sin perder la cuenta.

El largo es lo único que se comprueba, y es lo que se puede comprobar. El
estándar ISO 11784 con el que se implanta en Chile son quince dígitos —los tres
primeros, el código del país o del fabricante— y no lleva dígito verificador: un
chip mal tecleado no se delata solo, así que atrapar el dígito que se cayó al
copiarlo es todo lo que este módulo puede hacer por el mostrador.

Que el número esté apuntado no dice **nada** sobre si el animal está inscrito en
el Registro Nacional. Eso es el estado de identificación, que es un campo aparte
del Paciente por ese mismo motivo.
"""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Lo que sobra al escribir un chip: la puntuación con la que viene agrupado.
SEPARADORES = str.maketrans("", "", ". - ‐‑‒–—")

# Los que lleva un chip ISO 11784, que es el que se implanta en Chile.
DIGITOS = 15

# De cuántos en cuántos se dicta y se lee.
GRUPO = 3


class MicrochipInvalido(ValidationError):
    """Lo escrito no es un número de chip. Es una `ValidationError` para que
    llegue sola hasta el campo del formulario que lo pidió, con su mensaje
    puesto."""


def digitos_del_microchip(escrito):
    """Lo escrito reducido a lo que un chip lleva: dígitos.

    Es lo que hace que buscar «900 123» encuentre al Paciente cuyo chip se
    guardó de corrido. No valida nada: lo que devuelve puede no ser un chip.
    """
    return "".join(
        caracter for caracter in (escrito or "").translate(SEPARADORES) if caracter.isdigit()
    )


def normalizado(escrito):
    """El chip como se guarda, a partir de como se escribió.

    Devuelve `""` cuando no se escribió nada: el chip es opcional —llega a la
    consulta un animal sin chip, y exigirlo en el mostrador sería negarle la
    atención— y un hueco no es un error.
    """
    escrito = (escrito or "").strip()
    if not escrito:
        return ""

    # Lo escrito sí traía algo, y de ese algo no queda todo: eso no es un hueco,
    # es un chip que no se entiende. Decirlo es lo que evita que una nota
    # escrita en la casilla —«no tiene», «ilegible»— se guarde como un chip.
    chip = digitos_del_microchip(escrito)
    if chip != escrito.translate(SEPARADORES):
        raise MicrochipInvalido(
            _("El microchip son %(cuantos)s dígitos, sin letras."),
            code="microchip_ilegible",
            params={"cuantos": DIGITOS},
        )
    if len(chip) != DIGITOS:
        # El mensaje dice cuántos llegaron: casi siempre falta o sobra uno al
        # copiarlo, y verlo al lado es lo que deja encontrarlo.
        raise MicrochipInvalido(
            _("Un microchip lleva %(cuantos)s dígitos, y ese lleva %(cuantos_hay)s."),
            code="microchip_de_largo_imposible",
            params={"cuantos": DIGITOS, "cuantos_hay": len(chip)},
        )
    return chip


def formateado(chip):
    """El chip en grupos de tres: «900 123 456 789 012».

    Lo que no sea un chip ya normalizado vuelve tal cual. Pasa al repintar un
    formulario que no se pudo guardar: allí el valor es todavía lo que se
    tecleó, y devolvérselo cambiado a quien está corrigiendo una errata sería
    esconderle la errata.
    """
    if not chip or chip != digitos_del_microchip(chip) or len(chip) != DIGITOS:
        return chip
    return " ".join(chip[posicion : posicion + GRUPO] for posicion in range(0, DIGITOS, GRUPO))

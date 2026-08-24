"""El teléfono: cómo se lee lo que dicta el Tutor y cómo se guarda.

Se guarda en E.164 —«+56912345678»—, que es la forma que no admite dos lecturas:
lleva el país delante y no lleva nada más. Es la que después sirve para llamar,
para escribir por WhatsApp y para reconocer que dos Tutores son la misma familia.

Recepción no lo escribe así. Lo escribe como se lo dictan, y en Chile se dicta de
todas estas maneras a la vez:

    +56 9 1234 5678      con país y con espacios
    56912345678          con país y de corrido
    912345678            sin país
    09 1234 5678         con el cero de marcar de antes
    1234 5678            sin país y sin el 9, que se da por sabido

Las cinco son el mismo teléfono y las cinco entran. La última es la única que
adivina algo: ocho dígitos sueltos se leen como un celular al que le falta su 9,
porque es lo que se dicta en el mostrador. Un fijo necesita su código de área
—«22 345 6789» son nueve dígitos y entra como tal—, y ese es el precio de
aceptar la forma corta.

Un Tutor extranjero también se registra: cualquier número escrito con su `+` y su
código de país se guarda tal cual.
"""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

PAIS = "56"
MOVIL = "9"

# Lo que E.164 admite en total, sin contar el `+`.
DIGITOS_MINIMOS = 8
DIGITOS_MAXIMOS = 15

# Cuántos dígitos tiene un número chileno una vez quitado el país.
LARGO_NACIONAL = 9
# Y cuántos tiene un celular al que se le calló el 9.
LARGO_DE_MOVIL_CORTO = 8

# El 0 de marcar larga distancia dentro del país y el 00 de salir de él: se
# marcaban, nunca fueron parte del número.
SALIDA_INTERNACIONAL = "00"
TRONCAL_NACIONAL = "0"


# El consejo es el mismo venga el fallo de donde venga: lo que falta es siempre
# o el largo chileno o el código del país.
COMO_SE_ESCRIBE = _(
    "No se entiende como un teléfono. Escríbelo con sus nueve dígitos "
    "—«9 1234 5678»— o, si es de otro país, con su + y su código."
)


class TelefonoInvalido(ValidationError):
    """Lo escrito no se deja leer como un teléfono."""


def digitos_del_telefono(escrito):
    """Lo escrito reducido a sus dígitos.

    Es lo que hace que buscar «9 1234 5678» encuentre al Tutor cuyo teléfono se
    guardó como «+56912345678». No valida nada.
    """
    return "".join(caracter for caracter in (escrito or "") if caracter.isdigit())


def como_se_busca(escrito):
    """Los dígitos por los que buscar este teléfono, o nada si no los hay.

    Lo guardado es E.164 —«+56912345678»— y lo escrito es cualquiera de las
    formas del mostrador. Lo que todas tienen en común son los dígitos finales,
    así que se busca por ellos y se quita el 0 de delante: el troncal se marcaba
    —«09 1234 5678»— y nunca fue parte del número, de modo que buscarlo tal cual
    no encontraría al Tutor que sí está.
    """
    return digitos_del_telefono(escrito).lstrip(TRONCAL_NACIONAL)


def _en_e164(digitos):
    if not DIGITOS_MINIMOS <= len(digitos) <= DIGITOS_MAXIMOS:
        raise TelefonoInvalido(COMO_SE_ESCRIBE, code="telefono_de_largo_imposible")
    return "+" + digitos


def normalizado(escrito):
    """El teléfono como se guarda, a partir de como se escribió.

    Devuelve `""` cuando no se escribió nada: en el mostrador a veces solo hay un
    nombre.
    """
    escrito = (escrito or "").strip()
    if not escrito:
        return ""

    digitos = digitos_del_telefono(escrito)
    if not digitos:
        raise TelefonoInvalido(
            _("Un teléfono se escribe con números."), code="telefono_sin_numeros"
        )

    # Un `+` delante ya dice de qué país es: no hay nada que adivinar, y así se
    # registra a un Tutor extranjero sin que el sistema le corrija el número.
    if escrito.startswith("+"):
        return _en_e164(digitos)
    if digitos.startswith(SALIDA_INTERNACIONAL):
        return _en_e164(digitos[len(SALIDA_INTERNACIONAL) :])

    nacional = digitos.removeprefix(TRONCAL_NACIONAL)
    if nacional.startswith(PAIS) and len(nacional) == len(PAIS) + LARGO_NACIONAL:
        return _en_e164(nacional)
    if len(nacional) == LARGO_NACIONAL:
        return _en_e164(PAIS + nacional)
    if len(nacional) == LARGO_DE_MOVIL_CORTO:
        return _en_e164(PAIS + MOVIL + nacional)

    raise TelefonoInvalido(COMO_SE_ESCRIBE, code="telefono_de_largo_imposible")

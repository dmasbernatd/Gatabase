"""El RUT: cómo se lee lo que dicta el Tutor y cómo se guarda y se presenta.

Se guarda **sin puntos ni guion** y con la `K` en mayúscula —«123456785»—, que es
la única forma en que dos RUT iguales se parecen entre sí. Recepción no lo
escribe así: lo escribe como se lo dictan, y se lo dictan con puntos, con guion,
con espacios o de corrido. Todas esas formas entran por `normalizado` y salen
iguales.

Se presenta al revés, con `formateado`: a la chilena, que es como se lee en voz
alta y como aparece en la cédula. Nadie reconoce su propio RUT escrito de
corrido.

El dígito verificador se comprueba al entrar. No es una regla de formato: es una
suma que solo cuadra si los dígitos son los que son, así que atrapa el error de
tecleo del mostrador —un dígito cambiado, dos dígitos girados— en el momento en
que se comete y no el día que haya que emitir una boleta.
"""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Lo que sobra al escribir un RUT: la puntuación con la que se dicta.
SEPARADORES = str.maketrans("", "", ". - ‐‑‒–—")

# El dígito verificador puede ser una `K`; el resto del RUT, solo dígitos.
DIGITO_ONCE = "K"

# Un RUT chileno vivo va del millón al 99.999.999: personas por debajo del
# primer tramo y sociedades por encima del último. Fuera de ahí no hay un RUT
# raro, hay un error de tecleo, y conviene decirlo antes que hacer la suma.
DIGITOS_MINIMOS = 7
DIGITOS_MAXIMOS = 8


class RutInvalido(ValidationError):
    """Lo escrito no es un RUT. Es una `ValidationError` para que llegue sola
    hasta el campo del formulario que lo pidió, con su mensaje puesto."""


def caracteres_del_rut(escrito):
    """Lo escrito reducido a lo que un RUT lleva: dígitos y quizá una `K`.

    Es lo que hace que buscar «12.345.678» encuentre al Tutor cuyo RUT se guardó
    de corrido. No valida nada: lo que devuelve puede no ser un RUT.
    """
    return "".join(
        caracter
        for caracter in (escrito or "").translate(SEPARADORES).upper()
        if caracter.isdigit() or caracter == DIGITO_ONCE
    )


def como_se_busca(escrito):
    """Lo escrito leído como un trozo de RUT, o nada si no lo parece.

    Un RUT siempre lleva dígitos. Sin ninguno, lo escrito es un nombre y no un
    RUT a medias: buscar la «k» de «Karla» entre los RUT traería a todos los que
    acaban en K, que no se parecen a ella en nada.
    """
    trozo = caracteres_del_rut(escrito)
    return trozo if any(caracter.isdigit() for caracter in trozo) else ""


def digito_verificador(cuerpo):
    """El dígito que le toca a ese cuerpo: módulo 11 con la serie 2..7."""
    suma = 0
    factor = 2
    for digito in reversed(cuerpo):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - suma % 11
    return {11: "0", 10: DIGITO_ONCE}.get(resto, str(resto))


def normalizado(escrito):
    """El RUT como se guarda, a partir de como se escribió.

    Devuelve `""` cuando no se escribió nada: el RUT es opcional —hay Tutores
    extranjeros, y hay quien no lo quiere dar— y un hueco no es un error.
    """
    escrito = (escrito or "").strip()
    if not escrito:
        return ""

    # Lo escrito sí traía algo, y de ese algo no queda nada aprovechable: eso no
    # es un hueco, es un RUT que no se entiende, y decirlo es lo que evita que
    # una ficha se guarde como si el Tutor no hubiera dado ninguno.
    rut = caracteres_del_rut(escrito)
    cuerpo, verificador = rut[:-1], rut[-1:]
    if not verificador or not cuerpo.isdigit():
        raise RutInvalido(
            _("El RUT se escribe con números y, al final, su dígito verificador."),
            code="rut_ilegible",
        )
    if not DIGITOS_MINIMOS <= len(cuerpo) <= DIGITOS_MAXIMOS:
        raise RutInvalido(
            _("Un RUT lleva entre %(minimo)s y %(maximo)s dígitos antes del verificador."),
            code="rut_de_largo_imposible",
            params={"minimo": DIGITOS_MINIMOS, "maximo": DIGITOS_MAXIMOS},
        )

    esperado = digito_verificador(cuerpo)
    if verificador != esperado:
        # El mensaje dice cuál tendría que ser: casi siempre lo que falla es un
        # dígito del cuerpo, y verlo al lado es lo que deja encontrarlo.
        raise RutInvalido(
            _("El dígito verificador no corresponde: para %(cuerpo)s tendría que ser %(cual)s."),
            code="digito_verificador_que_no_cuadra",
            params={"cuerpo": cuerpo, "cual": esperado},
        )
    return cuerpo + verificador


def formateado(rut):
    """El RUT a la chilena: «12.345.678-5».

    Lo que no sea un RUT ya normalizado vuelve tal cual. Pasa al repintar un
    formulario que no se pudo guardar: allí el valor es todavía lo que se
    tecleó, y devolvérselo cambiado a quien está corrigiendo una errata sería
    esconderle la errata.
    """
    if not rut or len(rut) < DIGITOS_MINIMOS + 1 or rut != caracteres_del_rut(rut):
        return rut

    cuerpo, verificador = rut[:-1], rut[-1]
    if not cuerpo.isdigit():
        return rut

    grupos = []
    while len(cuerpo) > 3:
        grupos.insert(0, cuerpo[-3:])
        cuerpo = cuerpo[:-3]
    grupos.insert(0, cuerpo)
    return ".".join(grupos) + "-" + verificador

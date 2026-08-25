"""Cómo se lee lo que recepción teclea: el RUT y el teléfono.

Son las dos formas en que un mismo dato se escribe de muchas maneras y tiene que
quedar guardado de una sola. Se prueban aquí, sin base de datos y sin HTTP,
porque son decisiones de lectura y no de pantalla: el resto de la aplicación —el
formulario, el listado, el importador del 17— se apoya en que estas reglas sean
las mismas en todas partes.

Lo que ocurre al guardar una ficha con un RUT repetido o un teléfono compartido
se prueba por HTTP, en `test_fichas_de_tutor.py`: eso ya no es leer un dato, es
qué hace la Clínica con él.
"""

import pytest

from apps import telefono
from apps.tutors import rut

# Un RUT de verdad, escrito de las cinco formas en que lo dicta un Tutor.
RUT = "123456785"
FORMATEADO = "12.345.678-5"

# Los dos casos que el módulo 11 trata aparte: el 11 se escribe `0` y el 10, `K`.
RUT_CON_K = "12000008K"
RUT_CORTO = "51266633"


# --- RUT ------------------------------------------------------------------


@pytest.mark.parametrize(
    "escrito",
    [
        "12.345.678-5",
        "12345678-5",
        "123456785",
        "12 345 678 5",
        "  12.345.678-5  ",
        "12.345.678-5\n",
    ],
)
def test_el_rut_se_guarda_igual_se_escriba_como_se_escriba(escrito):
    assert rut.normalizado(escrito) == RUT


def test_un_rut_con_k_se_guarda_con_la_k_en_mayuscula():
    """La `K` es el dígito verificador 10. Escrita en minúscula es el mismo RUT,
    y guardarla de las dos formas rompería que el RUT sea único."""
    assert rut.normalizado("12.000.008-k") == RUT_CON_K
    assert rut.normalizado("12.000.008-K") == RUT_CON_K


def test_un_rut_de_siete_digitos_tambien_vale():
    """Los RUT antiguos tienen un dígito menos, y sus dueños siguen vivos."""
    assert rut.normalizado("5.126.663-3") == RUT_CORTO


def test_no_dar_el_rut_no_es_un_error():
    """Es opcional: hay Tutores extranjeros, y hay quien no lo quiere dar."""
    assert rut.normalizado("") == ""
    assert rut.normalizado(None) == ""
    assert rut.normalizado("   ") == ""


@pytest.mark.parametrize("escrito", ["12.345.678-4", "12.345.678-0", "12.000.008-1"])
def test_un_rut_con_el_digito_verificador_cambiado_no_pasa(escrito):
    with pytest.raises(rut.RutInvalido):
        rut.normalizado(escrito)


def test_el_aviso_del_digito_verificador_dice_cual_tendria_que_ser():
    """Casi siempre lo que falla es un dígito del cuerpo, no el verificador:
    verlo al lado es lo que deja encontrar la errata."""
    with pytest.raises(rut.RutInvalido) as fallo:
        rut.normalizado("12.345.678-4")

    assert "5" in " ".join(fallo.value.messages)


def test_dos_digitos_girados_dejan_de_cuadrar():
    """Es el error de tecleo del mostrador, y es justo lo que el módulo 11 pilla."""
    with pytest.raises(rut.RutInvalido):
        rut.normalizado("12.345.687-5")


@pytest.mark.parametrize(
    "escrito",
    [
        "no es un rut",  # algo se escribió, y no queda nada aprovechable
        "K",
        "12.345.678-X",  # solo la K vale como undécimo dígito
        "1K3456785",  # la K solo puede ir al final
        "1-9",  # demasiado corto para ser el RUT de nadie
        "1.234.567.890-1",  # demasiado largo
    ],
)
def test_lo_que_no_es_un_rut_no_se_guarda(escrito):
    with pytest.raises(rut.RutInvalido):
        rut.normalizado(escrito)


def test_el_rut_se_presenta_a_la_chilena():
    assert rut.formateado(RUT) == FORMATEADO
    assert rut.formateado(RUT_CORTO) == "5.126.663-3"
    assert rut.formateado(RUT_CON_K) == "12.000.008-K"


def test_lo_que_no_es_un_rut_guardado_se_presenta_tal_cual():
    """Pasa al repintar un formulario que no se pudo guardar: ahí el valor es
    todavía lo que se tecleó, y devolvérselo cambiado a quien está corrigiendo
    una errata sería esconderle la errata."""
    assert rut.formateado("") == ""
    assert rut.formateado("12.345.678-4") == "12.345.678-4"
    assert rut.formateado("lo que sea") == "lo que sea"


@pytest.mark.parametrize("escrito, buscado", [("12.345.678", "12345678"), ("678-5", "6785")])
def test_buscar_un_rut_ignora_la_puntuacion_con_que_se_escribe(escrito, buscado):
    assert rut.como_se_busca(escrito) == buscado


def test_un_nombre_no_se_busca_entre_los_rut():
    """La «k» de «Karla» traería a todos los Tutores cuyo RUT acaba en K."""
    assert rut.como_se_busca("Karla") == ""
    assert rut.como_se_busca("camila") == ""


# --- Teléfono -------------------------------------------------------------


MOVIL = "+56912345678"


@pytest.mark.parametrize(
    "escrito",
    [
        "+56912345678",
        "+56 9 1234 5678",
        "56912345678",
        "56 9 1234 5678",
        "912345678",
        "9 1234 5678",
        "09 1234 5678",
        "0912345678",
        "12345678",
        "1234 5678",
        "(9) 1234-5678",
        "0056912345678",
    ],
)
def test_el_movil_se_guarda_igual_se_escriba_como_se_escriba(escrito):
    assert telefono.normalizado(escrito) == MOVIL


def test_un_fijo_con_su_codigo_de_area_tambien_entra():
    """Nueve dígitos son nueve dígitos: el 2 de Santiago ocupa el sitio del 9."""
    assert telefono.normalizado("22 345 6789") == "+56223456789"


def test_un_numero_extranjero_se_guarda_tal_cual():
    """Un Tutor extranjero se registra igual, y su número no se corrige."""
    assert telefono.normalizado("+34 600 123 456") == "+34600123456"


def test_no_dar_el_telefono_no_es_un_error():
    assert telefono.normalizado("") == ""
    assert telefono.normalizado(None) == ""
    assert telefono.normalizado("   ") == ""


@pytest.mark.parametrize(
    "escrito",
    [
        "sin números",
        "1234",  # demasiado corto para ser el teléfono de nadie
        "1234567",
        "1234567890",  # ni nueve dígitos ni ocho ni con país delante
        "+1234567",
        "+1234567890123456",
    ],
)
def test_lo_que_no_se_deja_leer_como_telefono_no_se_guarda(escrito):
    with pytest.raises(telefono.TelefonoInvalido):
        telefono.normalizado(escrito)


def test_el_aviso_dice_como_se_escribe_un_telefono():
    with pytest.raises(telefono.TelefonoInvalido) as fallo:
        telefono.normalizado("1234")

    assert "9 1234 5678" in " ".join(fallo.value.messages)


@pytest.mark.parametrize("escrito, buscado", [("9 1234 5678", "912345678"), ("+56 9", "569")])
def test_buscar_un_telefono_ignora_los_espacios_y_el_mas(escrito, buscado):
    assert telefono.digitos_del_telefono(escrito) == buscado


def test_un_nombre_no_se_busca_entre_los_telefonos():
    assert telefono.digitos_del_telefono("camila") == ""

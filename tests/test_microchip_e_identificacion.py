"""El microchip del Paciente y el estado de identificación de la Ley 21.020.

Son dos cosas distintas a propósito, y el ticket 08 insiste en ello: tener el
número apuntado no es estar inscrito. Un animal puede llevar el chip puesto y no
constar en el Registro Nacional, y eso —no la falta de chip— es lo que recepción
tiene que poder decirle al Tutor.

La primera mitad prueba cómo se lee un número de chip, sin base de datos y sin
HTTP: es una decisión de lectura, y de ella depende que el chip sirva para
encontrar al animal (ticket 11) y que «único dentro de la Clínica» signifique
algo. La segunda entra por HTTP, como entra recepción.
"""

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.audit.models import Accion, RegistroDeAcceso
from apps.patients import microchip
from apps.patients.catalogo import Especie
from apps.patients.models import EstadoDeIdentificacion, Paciente
from tests.factories import ClinicaFactory, PacienteFactory, TutorFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

# Un número de chip como los que se implantan en Chile: quince dígitos que
# empiezan por el código de país del fabricante.
CHIP = "900123456789012"
OTRO_CHIP = "985112001234567"


def recepcion(client):
    """Quien está en el mostrador: el rol que registra y corrige fichas."""
    usuario = UsuarioFactory(rol="recepcion")
    client.force_login(usuario)
    return usuario


def anotaciones_sobre(objeto, accion):
    return RegistroDeAcceso.de_todas_las_clinicas.filter(
        tipo_de_objeto=objeto._meta.label, identificador=str(objeto.pk), accion=accion
    )


def datos_de(paciente, **cambios):
    """La ficha de ese Paciente tal como la reenvía el formulario de corrección."""
    return {
        "nombre": paciente.nombre,
        "especie": paciente.especie,
        "raza": paciente.raza,
        "sexo": paciente.sexo,
        "fecha_de_nacimiento": "",
        "color": paciente.color,
        "observaciones": paciente.observaciones,
        "microchip": paciente.microchip,
        "estado_de_identificacion": paciente.estado_de_identificacion,
    } | cambios


def corregir(client, paciente, **cambios):
    return client.post(reverse("patients:editar", args=[paciente.pk]), datos_de(paciente, **cambios))


# --- Cómo se lee un número de chip ----------------------------------------


@pytest.mark.parametrize(
    "escrito",
    [
        "900123456789012",
        "900 123 456 789 012",
        "900.123.456.789.012",
        "900-123-456-789-012",
        "  900123456789012  ",
        "900123456789012\n",
    ],
)
def test_el_microchip_se_guarda_igual_se_escriba_como_se_escriba(escrito):
    """El lector lo escupe de corrido, el certificado lo trae en grupos y
    recepción lo teclea de memoria. Las tres formas son el mismo animal, y si se
    guardaran distintas «único dentro de la Clínica» no significaría nada."""
    assert microchip.normalizado(escrito) == CHIP


def test_no_tener_chip_no_es_un_error():
    """El microchip es opcional: llega a la consulta un animal sin chip, y
    exigirlo en el mostrador sería negarle la atención."""
    assert microchip.normalizado("") == ""
    assert microchip.normalizado(None) == ""
    assert microchip.normalizado("   ") == ""


@pytest.mark.parametrize("escrito", ["90012345678901", "9001234567890123", "1"])
def test_un_microchip_que_no_lleva_quince_digitos_no_se_guarda(escrito):
    """Quince es el largo del estándar ISO con el que se implanta en Chile. Uno
    de menos o uno de más es un dígito que se cayó al teclear, y verlo ahora es
    verlo antes de que el chip deje de encontrar al animal."""
    with pytest.raises(microchip.MicrochipInvalido):
        microchip.normalizado(escrito)


@pytest.mark.parametrize("escrito", ["900123456789O12", "no tiene", "abcdefghijklmno"])
def test_un_microchip_con_algo_que_no_es_un_digito_no_se_guarda(escrito):
    """Un chip son dígitos y nada más. La `O` por el cero es el error de tecleo
    de la casa, y una nota escrita en la casilla —«no tiene»— sería un chip."""
    with pytest.raises(microchip.MicrochipInvalido):
        microchip.normalizado(escrito)


def test_el_microchip_se_presenta_en_grupos_para_poder_dictarlo():
    """Quince dígitos de corrido no se leen en voz alta ni se comparan con un
    certificado a ojo."""
    assert microchip.formateado(CHIP) == "900 123 456 789 012"
    assert microchip.formateado("") == ""


@pytest.mark.parametrize("escrito", ["9001234", "900123456789O12", "no tiene"])
def test_lo_que_no_es_un_chip_se_presenta_tal_cual(escrito):
    """Es lo que pasa al repintar un formulario que no se pudo guardar: el valor
    es todavía lo que se tecleó, y devolvérselo agrupado a quien está
    corrigiendo una errata sería esconderle la errata."""
    assert microchip.formateado(escrito) == escrito


def test_un_microchip_rechazado_vuelve_tal_como_se_tecleo(client):
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    respuesta = corregir(client, paciente, microchip="900 123 456 789 01")

    assert "900 123 456 789 01" in respuesta.content.decode()


# --- El microchip en la ficha ---------------------------------------------


def test_recepcion_apunta_el_microchip_de_un_paciente(client):
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    corregir(client, paciente, microchip="900 123 456 789 012")

    paciente.refresh_from_db()
    assert paciente.microchip == CHIP


def test_la_ficha_enseña_el_microchip_en_grupos(client):
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic, microchip=CHIP)

    contenido = client.get(reverse("patients:ficha", args=[paciente.pk])).content.decode()

    assert "900 123 456 789 012" in contenido


def test_un_microchip_ilegible_no_deja_guardar_la_ficha(client):
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    respuesta = corregir(client, paciente, microchip="9001234")

    assert respuesta.status_code == 200
    paciente.refresh_from_db()
    assert paciente.microchip == ""


# --- Único dentro de la Clínica, y solo dentro (ADR-0001) -----------------


def test_un_microchip_que_ya_esta_en_la_clinica_no_se_guarda_y_lleva_a_la_ficha(client):
    """Dos fichas con el mismo chip son el mismo animal registrado dos veces, y
    un duplicado sale caro de deshacer. El aviso lleva a la ficha que ya existe,
    que es a lo que recepción venía casi siempre."""
    usuario = recepcion(client)
    ya_registrado = PacienteFactory(clinic=usuario.clinic, nombre="Rocco", microchip=CHIP)
    paciente = PacienteFactory(clinic=usuario.clinic, nombre="Luna")

    respuesta = corregir(client, paciente, microchip="900.123.456.789.012")

    assert respuesta.status_code == 200
    paciente.refresh_from_db()
    assert paciente.microchip == ""
    assert reverse("patients:ficha", args=[ya_registrado.pk]) in respuesta.content.decode()
    assert "Rocco" in respuesta.content.decode()


def test_avisar_de_un_microchip_repetido_deja_constancia_de_la_lectura(client):
    """El aviso dice el nombre del otro Paciente y enlaza a su ficha: quien lo
    lee ha visto su ficha sin haberla abierto (ADR-0004)."""
    usuario = recepcion(client)
    ya_registrado = PacienteFactory(clinic=usuario.clinic, microchip=CHIP)
    paciente = PacienteFactory(clinic=usuario.clinic)

    corregir(client, paciente, microchip=CHIP)

    assert anotaciones_sobre(ya_registrado, Accion.LECTURA).get().usuario == usuario


def test_dos_clinicas_pueden_tener_el_mismo_microchip(client):
    """El chip identifica al animal en todo Chile, pero cada Clínica tiene su
    propio Paciente con su propia Historia clínica (ADR-0001). Que el mismo
    número exista en otra Clínica es correcto y no se detecta: detectarlo sería
    cruzar datos entre tenants, que es lo que el ADR prohíbe."""
    usuario = recepcion(client)
    PacienteFactory(clinic=ClinicaFactory(), microchip=CHIP)
    paciente = PacienteFactory(clinic=usuario.clinic)

    respuesta = corregir(client, paciente, microchip=CHIP)

    assert respuesta.status_code == 302
    paciente.refresh_from_db()
    assert paciente.microchip == CHIP
    assert Paciente.de_todas_las_clinicas.filter(microchip=CHIP).count() == 2


def test_la_base_de_datos_no_deja_repetir_un_microchip_dentro_de_la_clinica():
    """No depende de que nadie abra dos pestañas ni de que el importador del 18
    se acuerde de preguntar."""
    clinica = ClinicaFactory()
    PacienteFactory(clinic=clinica, microchip=CHIP)

    with pytest.raises(IntegrityError), transaction.atomic():
        PacienteFactory(clinic=clinica, microchip=CHIP)


def test_dos_pacientes_sin_chip_no_son_el_mismo_paciente():
    """El hueco se guarda como cadena vacía y la restricción lo deja fuera: si
    no, el segundo Paciente sin chip sería imposible de registrar."""
    clinica = ClinicaFactory()
    PacienteFactory(clinic=clinica)
    PacienteFactory(clinic=clinica)

    assert Paciente.de_todas_las_clinicas.filter(clinic=clinica, microchip="").count() == 2


def test_corregir_una_ficha_no_choca_con_su_propio_microchip(client):
    """Un Paciente no se duplica a sí mismo: cambiarle el color no puede
    tropezar con el chip que ya tenía."""
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic, microchip=CHIP)

    respuesta = corregir(client, paciente, color="Atigrado")

    paciente.refresh_from_db()
    assert respuesta.status_code == 302
    assert paciente.color == "Atigrado"
    assert paciente.microchip == CHIP


# --- El estado de identificación ------------------------------------------


def test_el_estado_de_identificacion_no_se_deduce_del_microchip(client):
    """Es un campo propio, y esa es la razón de ser del ticket: el número
    apuntado no dice si el animal está inscrito en el Registro Nacional, que es
    lo único que la Ley 21.020 da por cumplido."""
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    corregir(
        client,
        paciente,
        microchip=CHIP,
        estado_de_identificacion=EstadoDeIdentificacion.IMPLANTADO,
    )

    paciente.refresh_from_db()
    assert paciente.microchip == CHIP
    assert paciente.estado_de_identificacion == EstadoDeIdentificacion.IMPLANTADO


def test_un_paciente_con_el_chip_puesto_en_otra_parte_puede_no_traer_el_numero(client):
    """Se lo implantaron en otra clínica y el Tutor no trae el certificado. Es
    un estado real, y obligar a un número aquí obligaría a inventárselo."""
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    respuesta = corregir(
        client, paciente, estado_de_identificacion=EstadoDeIdentificacion.IMPLANTADO
    )

    paciente.refresh_from_db()
    assert respuesta.status_code == 302
    assert paciente.microchip == ""
    assert paciente.estado_de_identificacion == EstadoDeIdentificacion.IMPLANTADO


def test_un_numero_de_chip_con_sin_chip_no_se_guarda(client):
    """Es la única de las combinaciones que se contradice a sí misma, y sale de
    corregir una casilla y olvidar la otra."""
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    respuesta = corregir(
        client, paciente, microchip=CHIP, estado_de_identificacion=EstadoDeIdentificacion.SIN_CHIP
    )

    assert respuesta.status_code == 200
    paciente.refresh_from_db()
    assert paciente.microchip == ""


def test_no_haber_preguntado_todavia_no_es_no_tener_chip(client):
    """Como el Estado sanitario `desconocido` de `CONTEXT.md`: lo que nadie ha
    mirado no es un «no». Decirle a un Tutor que su perro no tiene chip porque
    la casilla llegó en blanco sería decirle algo que nadie comprobó."""
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    assert paciente.estado_de_identificacion == ""
    assert paciente.estado_de_identificacion != EstadoDeIdentificacion.SIN_CHIP


@pytest.mark.parametrize(
    "estado",
    [
        "",
        EstadoDeIdentificacion.SIN_CHIP,
        EstadoDeIdentificacion.IMPLANTADO,
        EstadoDeIdentificacion.INSCRITO,
    ],
)
def test_la_ficha_enseña_el_estado_de_identificacion(client, estado):
    """Visible en la ficha y con todas sus letras, para poder decírselo al Tutor
    sin tener que interpretar una casilla vacía."""
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic, estado_de_identificacion=estado)

    contenido = client.get(reverse("patients:ficha", args=[paciente.pk])).content.decode()

    assert str(paciente.identificacion_a_la_vista) in contenido


# --- Qué le falta al Tutor para cumplir la Ley 21.020 ---------------------


@pytest.mark.parametrize(
    "estado", ["", EstadoDeIdentificacion.SIN_CHIP, EstadoDeIdentificacion.IMPLANTADO]
)
def test_a_un_perro_que_no_esta_inscrito_le_falta_algo(client, estado):
    paciente = PacienteFactory(especie=Especie.PERRO, estado_de_identificacion=estado)

    assert paciente.lo_que_le_falta_a_la_ley is not None


def test_a_un_perro_inscrito_no_le_falta_nada():
    paciente = PacienteFactory(
        especie=Especie.PERRO, estado_de_identificacion=EstadoDeIdentificacion.INSCRITO
    )

    assert paciente.lo_que_le_falta_a_la_ley is None


def test_a_un_reptil_sin_chip_no_le_falta_nada():
    """La Ley 21.020 obliga con perros y gatos. Reclamarle a quien trae una
    iguana que la inscriba sería darle un consejo falso desde el mostrador."""
    paciente = PacienteFactory(
        especie=Especie.REPTIL, estado_de_identificacion=EstadoDeIdentificacion.SIN_CHIP
    )

    assert paciente.lo_que_le_falta_a_la_ley is None


def test_la_ficha_de_un_perro_sin_inscribir_dice_lo_que_le_falta(client):
    usuario = recepcion(client)
    paciente = PacienteFactory(
        clinic=usuario.clinic,
        especie=Especie.PERRO,
        estado_de_identificacion=EstadoDeIdentificacion.IMPLANTADO,
    )

    contenido = client.get(reverse("patients:ficha", args=[paciente.pk])).content.decode()

    assert str(paciente.lo_que_le_falta_a_la_ley) in contenido


# --- El alta -------------------------------------------------------------


def test_el_microchip_se_puede_apuntar_al_registrar_al_paciente(client):
    """El animal llega chipeado del mostrador de al lado. Obligar a guardar y
    corregir después dejaría un rato de ficha sin el único dato que la encuentra."""
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)

    client.post(
        reverse("patients:crear", args=[tutor.pk]),
        {
            "nombre": "Rocco",
            "especie": Especie.PERRO,
            "raza": "Mestizo",
            "microchip": "900 123 456 789 012",
            "estado_de_identificacion": EstadoDeIdentificacion.INSCRITO,
        },
    )

    paciente = Paciente.de_todas_las_clinicas.get(nombre="Rocco")
    assert paciente.microchip == CHIP
    assert paciente.estado_de_identificacion == EstadoDeIdentificacion.INSCRITO

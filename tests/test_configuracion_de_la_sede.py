"""La Sede declara cuándo atiende, si atiende urgencias y a quién derivar.

Dos mitades. La de arriba pregunta a `esta_en_horario` por instantes concretos
—dentro, fuera, en el borde exacto, en una fecha de Excepción y en los dos
domingos del año en que la hora local se mueve—, porque de esa función van a
colgar la agenda (H3) y la Autorespuesta (H4). La de abajo entra por HTTP como
el admin y comprueba lo que queda guardado, quién no puede entrar, y que nada de
otra Clínica se deje ni ver ni tocar.
"""

import datetime as dt

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.tenancy.horarios import Dia, esta_en_horario
from apps.tenancy.models import ClinicaDeDerivacion, ExcepcionDeAtencion, FranjaDeAtencion
from tests.factories import (
    ClinicaDeDerivacionFactory,
    ClinicaFactory,
    ExcepcionDeAtencionFactory,
    FranjaDeAtencionFactory,
    Rol,
    SedeFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


def instante(fecha, hora, offset):
    """El instante en que en Santiago son esa fecha y esa hora.

    Se escribe con el desfase de ese día —`-04` en invierno, `-03` en verano—
    para que el test diga qué hora marcaba el reloj de la puerta, y se devuelve
    en UTC, que es como llega desde la base. Las dos cosas importan: lo que se
    declara es hora local y lo que se guarda es un instante, y traducir de una a
    otra es justamente lo que se está probando.
    """
    local = dt.datetime.combine(fecha, hora, tzinfo=dt.timezone(dt.timedelta(hours=offset)))
    return local.astimezone(dt.timezone.utc)


INVIERNO = -4
VERANO = -3

# Un martes cualquiera de junio, con la Sede abierta de 09:00 a 13:00.
MARTES = dt.date(2026, 6, 16)


@pytest.fixture
def sede():
    return SedeFactory(nombre="Providencia")


@pytest.fixture
def sede_de_mananas(sede):
    FranjaDeAtencionFactory(sede=sede, dia=Dia.MARTES, desde=dt.time(9), hasta=dt.time(13))
    return sede


@pytest.mark.parametrize(
    ("hora", "atiende"),
    [
        (dt.time(10, 30), True),
        (dt.time(14, 0), False),
        (dt.time(8, 59), False),
        # Los dos bordes. A la hora de abrir se atiende y a la de cerrar ya no:
        # es lo que permite declarar mañana y tarde sin que el mediodía caiga en
        # las dos franjas a la vez.
        (dt.time(9, 0), True),
        (dt.time(13, 0), False),
    ],
)
def test_la_sede_atiende_dentro_de_su_franja_y_no_fuera(sede_de_mananas, hora, atiende):
    assert esta_en_horario(sede_de_mananas, instante(MARTES, hora, INVIERNO)) is atiende


def test_un_dia_sin_franjas_esta_cerrado(sede_de_mananas):
    domingo = MARTES + dt.timedelta(days=5)

    assert esta_en_horario(sede_de_mananas, instante(domingo, dt.time(10, 30), INVIERNO)) is False


def test_la_tarde_es_otra_franja_del_mismo_dia(sede_de_mananas):
    FranjaDeAtencionFactory(
        sede=sede_de_mananas, dia=Dia.MARTES, desde=dt.time(15), hasta=dt.time(19)
    )

    assert esta_en_horario(sede_de_mananas, instante(MARTES, dt.time(16), INVIERNO)) is True
    assert esta_en_horario(sede_de_mananas, instante(MARTES, dt.time(14), INVIERNO)) is False


def test_una_excepcion_sin_horas_cierra_el_dia_entero(sede_de_mananas):
    ExcepcionDeAtencionFactory(sede=sede_de_mananas, fecha=MARTES, motivo="Cierre por vacaciones")

    assert esta_en_horario(sede_de_mananas, instante(MARTES, dt.time(10, 30), INVIERNO)) is False


def test_una_excepcion_con_horas_sustituye_a_las_de_la_semana(sede_de_mananas):
    """El 24 de diciembre se cierra a las 14:00: ese día vale eso y solo eso."""
    ExcepcionDeAtencionFactory(
        sede=sede_de_mananas,
        fecha=MARTES,
        motivo="Víspera",
        desde=dt.time(11),
        hasta=dt.time(14),
    )

    # A las 09:30 atendería cualquier otro martes, y este no.
    assert esta_en_horario(sede_de_mananas, instante(MARTES, dt.time(9, 30), INVIERNO)) is False
    assert esta_en_horario(sede_de_mananas, instante(MARTES, dt.time(13, 30), INVIERNO)) is True


def test_la_excepcion_solo_vale_para_su_fecha(sede_de_mananas):
    ExcepcionDeAtencionFactory(sede=sede_de_mananas, fecha=MARTES)

    siguiente = MARTES + dt.timedelta(days=7)
    assert esta_en_horario(sede_de_mananas, instante(siguiente, dt.time(10, 30), INVIERNO)) is True


def test_la_excepcion_de_otra_sede_no_cierra_esta(sede_de_mananas):
    otra = SedeFactory(clinic=sede_de_mananas.clinic, nombre="Ñuñoa")
    ExcepcionDeAtencionFactory(sede=otra, fecha=MARTES)

    assert esta_en_horario(sede_de_mananas, instante(MARTES, dt.time(10, 30), INVIERNO)) is True


# Los dos domingos en que Chile mueve el reloj: el 6 de septiembre de 2026
# entra el horario de verano (−04 → −03) y el 5 de abril sale (−03 → −04). El
# horario se declara en hora local, así que «de 09:00 a 13:00 el domingo» tiene
# que seguir significando lo mismo el domingo del cambio que el anterior — y
# eso solo se cumple si el instante se traduce a Santiago en vez de darse por
# supuesto un desfase.
@pytest.mark.parametrize(
    ("fecha", "offset"),
    [
        (dt.date(2026, 9, 6), VERANO),
        (dt.date(2026, 8, 30), INVIERNO),
        (dt.date(2026, 4, 5), INVIERNO),
        (dt.date(2026, 3, 29), VERANO),
    ],
)
def test_el_horario_se_respeta_en_las_semanas_del_cambio_de_hora(sede, fecha, offset):
    FranjaDeAtencionFactory(sede=sede, dia=Dia.DOMINGO, desde=dt.time(9), hasta=dt.time(13))

    assert esta_en_horario(sede, instante(fecha, dt.time(9, 0), offset)) is True
    assert esta_en_horario(sede, instante(fecha, dt.time(8, 59), offset)) is False


def test_el_mismo_instante_utc_cae_dentro_o_fuera_segun_el_cambio_de_hora(sede):
    """Las 12:00 UTC son las 09:00 en Santiago en verano y las 08:00 en invierno.

    Es la comprobación que se cae si alguien compara la hora guardada sin
    traducirla: las dos darían lo mismo.
    """
    FranjaDeAtencionFactory(sede=sede, dia=Dia.DOMINGO, desde=dt.time(9), hasta=dt.time(13))
    mediodia_utc = dt.time(12, tzinfo=dt.timezone.utc)

    en_verano = dt.datetime.combine(dt.date(2026, 9, 6), mediodia_utc)
    en_invierno = dt.datetime.combine(dt.date(2026, 8, 30), mediodia_utc)

    assert esta_en_horario(sede, en_verano) is True
    assert esta_en_horario(sede, en_invierno) is False


# Lo que el formulario ya rechaza con palabras, la base de datos lo rechaza
# igual: al horario también se escribe desde un comando o desde el importador,
# y ahí no hay formulario que se acuerde de nada.


def test_la_base_no_acepta_una_franja_que_termina_antes_de_empezar(sede):
    with pytest.raises(IntegrityError), transaction.atomic():
        FranjaDeAtencionFactory(sede=sede, desde=dt.time(13), hasta=dt.time(9))


def test_la_base_no_acepta_media_excepcion(sede):
    with pytest.raises(IntegrityError), transaction.atomic():
        ExcepcionDeAtencionFactory(sede=sede, desde=dt.time(9), hasta=None)


def test_la_base_no_acepta_un_telefono_de_urgencias_sin_urgencias(sede):
    with pytest.raises(IntegrityError), transaction.atomic():
        SedeFactory(
            clinic=sede.clinic,
            nombre="Ñuñoa",
            atiende_urgencias=False,
            telefono_de_urgencias="+56987654321",
        )


# --------------------------------------------------------------------------
# Lo que el admin hace por HTTP.
# --------------------------------------------------------------------------


@pytest.fixture
def clinica():
    return ClinicaFactory(nombre="Clínica Los Andes")


@pytest.fixture
def sede_de_la_clinica(clinica):
    return SedeFactory(clinic=clinica, nombre="Providencia")


@pytest.fixture
def admin(client, clinica, sede_de_la_clinica):
    usuario = UsuarioFactory(clinic=clinica, sedes=[sede_de_la_clinica], rol=Rol.ADMIN)
    client.force_login(usuario)
    return usuario


def test_el_admin_ve_sus_sedes_y_el_horario_declarado(client, admin, sede_de_la_clinica):
    FranjaDeAtencionFactory(
        sede=sede_de_la_clinica, dia=Dia.MARTES, desde=dt.time(9), hasta=dt.time(13)
    )
    ajena = SedeFactory(nombre="Sede de otra Clínica")

    configuracion = client.get(reverse("tenancy:configuracion")).content.decode()
    horario = client.get(
        reverse("tenancy:horario_de_la_sede", args=[sede_de_la_clinica.pk])
    ).content.decode()

    assert sede_de_la_clinica.nombre in configuracion
    assert ajena.nombre not in configuracion
    assert "09:00" in horario and "13:00" in horario


def test_el_admin_declara_una_franja_del_horario(client, admin, sede_de_la_clinica):
    respuesta = client.post(
        reverse("tenancy:crear_franja", args=[sede_de_la_clinica.pk]),
        {"dia": Dia.MARTES, "desde": "09:00", "hasta": "13:00"},
    )

    franja = FranjaDeAtencion.de_todas_las_clinicas.get()
    assert respuesta.status_code == 302
    assert (franja.sede, franja.clinic) == (sede_de_la_clinica, sede_de_la_clinica.clinic)
    assert (franja.desde, franja.hasta) == (dt.time(9), dt.time(13))


def test_una_franja_que_termina_antes_de_empezar_no_se_guarda(client, admin, sede_de_la_clinica):
    respuesta = client.post(
        reverse("tenancy:crear_franja", args=[sede_de_la_clinica.pk]),
        {"dia": Dia.MARTES, "desde": "13:00", "hasta": "09:00"},
    )

    assert respuesta.status_code == 200
    assert not FranjaDeAtencion.de_todas_las_clinicas.exists()


def test_una_franja_que_se_pisa_con_otra_no_se_guarda(client, admin, sede_de_la_clinica):
    FranjaDeAtencionFactory(
        sede=sede_de_la_clinica, dia=Dia.MARTES, desde=dt.time(9), hasta=dt.time(13)
    )

    respuesta = client.post(
        reverse("tenancy:crear_franja", args=[sede_de_la_clinica.pk]),
        {"dia": Dia.MARTES, "desde": "12:00", "hasta": "18:00"},
    )

    assert respuesta.status_code == 200
    assert FranjaDeAtencion.de_todas_las_clinicas.count() == 1


def test_la_tarde_puede_empezar_a_la_hora_en_que_cierra_la_manana(
    client, admin, sede_de_la_clinica
):
    """Dos franjas contiguas no se pisan: las 13:00 caen en una sola."""
    FranjaDeAtencionFactory(
        sede=sede_de_la_clinica, dia=Dia.MARTES, desde=dt.time(9), hasta=dt.time(13)
    )

    client.post(
        reverse("tenancy:crear_franja", args=[sede_de_la_clinica.pk]),
        {"dia": Dia.MARTES, "desde": "13:00", "hasta": "19:00"},
    )

    assert FranjaDeAtencion.de_todas_las_clinicas.count() == 2


def test_el_admin_quita_una_franja(client, admin, sede_de_la_clinica):
    franja = FranjaDeAtencionFactory(sede=sede_de_la_clinica)

    client.post(reverse("tenancy:quitar_franja", args=[sede_de_la_clinica.pk, franja.pk]))

    assert not FranjaDeAtencion.de_todas_las_clinicas.exists()


def test_el_admin_cierra_una_fecha_y_la_sede_deja_de_atenderla(
    client, admin, sede_de_la_clinica
):
    """De la pantalla a la respuesta: lo declarado es lo que la función contesta."""
    FranjaDeAtencionFactory(
        sede=sede_de_la_clinica, dia=Dia.MARTES, desde=dt.time(9), hasta=dt.time(13)
    )

    client.post(
        reverse("tenancy:crear_excepcion", args=[sede_de_la_clinica.pk]),
        {"fecha": MARTES.isoformat(), "motivo": "Cierre por vacaciones"},
    )

    assert esta_en_horario(sede_de_la_clinica, instante(MARTES, dt.time(10), INVIERNO)) is False


def test_una_excepcion_a_medias_no_se_guarda(client, admin, sede_de_la_clinica):
    """«Abre a las 09:00» sin decir hasta cuándo no es ni cerrado ni un horario."""
    respuesta = client.post(
        reverse("tenancy:crear_excepcion", args=[sede_de_la_clinica.pk]),
        {"fecha": MARTES.isoformat(), "motivo": "Víspera", "desde": "09:00"},
    )

    assert respuesta.status_code == 200
    assert not ExcepcionDeAtencion.de_todas_las_clinicas.exists()


def test_el_admin_declara_que_la_sede_atiende_urgencias(client, admin, sede_de_la_clinica):
    client.post(
        reverse("tenancy:guardar_urgencias", args=[sede_de_la_clinica.pk]),
        {"atiende_urgencias": "on", "telefono_de_urgencias": "9 8765 4321"},
    )

    sede_de_la_clinica.refresh_from_db()
    assert sede_de_la_clinica.atiende_urgencias is True
    # El teléfono se guarda en E.164 pase por donde pase, como el del Tutor.
    assert sede_de_la_clinica.telefono_de_urgencias == "+56987654321"


def test_un_telefono_de_urgencias_sin_urgencias_no_se_guarda(client, admin, sede_de_la_clinica):
    respuesta = client.post(
        reverse("tenancy:guardar_urgencias", args=[sede_de_la_clinica.pk]),
        {"telefono_de_urgencias": "9 8765 4321"},
    )

    sede_de_la_clinica.refresh_from_db()
    assert respuesta.status_code == 200
    assert sede_de_la_clinica.telefono_de_urgencias == ""


def test_recepcion_no_entra_en_la_configuracion(client, clinica, sede_de_la_clinica):
    client.force_login(UsuarioFactory(clinic=clinica, sedes=[sede_de_la_clinica]))

    assert client.get(reverse("tenancy:configuracion")).status_code == 403


def test_no_se_declara_el_horario_de_una_sede_de_otra_clinica(client, admin):
    ajena = SedeFactory(nombre="Sede de otra Clínica")

    respuesta = client.post(
        reverse("tenancy:crear_franja", args=[ajena.pk]),
        {"dia": Dia.MARTES, "desde": "09:00", "hasta": "13:00"},
    )

    assert respuesta.status_code == 404
    assert not FranjaDeAtencion.de_todas_las_clinicas.exists()


# --------------------------------------------------------------------------
# Clínicas de derivación.
# --------------------------------------------------------------------------


def test_el_admin_anade_una_clinica_de_derivacion(client, admin, clinica):
    respuesta = client.post(
        reverse("tenancy:crear_derivacion"),
        {
            "nombre": "Urgencias Veterinarias Vitacura",
            "telefono": "2 2345 6789",
            "direccion": "Av. Kennedy 5000, Santiago",
        },
    )

    derivacion = ClinicaDeDerivacion.de_todas_las_clinicas.get()
    assert respuesta.status_code == 302
    assert derivacion.clinic == clinica
    assert derivacion.telefono == "+56223456789"


def test_no_se_anade_dos_veces_la_misma_clinica_de_derivacion(client, admin, clinica):
    ClinicaDeDerivacionFactory(clinic=clinica, nombre="Urgencias Vitacura")

    respuesta = client.post(
        reverse("tenancy:crear_derivacion"),
        {"nombre": "urgencias vitacura", "telefono": "", "direccion": ""},
    )

    assert respuesta.status_code == 200
    assert ClinicaDeDerivacion.de_todas_las_clinicas.count() == 1


def test_el_admin_quita_una_clinica_de_derivacion(client, admin, clinica):
    derivacion = ClinicaDeDerivacionFactory(clinic=clinica)

    client.post(reverse("tenancy:quitar_derivacion", args=[derivacion.pk]))

    assert not ClinicaDeDerivacion.de_todas_las_clinicas.exists()


def test_la_lista_no_ensena_las_clinicas_de_derivacion_de_otra_clinica(client, admin, clinica):
    propia = ClinicaDeDerivacionFactory(clinic=clinica, nombre="Urgencias Vitacura")
    ajena = ClinicaDeDerivacionFactory(nombre="Urgencias de otra Clínica")

    contenido = client.get(reverse("tenancy:derivaciones")).content.decode()

    assert propia.nombre in contenido
    assert ajena.nombre not in contenido


def test_no_se_edita_una_clinica_de_derivacion_de_otra_clinica(client, admin):
    ajena = ClinicaDeDerivacionFactory(nombre="Urgencias de otra Clínica")

    respuesta = client.get(reverse("tenancy:editar_derivacion", args=[ajena.pk]))

    assert respuesta.status_code == 404

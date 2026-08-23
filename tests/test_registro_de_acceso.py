"""Queda constancia de quién vio o modificó datos personales, y cuándo (ADR-0004).

Tres planos: lo que se anota al servir una página, lo que la base de datos
impide hacerle a esa anotación después, y lo que el admin de la Clínica puede
consultar. El primero entra por HTTP a propósito: una lectura no dispara
señales de modelo, así que si la vista no lo anota no lo anota nadie.
"""

import datetime as dt

import pytest
from django.db import DatabaseError, connection, transaction
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import Accion, RegistroDeAcceso
from apps.audit.registro import anotar
from tests.factories import (
    ClinicaFactory,
    RegistroDeAccesoFactory,
    TutorFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db

# 20 de junio de 2026, 23:30 en Santiago: en UTC ya es el día 21. Un rango de
# fechas que se calculase en UTC dejaría fuera esta anotación.
CASI_MEDIANOCHE_EN_SANTIAGO = dt.datetime(2026, 6, 21, 3, 30, tzinfo=dt.timezone.utc)


def admin_de(clinica, client):
    usuario = UsuarioFactory(clinic=clinica, rol="admin")
    client.force_login(usuario)
    return usuario


# --- Lo que se anota al servir una página ---------------------------------


def test_abrir_la_ficha_de_un_tutor_deja_constancia(client):
    usuario = UsuarioFactory()
    tutor = TutorFactory(clinic=usuario.clinic)
    client.force_login(usuario)
    antes = timezone.now()

    client.get(reverse("tutors:ficha", args=[tutor.pk]))

    anotacion = RegistroDeAcceso.de_todas_las_clinicas.get()
    assert anotacion.usuario == usuario
    assert anotacion.clinic == usuario.clinic
    assert anotacion.tipo_de_objeto == "tutors.Tutor"
    assert anotacion.identificador == str(tutor.pk)
    assert anotacion.accion == Accion.LECTURA
    assert antes <= anotacion.momento <= timezone.now()


def test_el_listado_de_tutores_deja_constancia_del_conjunto(client):
    usuario = UsuarioFactory()
    TutorFactory(clinic=usuario.clinic)
    client.force_login(usuario)

    client.get(reverse("tutors:lista"))

    anotacion = RegistroDeAcceso.de_todas_las_clinicas.get()
    assert anotacion.tipo_de_objeto == "tutors.Tutor"
    # Sin identificador: lo servido fue el conjunto, no un Tutor concreto.
    assert anotacion.identificador == ""


def test_pedir_un_tutor_de_otra_clinica_no_deja_constancia(client):
    """Un 404 no llegó a servir ningún dato; anotarlo ensuciaría la evidencia."""
    usuario = UsuarioFactory()
    ajeno = TutorFactory()
    client.force_login(usuario)

    respuesta = client.get(reverse("tutors:ficha", args=[ajeno.pk]))

    assert respuesta.status_code == 404
    assert not RegistroDeAcceso.de_todas_las_clinicas.exists()


def test_cada_visita_a_la_ficha_deja_su_propia_anotacion(client):
    usuario = UsuarioFactory()
    tutor = TutorFactory(clinic=usuario.clinic)
    client.force_login(usuario)

    client.get(reverse("tutors:ficha", args=[tutor.pk]))
    client.get(reverse("tutors:ficha", args=[tutor.pk]))

    assert RegistroDeAcceso.de_todas_las_clinicas.count() == 2


def test_anotar_una_modificacion_guarda_el_objeto_que_se_toco():
    """Lo que no sale de la URL — un formulario que acaba de guardar — se anota
    pasando el objeto. Es por donde entrarán las vistas de edición del ticket 05."""
    usuario = UsuarioFactory()
    tutor = TutorFactory(clinic=usuario.clinic)

    anotar(usuario, Accion.MODIFICACION, tutor)

    anotacion = RegistroDeAcceso.de_todas_las_clinicas.get()
    assert anotacion.accion == Accion.MODIFICACION
    assert anotacion.tipo_de_objeto == "tutors.Tutor"
    assert anotacion.identificador == str(tutor.pk)


def test_se_anota_aunque_no_haya_Clinica_activa():
    """La Clínica de la anotación sale del Usuario. Una tarea o un comando, sin
    petición HTTP y por tanto sin Clínica activa, tiene que poder anotar igual."""
    usuario = UsuarioFactory()
    tutor = TutorFactory(clinic=usuario.clinic)

    anotacion = anotar(usuario, Accion.LECTURA, tutor)

    assert anotacion.clinic == usuario.clinic


# --- Lo que la base de datos impide ---------------------------------------


def test_una_anotacion_no_se_puede_modificar():
    anotacion = RegistroDeAccesoFactory()

    with pytest.raises(DatabaseError), transaction.atomic():
        RegistroDeAcceso.de_todas_las_clinicas.filter(pk=anotacion.pk).update(
            accion=Accion.MODIFICACION
        )

    assert RegistroDeAcceso.de_todas_las_clinicas.get(pk=anotacion.pk).accion == anotacion.accion


def test_una_anotacion_no_se_puede_borrar():
    anotacion = RegistroDeAccesoFactory()

    with pytest.raises(DatabaseError), transaction.atomic():
        RegistroDeAcceso.de_todas_las_clinicas.filter(pk=anotacion.pk).delete()

    assert RegistroDeAcceso.de_todas_las_clinicas.filter(pk=anotacion.pk).exists()


def test_la_tabla_no_concede_a_nadie_permiso_para_modificarla():
    """El disparador de arriba es la defensa que ningún rol se salta; esta es la
    otra mitad, la que pide el ADR: los permisos de la tabla.

    Hace falta mirar el ACL y no intentar la operación, porque el rol de
    desarrollo es superusuario de Postgres y se salta los permisos — en un
    despliegue, donde no lo es, esto es lo único que hay entre él y la tabla.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "select privilege_type from information_schema.table_privileges "
            "where table_name = 'audit_registrodeacceso'"
        )
        concedidos = {fila[0] for fila in cursor.fetchall()}

    assert "INSERT" in concedidos, "sin INSERT no se podría anotar nada"
    assert not concedidos & {"UPDATE", "DELETE", "TRUNCATE"}


def test_borrar_al_usuario_no_borra_su_rastro():
    """La anotación conserva a su autor: el Usuario no se puede borrar debajo."""
    anotacion = RegistroDeAccesoFactory()

    with pytest.raises(DatabaseError), transaction.atomic():
        anotacion.usuario.delete()

    assert RegistroDeAcceso.de_todas_las_clinicas.filter(pk=anotacion.pk).exists()


# --- Lo que el admin consulta ---------------------------------------------

# Dos anotaciones que se distinguen de un vistazo dentro de la página entera.
# Llevan prefijo a propósito: buscar «111» a secas también encontraría el número
# de la Clínica o de la Sede que fabrica el escenario, y el test pasaría o
# fallaría según cuántos tests se hubieran ejecutado antes.
UNO = "pk-111"
OTRO = "pk-999"


def test_el_registro_esta_aislado_por_clinica(client):
    clinica = ClinicaFactory()
    propia = RegistroDeAccesoFactory(usuario__clinic=clinica, identificador=UNO)
    RegistroDeAccesoFactory(identificador=OTRO)
    admin_de(clinica, client)

    contenido = client.get(reverse("audit:registro")).content.decode()

    assert propia.usuario.email in contenido
    assert OTRO not in contenido


def test_recepcion_no_puede_consultar_el_registro(client):
    usuario = UsuarioFactory(rol="recepcion")
    client.force_login(usuario)

    assert client.get(reverse("audit:registro")).status_code == 403


def test_consultar_el_registro_no_se_anota_a_si_mismo(client):
    """El Registro no contiene datos personales de Tutor: anotarse a sí mismo
    solo lo llenaría de ruido."""
    clinica = ClinicaFactory()
    admin_de(clinica, client)

    client.get(reverse("audit:registro"))

    assert not RegistroDeAcceso.de_todas_las_clinicas.exists()


def test_el_admin_filtra_por_usuario(client):
    clinica = ClinicaFactory()
    veterinaria = UsuarioFactory(clinic=clinica, email="vet@clinica.example")
    RegistroDeAccesoFactory(usuario=veterinaria, identificador=UNO)
    RegistroDeAccesoFactory(usuario__clinic=clinica, identificador=OTRO)
    admin_de(clinica, client)

    contenido = client.get(reverse("audit:registro"), {"usuario": veterinaria.pk}).content.decode()

    assert UNO in contenido
    assert OTRO not in contenido


def test_el_admin_filtra_por_objeto(client):
    clinica = ClinicaFactory()
    RegistroDeAccesoFactory(
        usuario__clinic=clinica, tipo_de_objeto="tutors.Tutor", identificador=UNO
    )
    RegistroDeAccesoFactory(
        usuario__clinic=clinica, tipo_de_objeto="patients.Paciente", identificador=OTRO
    )
    admin_de(clinica, client)

    contenido = client.get(
        reverse("audit:registro"), {"tipo_de_objeto": "tutors.Tutor"}
    ).content.decode()

    assert UNO in contenido
    assert OTRO not in contenido


def test_el_admin_filtra_por_un_objeto_concreto(client):
    clinica = ClinicaFactory()
    RegistroDeAccesoFactory(usuario__clinic=clinica, identificador=UNO)
    RegistroDeAccesoFactory(usuario__clinic=clinica, identificador=OTRO)
    admin_de(clinica, client)

    contenido = client.get(reverse("audit:registro"), {"identificador": UNO}).content.decode()

    assert UNO in contenido
    assert OTRO not in contenido


def test_el_admin_filtra_por_rango_de_fechas(client):
    clinica = ClinicaFactory()
    RegistroDeAccesoFactory(
        usuario__clinic=clinica,
        identificador=UNO,
        momento=CASI_MEDIANOCHE_EN_SANTIAGO,
    )
    RegistroDeAccesoFactory(
        usuario__clinic=clinica,
        identificador=OTRO,
        momento=CASI_MEDIANOCHE_EN_SANTIAGO + dt.timedelta(days=5),
    )
    admin_de(clinica, client)

    contenido = client.get(
        reverse("audit:registro"), {"desde": "2026-06-20", "hasta": "2026-06-20"}
    ).content.decode()

    # El rango son días de Santiago: las 23:30 del 20 en Chile entran, aunque
    # en UTC ya sea el 21.
    assert UNO in contenido
    assert OTRO not in contenido


def test_el_rango_cuadra_el_dia_en_que_cambia_la_hora_de_verano(client):
    """El 6 de septiembre de 2026 la medianoche no existe en Chile: el reloj
    salta de las 24:00 del sábado a la 01:00 del domingo. El día tiene que
    empezar y terminar donde le toca igualmente."""
    clinica = ClinicaFactory()
    # 23:00 del sábado 5 en Santiago (aún UTC-4) → 03:00 UTC del domingo.
    RegistroDeAccesoFactory(
        usuario__clinic=clinica,
        identificador=OTRO,
        momento=dt.datetime(2026, 9, 6, 3, 0, tzinfo=dt.timezone.utc),
    )
    # 10:00 del domingo 6 en Santiago (ya UTC-3) → 13:00 UTC.
    RegistroDeAccesoFactory(
        usuario__clinic=clinica,
        identificador=UNO,
        momento=dt.datetime(2026, 9, 6, 13, 0, tzinfo=dt.timezone.utc),
    )
    admin_de(clinica, client)

    contenido = client.get(
        reverse("audit:registro"), {"desde": "2026-09-06", "hasta": "2026-09-06"}
    ).content.decode()

    assert UNO in contenido
    assert OTRO not in contenido


def test_un_filtro_que_no_se_entiende_no_devuelve_nada(client):
    """Fallar abierto sería entregar el Registro entero a quien pidió una
    búsqueda concreta."""
    clinica = ClinicaFactory()
    RegistroDeAccesoFactory(usuario__clinic=clinica, identificador=UNO)
    admin_de(clinica, client)

    respuesta = client.get(reverse("audit:registro"), {"desde": "el martes pasado"})

    assert respuesta.status_code == 200
    assert UNO not in respuesta.content.decode()


def test_un_rango_de_fechas_al_reves_no_devuelve_nada_ni_revienta(client):
    clinica = ClinicaFactory()
    RegistroDeAccesoFactory(usuario__clinic=clinica, identificador=UNO)
    admin_de(clinica, client)

    respuesta = client.get(
        reverse("audit:registro"), {"desde": "2026-06-25", "hasta": "2026-06-20"}
    )

    assert respuesta.status_code == 200
    assert UNO not in respuesta.content.decode()

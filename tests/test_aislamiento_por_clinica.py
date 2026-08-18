"""Ningún Usuario ve datos de otra Clínica (ADR-0003).

Dos planos: el manager, que es donde vive la garantía, y la petición HTTP, que
es donde se rompería si la garantía fallase.
"""

import pytest
from django.urls import reverse

from apps.tenancy.aislamiento import activar_clinica, clinica_activa
from apps.tutors.models import Tutor
from tests.factories import ClinicaFactory, TutorFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


def test_el_manager_por_defecto_solo_ve_la_clinica_activa():
    propia = ClinicaFactory()
    TutorFactory(clinic=propia, nombre="Camila Rojas")
    TutorFactory(nombre="Tutor de otra Clínica")

    with activar_clinica(propia):
        assert [t.nombre for t in Tutor.objects.all()] == ["Camila Rojas"]


def test_sin_clinica_activa_el_manager_por_defecto_no_devuelve_nada():
    """Un olvido deja la página vacía; nunca enseña la Clínica de al lado."""
    TutorFactory()

    assert not Tutor.objects.exists()


def test_el_manager_sin_filtro_existe_y_hay_que_pedirlo_por_su_nombre():
    TutorFactory()
    TutorFactory()

    assert Tutor.de_todas_las_clinicas.count() == 2


def test_activar_clinica_deja_el_contexto_como_estaba():
    clinica = ClinicaFactory()

    with pytest.raises(ZeroDivisionError):
        with activar_clinica(clinica):
            1 / 0

    assert clinica_activa() is None


def test_el_middleware_activa_la_clinica_del_usuario_autenticado(client):
    usuario = UsuarioFactory()
    client.force_login(usuario)

    respuesta = client.get(reverse("tenancy:inicio"))

    assert respuesta.wsgi_request.clinica == usuario.clinic


def test_el_listado_no_muestra_tutores_de_otra_clinica(client):
    usuario = UsuarioFactory()
    TutorFactory(clinic=usuario.clinic, nombre="Camila Rojas")
    TutorFactory(nombre="Ignacio Fuentes")
    client.force_login(usuario)

    contenido = client.get(reverse("tutors:lista")).content.decode()

    assert "Camila Rojas" in contenido
    assert "Ignacio Fuentes" not in contenido


def test_la_busqueda_no_encuentra_tutores_de_otra_clinica(client):
    usuario = UsuarioFactory()
    ajeno = TutorFactory(nombre="Ignacio Fuentes")
    client.force_login(usuario)

    contenido = client.get(reverse("tutors:lista"), {"q": "Fuentes"}).content.decode()

    assert "Ignacio Fuentes" not in contenido
    assert reverse("tutors:ficha", args=[ajeno.pk]) not in contenido


def test_pedir_por_identificador_un_tutor_de_otra_clinica_da_404(client):
    usuario = UsuarioFactory()
    ajeno = TutorFactory(nombre="Ignacio Fuentes")
    client.force_login(usuario)

    respuesta = client.get(reverse("tutors:ficha", args=[ajeno.pk]))

    # 404 y no 403: un 403 confirmaría que ese Tutor existe en alguna Clínica.
    assert respuesta.status_code == 404
    assert "Ignacio Fuentes" not in respuesta.content.decode()


def test_la_ficha_de_un_tutor_propio_se_ve(client):
    usuario = UsuarioFactory()
    propio = TutorFactory(clinic=usuario.clinic, nombre="Camila Rojas")
    client.force_login(usuario)

    respuesta = client.get(reverse("tutors:ficha", args=[propio.pk]))

    assert respuesta.status_code == 200
    assert "Camila Rojas" in respuesta.content.decode()


def test_la_clinica_activa_no_sobrevive_a_la_peticion(client):
    usuario = UsuarioFactory()
    client.force_login(usuario)

    client.get(reverse("tenancy:inicio"))

    assert clinica_activa() is None

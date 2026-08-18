"""Tras entrar, el Usuario ve su Clínica y su Sede actual, y puede cambiar de Sede."""

import pytest
from django.urls import reverse

from tests.factories import ClinicaFactory, SedeFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


def test_el_inicio_muestra_el_nombre_de_la_clinica_y_de_la_sede(client):
    clinica = ClinicaFactory(nombre="Clínica Los Andes")
    sede = SedeFactory(clinic=clinica, nombre="Ñuñoa")
    usuario = UsuarioFactory(clinic=clinica, sedes=[sede])
    client.force_login(usuario)

    contenido = client.get(reverse("tenancy:inicio")).content.decode()

    assert "Clínica Los Andes" in contenido
    assert "Ñuñoa" in contenido


def test_un_usuario_de_una_sola_sede_no_ve_selector_de_sede(client):
    usuario = UsuarioFactory()
    client.force_login(usuario)

    contenido = client.get(reverse("tenancy:inicio")).content.decode()

    assert reverse("tenancy:cambiar_sede") not in contenido


def test_un_usuario_de_varias_sedes_cambia_de_sede(client):
    clinica = ClinicaFactory()
    providencia = SedeFactory(clinic=clinica, nombre="Providencia")
    maipu = SedeFactory(clinic=clinica, nombre="Maipú")
    usuario = UsuarioFactory(clinic=clinica, sedes=[providencia, maipu])
    client.force_login(usuario)

    client.post(reverse("tenancy:cambiar_sede"), {"sede": maipu.pk})
    contenido = client.get(reverse("tenancy:inicio")).content.decode()

    assert client.session["sede_actual"] == maipu.pk
    assert "Maipú" in contenido


def test_un_usuario_no_puede_cambiarse_a_una_sede_que_no_es_suya(client):
    clinica = ClinicaFactory()
    propia = SedeFactory(clinic=clinica, nombre="Providencia")
    ajena = SedeFactory(nombre="Sede de otra Clínica")
    usuario = UsuarioFactory(clinic=clinica, sedes=[propia])
    client.force_login(usuario)

    respuesta = client.post(reverse("tenancy:cambiar_sede"), {"sede": ajena.pk})

    assert respuesta.status_code == 404
    assert client.session.get("sede_actual") != ajena.pk

"""Comando de gestión para dar de alta una Clínica con su primera Sede y su primer admin."""

import pytest
from django.core.management import CommandError, call_command
from django.urls import reverse

from apps.tenancy.models import Clinica, Rol, Usuario

pytestmark = pytest.mark.django_db

CONTRASENA = "primera-consulta-2026"


def _dar_de_alta(**cambios):
    argumentos = {
        "clinica": "Clínica Los Andes",
        "sede": "Providencia",
        "email": "admin@losandes.example",
        "nombre": "Camila",
        "apellidos": "Rojas",
        "contrasena": CONTRASENA,
    }
    argumentos.update(cambios)
    call_command("crear_clinica", **argumentos)


def test_el_comando_crea_clinica_sede_y_admin():
    _dar_de_alta()

    clinica = Clinica.objects.get(nombre="Clínica Los Andes")
    admin = Usuario.objects.get(email="admin@losandes.example")
    assert [sede.nombre for sede in clinica.sedes.all()] == ["Providencia"]
    assert admin.clinic == clinica
    assert admin.rol == Rol.ADMIN
    assert list(admin.sedes.all()) == list(clinica.sedes.all())


def test_el_admin_dado_de_alta_entra_con_su_contrasena(client):
    """Su contraseña vale, pero es admin: antes de tener sesión configura su
    segundo factor (ver `tests/test_segundo_factor.py`)."""
    _dar_de_alta()

    respuesta = client.post(
        reverse("account_login"),
        {"login": "admin@losandes.example", "password": CONTRASENA},
    )

    assert respuesta["Location"] == reverse("tenancy:alta_de_segundo_factor")


def test_el_comando_no_pisa_una_clinica_ya_dada_de_alta():
    _dar_de_alta()

    with pytest.raises(CommandError):
        _dar_de_alta()

    assert Clinica.objects.count() == 1

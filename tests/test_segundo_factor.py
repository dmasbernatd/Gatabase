"""El segundo factor es obligatorio para el admin, y solo para él.

El admin es quien puede exportar la base entera de una Clínica; el veterinario y
recepción trabajan en el mostrador, con Tutores esperando delante. Por eso la
misma decisión — pedir un código de la aplicación del teléfono — es prudencia en
un caso y fricción inaceptable en el otro.
"""

import pytest
from allauth.mfa.models import Authenticator
from allauth.mfa.totp.internal.auth import (
    TOTP,
    format_hotp_value,
    generate_totp_secret,
    hotp_value,
    yield_hotp_counters_from_time,
)
from django.core.management import CommandError, call_command
from django.urls import reverse

from apps.tenancy.models import Rol
from tests.factories import CONTRASENA_DE_PRUEBA, UsuarioFactory

pytestmark = pytest.mark.django_db


def _entrar(client, usuario):
    return client.post(
        reverse("account_login"),
        {"login": usuario.email, "password": CONTRASENA_DE_PRUEBA},
    )


def _codigo(secreto):
    """El código que mostraría ahora mismo la aplicación del teléfono."""
    return format_hotp_value(hotp_value(secreto, next(yield_hotp_counters_from_time())))


def _con_segundo_factor(usuario):
    secreto = generate_totp_secret()
    TOTP.activate(usuario, secreto)
    return secreto


def test_un_admin_sin_segundo_factor_no_completa_el_login(client):
    admin = UsuarioFactory(rol=Rol.ADMIN)

    respuesta = _entrar(client, admin)

    assert respuesta["Location"] == reverse("tenancy:alta_de_segundo_factor")
    assert "_auth_user_id" not in client.session


def test_un_admin_a_medio_entrar_no_ve_ninguna_pagina_interna(client):
    admin = UsuarioFactory(rol=Rol.ADMIN)
    _entrar(client, admin)

    respuesta = client.get(reverse("tenancy:usuarios"))

    assert respuesta["Location"].startswith(reverse("account_login"))


def test_el_admin_da_de_alta_su_segundo_factor_y_entra(client):
    admin = UsuarioFactory(rol=Rol.ADMIN)
    _entrar(client, admin)
    client.get(reverse("tenancy:alta_de_segundo_factor"))
    secreto = client.session["mfa.totp.secret"]

    respuesta = client.post(
        reverse("tenancy:alta_de_segundo_factor"), {"code": _codigo(secreto)}
    )

    assert respuesta.status_code == 302
    assert client.session.get("_auth_user_id") == str(admin.pk)
    assert Authenticator.objects.filter(user=admin, type=Authenticator.Type.TOTP).exists()


def test_la_pagina_de_alta_muestra_el_codigo_que_hay_que_escanear(client):
    admin = UsuarioFactory(rol=Rol.ADMIN)
    _entrar(client, admin)

    contenido = client.get(reverse("tenancy:alta_de_segundo_factor")).content.decode()

    assert client.session["mfa.totp.secret"] in contenido
    assert "data:image/svg+xml;base64," in contenido


def test_un_codigo_equivocado_no_da_de_alta_el_segundo_factor(client):
    admin = UsuarioFactory(rol=Rol.ADMIN)
    _entrar(client, admin)
    client.get(reverse("tenancy:alta_de_segundo_factor"))

    respuesta = client.post(reverse("tenancy:alta_de_segundo_factor"), {"code": "000000"})

    assert respuesta.status_code == 200
    assert "_auth_user_id" not in client.session
    assert not Authenticator.objects.filter(user=admin).exists()


def test_la_pagina_de_alta_no_se_abre_sin_un_login_a_medias(client):
    respuesta = client.get(reverse("tenancy:alta_de_segundo_factor"))

    assert respuesta.status_code == 302
    assert respuesta["Location"].startswith(reverse("account_login"))


def test_un_admin_con_segundo_factor_teclea_el_codigo_para_entrar(client):
    admin = UsuarioFactory(rol=Rol.ADMIN)
    secreto = _con_segundo_factor(admin)

    respuesta = _entrar(client, admin)

    assert respuesta["Location"] == reverse("mfa_authenticate")
    assert "_auth_user_id" not in client.session

    client.post(reverse("mfa_authenticate"), {"code": _codigo(secreto)})

    assert client.session.get("_auth_user_id") == str(admin.pk)


def test_un_codigo_equivocado_no_completa_el_login_del_admin(client):
    admin = UsuarioFactory(rol=Rol.ADMIN)
    _con_segundo_factor(admin)
    _entrar(client, admin)

    respuesta = client.post(reverse("mfa_authenticate"), {"code": "000000"})

    assert respuesta.status_code == 200
    assert "_auth_user_id" not in client.session


@pytest.mark.parametrize("rol", [Rol.VETERINARIO, Rol.RECEPCION])
def test_al_mostrador_no_se_le_exige_segundo_factor(client, rol):
    usuario = UsuarioFactory(rol=rol)

    respuesta = _entrar(client, usuario)

    assert respuesta["Location"] == reverse("tenancy:inicio")
    assert client.session.get("_auth_user_id") == str(usuario.pk)


def test_a_quien_no_se_le_exige_pero_lo_tiene_igual_se_le_pide(client):
    """No exigirlo no es prohibirlo: un veterinario que lo dio de alta sigue
    entrando con él."""
    veterinario = UsuarioFactory(rol=Rol.VETERINARIO)
    _con_segundo_factor(veterinario)

    respuesta = _entrar(client, veterinario)

    assert respuesta["Location"] == reverse("mfa_authenticate")


def test_el_comando_retira_el_segundo_factor_de_un_admin_que_perdio_el_telefono(client):
    admin = UsuarioFactory(rol=Rol.ADMIN)
    _con_segundo_factor(admin)

    call_command("restablecer_segundo_factor", admin.email)

    assert not Authenticator.objects.filter(user=admin).exists()
    assert _entrar(client, admin)["Location"] == reverse("tenancy:alta_de_segundo_factor")


def test_el_comando_se_queja_de_un_correo_que_no_existe():
    with pytest.raises(CommandError):
        call_command("restablecer_segundo_factor", "nadie@clinica.example")

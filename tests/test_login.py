"""Un Usuario entra con su correo y su contraseña, y sin sesión no ve nada interno."""

import pytest
from django.urls import NoReverseMatch, reverse

from tests.factories import CONTRASENA_DE_PRUEBA, UsuarioFactory

pytestmark = pytest.mark.django_db


def _entrar(client, usuario, contrasena=CONTRASENA_DE_PRUEBA):
    return client.post(
        reverse("account_login"),
        {"login": usuario.email, "password": contrasena},
    )


def test_un_usuario_entra_con_su_correo_y_su_contrasena(client):
    usuario = UsuarioFactory()

    respuesta = _entrar(client, usuario)

    assert respuesta.status_code == 302
    assert client.session.get("_auth_user_id") == str(usuario.pk)


def test_una_contrasena_equivocada_no_abre_sesion(client):
    usuario = UsuarioFactory()

    respuesta = _entrar(client, usuario, contrasena="la-que-no-es")

    assert respuesta.status_code == 200
    assert "_auth_user_id" not in client.session


def test_un_usuario_desactivado_no_entra(client):
    usuario = UsuarioFactory(is_active=False)

    _entrar(client, usuario)

    assert "_auth_user_id" not in client.session


def test_el_login_lleva_al_inicio_del_panel(client):
    usuario = UsuarioFactory()

    respuesta = _entrar(client, usuario)

    assert respuesta["Location"] == reverse("tenancy:inicio")


def test_un_usuario_con_sesion_puede_salir(client):
    usuario = UsuarioFactory()
    _entrar(client, usuario)

    client.post(reverse("account_logout"))

    assert "_auth_user_id" not in client.session


@pytest.mark.parametrize(
    "pagina", ["tenancy:inicio", "tenancy:usuarios", "tenancy:crear_usuario"]
)
def test_un_usuario_sin_sesion_que_pide_una_pagina_interna_acaba_en_el_login(client, pagina):
    respuesta = client.get(reverse(pagina))

    assert respuesta.status_code == 302
    assert respuesta["Location"].startswith(reverse("account_login"))


def test_sin_sesion_tampoco_se_actua_sobre_las_paginas_que_solo_aceptan_post(client):
    """Sin sesión se va al login, no a un 405 que ya cuenta que la página existe."""
    respuesta = client.get(reverse("tenancy:cambiar_sede"))

    assert respuesta.status_code == 302
    assert respuesta["Location"].startswith(reverse("account_login"))


def test_no_existe_ninguna_pagina_de_registro(client):
    """Los Usuarios los crea el admin de la Clínica: nadie se da de alta solo."""
    with pytest.raises(NoReverseMatch):
        reverse("account_signup")

    assert client.get("/accounts/signup/").status_code == 404

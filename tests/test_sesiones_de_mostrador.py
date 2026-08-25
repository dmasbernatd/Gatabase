"""La sesión de un computador de mostrador caduca sola, avisa antes, y se cambia
de Usuario en un clic.

El riesgo de este ticket no es un atacante remoto: es la pantalla encendida a la
vista de los Tutores y la tablet que comparten tres veterinarios. Por eso todo
se comprueba por HTTP, que es como se usa de verdad.
"""

from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.sessions.models import Session
from django.urls import reverse
from django.utils import timezone

from apps.tenancy.models import Rol
from apps.tenancy.sedes import CLAVE_DE_SESION
from tests.factories import CONTRASENA_DE_PRUEBA, SedeFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

PAGINAS_INTERNAS = ["tenancy:inicio", "buscar", "tutors:lista"]


def _entrar(client, usuario):
    return client.post(
        reverse("account_login"),
        {"login": usuario.email, "password": CONTRASENA_DE_PRUEBA},
    )


def _sesion_guardada(client):
    return Session.objects.get(session_key=client.session.session_key)


def _caducar(client):
    """Adelanta el reloj de la sesión guardada: el Usuario dejó de tocar nada."""
    sesion = _sesion_guardada(client)
    sesion.expire_date = timezone.now() - timedelta(seconds=1)
    sesion.save(update_fields=["expire_date"])


def test_la_sesion_caduca_por_inactividad(client):
    usuario = UsuarioFactory()
    _entrar(client, usuario)
    _caducar(client)

    respuesta = client.get(reverse("tenancy:inicio"))

    assert respuesta.status_code == 302
    assert respuesta["Location"].startswith(reverse("account_login"))


def test_cada_peticion_alarga_la_sesion(client):
    """Caduca por inactividad, no a las 30 minutos de haber entrado: quien está
    trabajando no se queda fuera a media ficha."""
    usuario = UsuarioFactory()
    _entrar(client, usuario)
    sesion = _sesion_guardada(client)
    sesion.expire_date = timezone.now() + timedelta(seconds=60)
    sesion.save(update_fields=["expire_date"])

    client.get(reverse("tenancy:inicio"))

    alargada = _sesion_guardada(client).expire_date
    assert alargada > timezone.now() + timedelta(seconds=60)


def test_la_caducidad_por_defecto_es_de_media_hora():
    assert settings.SESSION_COOKIE_AGE == 30 * 60
    assert settings.SESSION_SAVE_EVERY_REQUEST is True


def test_el_aviso_se_da_antes_de_que_caduque_la_sesion():
    from apps.tenancy.sesion import segundos_de_aviso

    assert 0 < segundos_de_aviso() < settings.SESSION_COOKIE_AGE


def test_con_sesiones_muy_cortas_el_aviso_no_llega_tarde(settings):
    """Con la caducidad bajada a un minuto, un aviso de dos no se daría nunca."""
    from apps.tenancy.sesion import segundos_de_aviso

    settings.SESSION_COOKIE_AGE = 60

    assert 0 < segundos_de_aviso() <= 30


def test_la_pagina_lleva_lo_que_el_aviso_necesita_para_contar(client):
    usuario = UsuarioFactory()
    _entrar(client, usuario)

    contenido = client.get(reverse("tenancy:inicio")).content.decode()

    assert 'data-segundos-de-sesion="1800"' in contenido
    assert "data-segundos-de-aviso=" in contenido


def test_seguir_conectado_alarga_la_sesion_sin_recargar(client):
    usuario = UsuarioFactory()
    _entrar(client, usuario)
    sesion = _sesion_guardada(client)
    sesion.expire_date = timezone.now() + timedelta(seconds=60)
    sesion.save(update_fields=["expire_date"])

    respuesta = client.post(reverse("tenancy:seguir_conectado"))

    assert respuesta.status_code == 204
    assert _sesion_guardada(client).expire_date > timezone.now() + timedelta(seconds=60)


def test_seguir_conectado_no_le_sirve_a_quien_no_tiene_sesion(client):
    respuesta = client.post(reverse("tenancy:seguir_conectado"))

    assert respuesta.status_code == 302
    assert respuesta["Location"].startswith(reverse("account_login"))


@pytest.mark.parametrize("pagina", PAGINAS_INTERNAS)
def test_toda_pagina_interna_dice_que_usuario_esta_activo(client, pagina):
    """La firma de una Consulta tiene valor legal: quien la escribe tiene que
    poder ver de un vistazo con qué cuenta está trabajando."""
    usuario = UsuarioFactory(nombre="Ignacia", apellidos="Fuenzalida", rol=Rol.VETERINARIO)
    _entrar(client, usuario)

    contenido = client.get(reverse(pagina)).content.decode()

    assert "Ignacia Fuenzalida" in contenido
    assert "veterinario" in contenido


@pytest.mark.parametrize("pagina", PAGINAS_INTERNAS)
def test_desde_toda_pagina_interna_se_cambia_de_usuario(client, pagina):
    usuario = UsuarioFactory()
    _entrar(client, usuario)

    contenido = client.get(reverse(pagina)).content.decode()

    assert reverse("tenancy:cambiar_de_usuario") in contenido


def test_el_cambio_de_usuario_cierra_la_sesion_y_lleva_al_login(client):
    usuario = UsuarioFactory()
    _entrar(client, usuario)

    respuesta = client.post(reverse("tenancy:cambiar_de_usuario"))

    assert respuesta["Location"] == reverse("account_login")
    assert "_auth_user_id" not in client.session


def test_el_cambio_de_usuario_conserva_la_sede_de_la_tablet(client):
    """La tablet no se mueve de box: quien entra detrás no tiene que volver a
    elegir dónde está trabajando."""
    box = SedeFactory(nombre="Box de Ñuñoa")
    otra = SedeFactory(clinic=box.clinic, nombre="Almirante Barroso")
    saliente = UsuarioFactory(clinic=box.clinic, sedes=[box, otra])
    entrante = UsuarioFactory(clinic=box.clinic, sedes=[box, otra])
    _entrar(client, saliente)
    client.post(reverse("tenancy:cambiar_sede"), {"sede": box.pk})

    client.post(reverse("tenancy:cambiar_de_usuario"))
    _entrar(client, entrante)

    assert client.session[CLAVE_DE_SESION] == box.pk


def test_sin_sesion_el_cambio_de_usuario_no_hace_nada(client):
    respuesta = client.get(reverse("tenancy:cambiar_de_usuario"))

    assert respuesta.status_code == 302
    assert respuesta["Location"].startswith(reverse("account_login"))

"""La planilla que nadie confirmó no se queda en el disco para siempre.

Entre la vista previa y la confirmación la planilla espera en disco
(`apps/imports/almacen.py`), y es una copia de los datos personales de cientos
de Tutores. Lo que se comprueba aquí es que se va sola cuando ya no la puede
confirmar nadie —al subir otra, o cuando la barre el cron— y que no se va la que
alguien sigue mirando.
"""

import io
import os
import time

import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.tutors.models import Tutor
from tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

CABECERA = "nombre,apellidos,rut,telefono,correo,direccion"


@pytest.fixture
def directorio(settings, tmp_path):
    settings.DIRECTORIO_DE_IMPORTACIONES = tmp_path
    return tmp_path


def subir(client, nombre="clientes.csv"):
    archivo = io.BytesIO(f"{CABECERA}\nAna,Pérez,,+56912345678,,\n".encode())
    archivo.name = nombre
    return client.post(reverse("imports:tutores"), {"archivo": archivo}, follow=True)


def admin(client):
    client.force_login(UsuarioFactory(rol="admin"))


def envejecer(archivo, segundos):
    antes = time.time() - segundos
    os.utime(archivo, (antes, antes))


def barrer():
    salida = io.StringIO()
    call_command("barrer_importaciones", stdout=salida)
    return salida.getvalue()


def test_el_cron_borra_la_planilla_cuya_sesion_ya_caduco(client, directorio, settings):
    admin(client)
    subir(client)
    (archivo,) = directorio.glob("*.csv")
    envejecer(archivo, settings.SESSION_COOKIE_AGE + 60)

    salida = barrer()

    assert not archivo.exists()
    assert "1" in salida


def test_el_cron_no_toca_la_planilla_que_alguien_todavia_puede_confirmar(
    client, directorio, settings
):
    admin(client)
    subir(client)
    (archivo,) = directorio.glob("*.csv")
    envejecer(archivo, settings.SESSION_COOKIE_AGE - 60)

    barrer()

    assert archivo.exists()
    client.post(reverse("imports:confirmar"))
    assert Tutor.de_todas_las_clinicas.filter(nombre="Ana").exists()


def test_mirar_la_vista_previa_la_rejuvenece_y_el_cron_la_respeta(client, directorio, settings):
    admin(client)
    subir(client)
    (archivo,) = directorio.glob("*.csv")
    envejecer(archivo, settings.SESSION_COOKIE_AGE + 60)

    client.get(reverse("imports:vista_previa"))
    barrer()

    assert archivo.exists()


def test_subir_una_planilla_barre_las_viejas_de_otros(client, directorio, settings):
    olvidada = directorio / "de-una-sesion-que-caduco.csv"
    olvidada.write_text(f"{CABECERA}\n")
    envejecer(olvidada, settings.SESSION_COOKIE_AGE + 60)

    admin(client)
    subir(client)

    assert not olvidada.exists()
    assert len(list(directorio.glob("*.csv"))) == 1


def test_el_cron_con_el_directorio_vacio_no_revienta(directorio):
    assert "0" in barrer()

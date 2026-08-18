"""El admin de la Clínica crea Usuarios, les asigna rol y Sedes, y los desactiva."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.tenancy.models import Rol
from tests.factories import ClinicaFactory, SedeFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

Usuario = get_user_model()

CONTRASENA_NUEVA = "consulta-de-la-tarde-2026"


@pytest.fixture
def clinica():
    return ClinicaFactory(nombre="Clínica Los Andes")


@pytest.fixture
def sede(clinica):
    return SedeFactory(clinic=clinica, nombre="Providencia")


@pytest.fixture
def admin(client, clinica, sede):
    usuario = UsuarioFactory(clinic=clinica, sedes=[sede], rol=Rol.ADMIN)
    client.force_login(usuario)
    return usuario


def test_el_admin_crea_un_usuario_con_rol_y_sedes(client, admin, clinica, sede):
    respuesta = client.post(
        reverse("tenancy:crear_usuario"),
        {
            "email": "veterinaria@losandes.example",
            "nombre": "Antonia",
            "apellidos": "Vergara",
            "rol": Rol.VETERINARIO,
            "sedes": [sede.pk],
            "contrasena": CONTRASENA_NUEVA,
        },
    )

    creada = Usuario.objects.get(email="veterinaria@losandes.example")
    assert respuesta.status_code == 302
    assert creada.clinic == clinica
    assert creada.rol == Rol.VETERINARIO
    assert list(creada.sedes.all()) == [sede]


def test_el_usuario_creado_puede_entrar_con_su_contrasena(client, admin, sede):
    client.post(
        reverse("tenancy:crear_usuario"),
        {
            "email": "recepcion@losandes.example",
            "nombre": "Javiera",
            "apellidos": "Soto",
            "rol": Rol.RECEPCION,
            "sedes": [sede.pk],
            "contrasena": CONTRASENA_NUEVA,
        },
    )
    client.logout()

    client.post(
        reverse("account_login"),
        {"login": "recepcion@losandes.example", "password": CONTRASENA_NUEVA},
    )

    assert "_auth_user_id" in client.session


def test_el_admin_no_puede_asignar_una_sede_de_otra_clinica(client, admin, sede):
    ajena = SedeFactory(nombre="Sede de otra Clínica")

    client.post(
        reverse("tenancy:crear_usuario"),
        {
            "email": "colada@otra.example",
            "nombre": "Pedro",
            "apellidos": "Muñoz",
            "rol": Rol.RECEPCION,
            "sedes": [ajena.pk],
            "contrasena": CONTRASENA_NUEVA,
        },
    )

    assert not Usuario.objects.filter(email="colada@otra.example").exists()


def test_el_admin_cambia_el_rol_y_las_sedes_de_un_usuario(client, admin, clinica, sede):
    otra_sede = SedeFactory(clinic=clinica, nombre="Maipú")
    usuario = UsuarioFactory(clinic=clinica, sedes=[sede], rol=Rol.RECEPCION)

    client.post(
        reverse("tenancy:editar_usuario", args=[usuario.pk]),
        {
            "email": usuario.email,
            "nombre": usuario.nombre,
            "apellidos": usuario.apellidos,
            "rol": Rol.VETERINARIO,
            "sedes": [sede.pk, otra_sede.pk],
        },
    )

    usuario.refresh_from_db()
    assert usuario.rol == Rol.VETERINARIO
    assert set(usuario.sedes.all()) == {sede, otra_sede}


def test_el_admin_desactiva_un_usuario(client, admin, clinica, sede):
    usuario = UsuarioFactory(clinic=clinica, sedes=[sede])

    client.post(reverse("tenancy:desactivar_usuario", args=[usuario.pk]))

    usuario.refresh_from_db()
    assert not usuario.is_active


def test_el_listado_solo_muestra_usuarios_de_la_propia_clinica(client, admin, clinica, sede):
    UsuarioFactory(clinic=clinica, sedes=[sede], nombre="Javiera", apellidos="Soto")
    UsuarioFactory(nombre="Rosa", apellidos="Delaotra")

    contenido = client.get(reverse("tenancy:usuarios")).content.decode()

    assert "Soto" in contenido
    assert "Delaotra" not in contenido


def test_el_admin_no_toca_usuarios_de_otra_clinica(client, admin):
    ajeno = UsuarioFactory()

    respuesta = client.post(reverse("tenancy:desactivar_usuario", args=[ajeno.pk]))

    ajeno.refresh_from_db()
    assert respuesta.status_code == 404
    assert ajeno.is_active


def test_un_admin_no_puede_desactivarse_a_si_mismo(client, admin):
    respuesta = client.post(reverse("tenancy:desactivar_usuario", args=[admin.pk]))

    admin.refresh_from_db()
    assert respuesta.status_code == 404
    assert admin.is_active


def test_una_contrasena_parecida_al_correo_no_se_acepta(client, admin, sede):
    client.post(
        reverse("tenancy:crear_usuario"),
        {
            "email": "javiera.soto@losandes.example",
            "nombre": "Javiera",
            "apellidos": "Soto",
            "rol": Rol.RECEPCION,
            "sedes": [sede.pk],
            "contrasena": "javiera.soto@losandes.example",
        },
    )

    assert not Usuario.objects.filter(email="javiera.soto@losandes.example").exists()


@pytest.mark.parametrize("rol", [Rol.RECEPCION, Rol.VETERINARIO])
def test_quien_no_es_admin_no_accede_a_la_administracion_de_usuarios(
    client, clinica, sede, rol
):
    otro = UsuarioFactory(clinic=clinica, sedes=[sede])
    client.force_login(UsuarioFactory(clinic=clinica, sedes=[sede], rol=rol))

    assert client.get(reverse("tenancy:usuarios")).status_code == 403
    assert client.get(reverse("tenancy:crear_usuario")).status_code == 403
    assert client.get(reverse("tenancy:editar_usuario", args=[otro.pk])).status_code == 403
    assert (
        client.post(reverse("tenancy:desactivar_usuario", args=[otro.pk])).status_code == 403
    )

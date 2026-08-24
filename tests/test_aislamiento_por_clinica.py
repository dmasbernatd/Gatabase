"""Ningún Usuario ve datos de otra Clínica (ADR-0003).

Dos planos: el manager, que es donde vive la garantía, y la petición HTTP, que
es donde se rompería si la garantía fallase.
"""

import pytest
from django.urls import reverse

from apps.patients.catalogo import Especie
from apps.patients.models import Paciente
from apps.tenancy.aislamiento import activar_clinica, clinica_activa
from apps.tutors.models import Tutor
from tests.factories import ClinicaFactory, PacienteFactory, TutorFactory, UsuarioFactory

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


def test_abrir_para_editar_un_tutor_de_otra_clinica_da_404(client):
    usuario = UsuarioFactory()
    ajeno = TutorFactory(nombre="Ignacio", apellidos="Fuentes", telefono="+56911112222")
    client.force_login(usuario)

    respuesta = client.get(reverse("tutors:editar", args=[ajeno.pk]))

    assert respuesta.status_code == 404
    assert "+56911112222" not in respuesta.content.decode()


def test_guardar_encima_de_un_tutor_de_otra_clinica_da_404_y_no_lo_toca(client):
    """Un 404 en el listado no sirve de nada si el formulario acepta el `pk`."""
    usuario = UsuarioFactory()
    ajeno = TutorFactory(nombre="Ignacio", apellidos="Fuentes")
    client.force_login(usuario)

    respuesta = client.post(
        reverse("tutors:editar", args=[ajeno.pk]), {"nombre": "Camila", "apellidos": "Rojas"}
    )

    ajeno.refresh_from_db()
    assert respuesta.status_code == 404
    assert ajeno.nombre == "Ignacio"


def test_el_tutor_que_registra_recepcion_nace_en_su_propia_clinica(client):
    usuario = UsuarioFactory()
    client.force_login(usuario)

    client.post(reverse("tutors:crear"), {"nombre": "Camila", "apellidos": "Rojas"})

    assert Tutor.de_todas_las_clinicas.get().clinic == usuario.clinic


def test_la_clinica_activa_no_sobrevive_a_la_peticion(client):
    usuario = UsuarioFactory()
    client.force_login(usuario)

    client.get(reverse("tenancy:inicio"))

    assert clinica_activa() is None


# --- Pacientes y Vínculos -------------------------------------------------
#
# El Paciente entra por HTTP igual que el Tutor, y el Vínculo además por los dos
# extremos: no basta con no ver al Paciente de otra Clínica si se le puede colgar
# un Tutor propio, ni con no ver a su Tutor si se le puede pasar el cargo.


def test_pedir_por_identificador_un_paciente_de_otra_clinica_da_404(client):
    usuario = UsuarioFactory()
    ajeno = PacienteFactory(nombre="Rocco")
    client.force_login(usuario)

    respuesta = client.get(reverse("patients:ficha", args=[ajeno.pk]))

    assert respuesta.status_code == 404
    assert "Rocco" not in respuesta.content.decode()


def test_abrir_para_editar_un_paciente_de_otra_clinica_da_404(client):
    usuario = UsuarioFactory()
    ajeno = PacienteFactory(nombre="Rocco")
    client.force_login(usuario)

    respuesta = client.get(reverse("patients:editar", args=[ajeno.pk]))

    assert respuesta.status_code == 404
    assert "Rocco" not in respuesta.content.decode()


def test_guardar_encima_de_un_paciente_de_otra_clinica_da_404_y_no_lo_toca(client):
    usuario = UsuarioFactory()
    ajeno = PacienteFactory(nombre="Rocco")
    client.force_login(usuario)

    respuesta = client.post(
        reverse("patients:editar", args=[ajeno.pk]), {"nombre": "Otro", "especie": Especie.GATO}
    )

    ajeno.refresh_from_db()
    assert respuesta.status_code == 404
    assert ajeno.nombre == "Rocco"


def test_registrar_un_paciente_a_nombre_de_un_tutor_de_otra_clinica_da_404(client):
    usuario = UsuarioFactory()
    ajeno = TutorFactory(nombre="Ignacio", apellidos="Fuentes")
    client.force_login(usuario)

    respuesta = client.post(
        reverse("patients:crear", args=[ajeno.pk]), {"nombre": "Rocco", "especie": Especie.PERRO}
    )

    assert respuesta.status_code == 404
    assert not Paciente.de_todas_las_clinicas.exists()


def test_el_paciente_que_registra_recepcion_nace_en_su_propia_clinica(client):
    usuario = UsuarioFactory()
    tutor = TutorFactory(clinic=usuario.clinic)
    client.force_login(usuario)

    client.post(
        reverse("patients:crear", args=[tutor.pk]), {"nombre": "Rocco", "especie": Especie.PERRO}
    )

    paciente = Paciente.de_todas_las_clinicas.get()
    assert paciente.clinic == usuario.clinic
    assert paciente.quienes_responden.get().clinic == usuario.clinic


def test_no_se_puede_vincular_a_un_tutor_de_otra_clinica(client):
    """Ni ofreciéndolo en el desplegable ni enviando su identificador a mano."""
    usuario = UsuarioFactory()
    propio = PacienteFactory(clinic=usuario.clinic)
    ajeno = TutorFactory(nombre="Ignacio", apellidos="Fuentes")
    client.force_login(usuario)

    ofrecidos = client.get(reverse("patients:vincular", args=[propio.pk])).content.decode()
    respuesta = client.post(reverse("patients:vincular", args=[propio.pk]), {"tutor": ajeno.pk})

    assert "Ignacio Fuentes" not in ofrecidos
    assert respuesta.status_code == 200
    assert not propio.quienes_responden.exists()


def test_sumar_un_tutor_a_un_paciente_de_otra_clinica_da_404(client):
    usuario = UsuarioFactory()
    ajeno = PacienteFactory()
    client.force_login(usuario)

    respuesta = client.post(
        reverse("patients:vincular", args=[ajeno.pk]),
        {"tutor": TutorFactory(clinic=usuario.clinic).pk},
    )

    assert respuesta.status_code == 404
    assert not ajeno.quienes_responden.exists()


def test_pasar_el_cargo_en_un_vinculo_de_otra_clinica_da_404(client):
    usuario = UsuarioFactory()
    ajeno = PacienteFactory()
    primero = TutorFactory(clinic=ajeno.clinic).se_hace_cargo_de(ajeno)
    segundo = TutorFactory(clinic=ajeno.clinic).se_hace_cargo_de(ajeno)
    client.force_login(usuario)

    respuesta = client.post(reverse("patients:responsable", args=[ajeno.pk, segundo.pk]))

    primero.refresh_from_db()
    assert respuesta.status_code == 404
    assert primero.responsable

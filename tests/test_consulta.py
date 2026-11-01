"""Abrir una Consulta y escribirla durante la atención (H2, ticket 01).

La costura es la petición HTTP con el cliente de test, autenticada como
veterinario o como recepción (`spec.md`): se prueba lo que el Usuario observa y
lo que el sistema le niega, no la estructura interna del modelo.

Lo que este archivo viene a fijar, y que no es evidente mirando el formulario:
una Consulta se abre **sin Cita** —la mitad de lo que entra por la puerta no
tenía hora—, la escribe **su autor** y nadie más, y **no se borra**. De lo que
pasa al cerrarla sabe el ticket 02.
"""

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.audit.models import Accion, RegistroDeAcceso
from apps.patients.estados import EstadoDelPaciente
from apps.patients.models import Paciente
from apps.records.models import Consulta
from tests.factories import (
    ConsultaFactory,
    PacienteFactory,
    SedeFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


# --- Quién entra ----------------------------------------------------------


def veterinario(client, **campos):
    """Quien atiende: el único rol que abre y escribe Consultas."""
    usuario = UsuarioFactory(rol="veterinario", **campos)
    client.force_login(usuario)
    return usuario


def recepcion(client, **campos):
    """Quien está en el mostrador: lee la Consulta, pero no la firma."""
    usuario = UsuarioFactory(rol="recepcion", **campos)
    client.force_login(usuario)
    return usuario


def anotaciones_sobre(objeto, accion):
    return RegistroDeAcceso.de_todas_las_clinicas.filter(
        tipo_de_objeto=objeto._meta.label, identificador=str(objeto.pk), accion=accion
    )


LO_QUE_SE_ESCRIBE = {
    "motivo": "Cojea de la pata de atrás desde el fin de semana",
    "subjetivo": "El Tutor cuenta que saltó de la cama el sábado",
    "objetivo": "Dolor a la extensión de la rodilla derecha",
    "evaluacion": "Compatible con rotura de ligamento cruzado",
    "plan": "Radiografía y reposo estricto; revisión en siete días",
    "diagnostico": "Rotura de ligamento cruzado craneal",
    "tratamiento_indicado": "Antiinflamatorio diez días y reposo",
    "folio_de_la_receta_del_sag": "SAG-2026-00123",
}

VACIA = {campo: "" for campo in LO_QUE_SE_ESCRIBE}


def abrir(client, paciente, **escrito):
    """Abre una Consulta desde la ficha del Paciente, como la abre el veterinario."""
    return client.post(reverse("records:abrir", args=[paciente.pk]), {**VACIA, **escrito})


def escribir(client, consulta, **escrito):
    return client.post(reverse("records:escribir", args=[consulta.pk]), {**VACIA, **escrito})


# --- Abrir una Consulta ---------------------------------------------------


def test_el_veterinario_abre_una_consulta_desde_la_ficha_del_paciente(client):
    usuario = veterinario(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    respuesta = abrir(client, paciente, **LO_QUE_SE_ESCRIBE)

    consulta = Consulta.de_todas_las_clinicas.get(paciente=paciente)
    # Guardar vuelve a la Consulta, que es donde se sigue escribiendo.
    assert respuesta["Location"] == reverse("records:consulta", args=[consulta.pk])
    for campo, escrito in LO_QUE_SE_ESCRIBE.items():
        assert getattr(consulta, campo) == escrito


def test_la_consulta_registra_quien_atendio_en_que_sede_y_cuando(client):
    """Las tres cosas que se preguntan al leerla seis meses después."""
    sede = SedeFactory()
    usuario = veterinario(client, clinic=sede.clinic, sedes=[sede])
    paciente = PacienteFactory(clinic=sede.clinic)

    abrir(client, paciente)

    consulta = Consulta.de_todas_las_clinicas.get(paciente=paciente)
    assert consulta.veterinario == usuario
    assert consulta.sede == sede
    assert consulta.clinic == sede.clinic
    assert consulta.abierta is not None


def test_una_consulta_se_abre_sin_que_exista_ninguna_cita(client):
    """La mitad de lo que entra por la puerta no tenía hora.

    `records` no importa de `scheduling` (`CLAUDE.md`), así que la Consulta no
    sabe siquiera que existan las Citas: no hay ninguna en el sistema y se abre
    igual. Sin esto, atender a un espontáneo obligaría a inventar una reserva
    que nadie hizo.
    """
    usuario = veterinario(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    abrir(client, paciente, motivo="Llegó sin hora, atropellado")

    consulta = Consulta.de_todas_las_clinicas.get(paciente=paciente)
    assert consulta.motivo == "Llegó sin hora, atropellado"
    # Y lo que lo garantiza no es este test, sino que la Consulta no tiene por
    # dónde apuntar a una Cita: el vínculo irá al revés, y es opcional.
    assert not hasattr(consulta, "cita")


def test_una_consulta_se_abre_sin_nada_escrito(client):
    """Se abre al empezar a atender, cuando todavía no se sabe nada. Exigir
    aquí lo que no se sabe obligaría a escribir un punto para poder guardar, y
    un punto no se distingue de un dato que nadie tomó."""
    usuario = veterinario(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    abrir(client, paciente)

    assert Consulta.de_todas_las_clinicas.filter(paciente=paciente).count() == 1


def test_el_formulario_de_apertura_se_sirve_con_el_paciente_delante(client):
    usuario = veterinario(client)
    paciente = PacienteFactory(clinic=usuario.clinic, nombre="Rocco")

    respuesta = client.get(reverse("records:abrir", args=[paciente.pk]))

    assert respuesta.status_code == 200
    assert "Rocco" in respuesta.content.decode()


def test_la_ficha_del_paciente_ofrece_abrir_una_consulta_al_veterinario(client):
    usuario = veterinario(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    respuesta = client.get(reverse("patients:ficha", args=[paciente.pk]))

    assert reverse("records:abrir", args=[paciente.pk]) in respuesta.content.decode()


def test_la_ficha_no_le_ofrece_abrir_una_consulta_a_recepcion(client):
    """No es decoración: lo que recepción no puede hacer tampoco se le ofrece,
    para que no descubra el 403 con el animal delante."""
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    respuesta = client.get(reverse("patients:ficha", args=[paciente.pk]))

    assert reverse("records:abrir", args=[paciente.pk]) not in respuesta.content.decode()


# --- Guardar cuantas veces haga falta -------------------------------------


def test_guardar_deja_la_consulta_abierta_y_vuelve_a_ella(client):
    """Una Consulta no se escribe de una vez: se escribe entre que entra el
    animal y que sale."""
    usuario = veterinario(client)
    consulta = ConsultaFactory(paciente__clinic=usuario.clinic, veterinario=usuario)

    respuesta = escribir(client, consulta, motivo="Revisión", objetivo="Temperatura normal")

    assert respuesta["Location"] == reverse("records:consulta", args=[consulta.pk])
    guardada = Consulta.de_todas_las_clinicas.get(pk=consulta.pk)
    assert guardada.esta_abierta
    assert guardada.objetivo == "Temperatura normal"


def test_se_puede_guardar_muchas_veces_seguidas(client):
    usuario = veterinario(client)
    consulta = ConsultaFactory(paciente__clinic=usuario.clinic, veterinario=usuario)

    escribir(client, consulta, subjetivo="Primero esto")
    escribir(client, consulta, subjetivo="Primero esto", objetivo="Después esto")
    escribir(client, consulta, subjetivo="Primero esto", objetivo="Después esto", plan="Y esto")

    guardada = Consulta.de_todas_las_clinicas.get(pk=consulta.pk)
    assert (guardada.subjetivo, guardada.objetivo, guardada.plan) == (
        "Primero esto",
        "Después esto",
        "Y esto",
    )
    # Y sigue siendo una sola Consulta: guardar no abre otra.
    assert Consulta.de_todas_las_clinicas.filter(paciente=consulta.paciente).count() == 1


def test_guardar_no_reescribe_quien_atendio(client):
    """Quién atendió es un hecho de aquella tarde. La Consulta la escribe solo su
    autor, así que esto no puede pasar hoy; el test es lo que hace que siga sin
    poder pasar el día que algo más escriba por esta vista."""
    usuario = veterinario(client)
    consulta = ConsultaFactory(paciente__clinic=usuario.clinic, veterinario=usuario)
    sede_de_antes = consulta.sede

    escribir(client, consulta, plan="Reposo")

    guardada = Consulta.de_todas_las_clinicas.get(pk=consulta.pk)
    assert guardada.veterinario == usuario
    assert guardada.sede == sede_de_antes


# --- Quién la escribe y quién solo la lee ---------------------------------


def test_recepcion_no_abre_consultas(client):
    """Una Consulta es un documento clínico firmado por un veterinario: recepción
    no puede figurar como su autor."""
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    respuesta = abrir(client, paciente, **LO_QUE_SE_ESCRIBE)

    assert respuesta.status_code == 403
    assert not Consulta.de_todas_las_clinicas.filter(paciente=paciente).exists()


def test_el_admin_tampoco_abre_consultas(client):
    """Ser admin de la Clínica no es atender: el rol que firma es el que atiende."""
    usuario = UsuarioFactory(rol="admin")
    client.force_login(usuario)
    paciente = PacienteFactory(clinic=usuario.clinic)

    respuesta = abrir(client, paciente, **LO_QUE_SE_ESCRIBE)

    assert respuesta.status_code == 403
    assert not Consulta.de_todas_las_clinicas.filter(paciente=paciente).exists()


def test_recepcion_no_escribe_en_una_consulta_abierta(client):
    usuario = recepcion(client)
    consulta = ConsultaFactory(paciente__clinic=usuario.clinic)

    respuesta = escribir(client, consulta, plan="Lo que diga recepción")

    assert respuesta.status_code == 403
    assert Consulta.de_todas_las_clinicas.get(pk=consulta.pk).plan == ""


def test_recepcion_si_lee_la_consulta(client):
    """Es la hoja que antes estaba en el archivador: recepción la necesita para
    decirle al Tutor lo que se le hizo al animal."""
    usuario = recepcion(client)
    consulta = ConsultaFactory(paciente__clinic=usuario.clinic, plan="Reposo siete días")

    respuesta = client.get(reverse("records:consulta", args=[consulta.pk]))

    assert respuesta.status_code == 200
    assert "Reposo siete días" in respuesta.content.decode()


def test_otro_veterinario_lee_la_consulta_pero_no_la_cambia(client):
    """Dos manos escribiendo el mismo documento clínico dejan uno que no dice
    quién observó qué. El otro la lee entera y, si tiene algo que añadir, lo
    añadirá como Enmienda suya (ticket 03)."""
    usuario = veterinario(client)
    consulta = ConsultaFactory(paciente__clinic=usuario.clinic, plan="Lo que escribió el otro")

    assert consulta.veterinario != usuario
    leida = client.get(reverse("records:consulta", args=[consulta.pk]))
    assert leida.status_code == 200
    assert "Lo que escribió el otro" in leida.content.decode()

    respuesta = escribir(client, consulta, plan="Lo que yo diría")

    # No es un 403: la Consulta se puede ver, y ahí es donde se le manda.
    assert respuesta["Location"] == reverse("records:consulta", args=[consulta.pk])
    assert Consulta.de_todas_las_clinicas.get(pk=consulta.pk).plan == "Lo que escribió el otro"


def test_la_consulta_de_otro_no_ofrece_el_enlace_para_escribirla(client):
    usuario = veterinario(client)
    consulta = ConsultaFactory(paciente__clinic=usuario.clinic)

    respuesta = client.get(reverse("records:consulta", args=[consulta.pk]))

    assert reverse("records:escribir", args=[consulta.pk]) not in respuesta.content.decode()


def test_su_autor_si_ve_el_enlace_para_seguir_escribiendo(client):
    usuario = veterinario(client)
    consulta = ConsultaFactory(paciente__clinic=usuario.clinic, veterinario=usuario)

    respuesta = client.get(reverse("records:consulta", args=[consulta.pk]))

    assert reverse("records:escribir", args=[consulta.pk]) in respuesta.content.decode()


def test_sin_sesion_no_se_abre_ninguna_consulta(client):
    paciente = PacienteFactory()

    respuesta = abrir(client, paciente, **LO_QUE_SE_ESCRIBE)

    # Al login, no al 403: no hay Usuario a quien negarle nada todavía.
    assert respuesta.status_code == 302
    assert reverse("account_login") in respuesta["Location"]
    assert not Consulta.de_todas_las_clinicas.filter(paciente=paciente).exists()


# --- Un Paciente fallecido no admite Consultas nuevas ---------------------


def test_un_paciente_fallecido_no_admite_consultas_nuevas(client):
    """Su Historia clínica queda en solo lectura (`CONTEXT.md`), que es lo
    contrario de borrarla."""
    usuario = veterinario(client)
    paciente = PacienteFactory(clinic=usuario.clinic)
    paciente.cambiar_de_estado(EstadoDelPaciente.FALLECIDO)

    respuesta = abrir(client, paciente, **LO_QUE_SE_ESCRIBE)

    # Un desvío a ver la ficha, no un 403: el animal existe y su Historia se lee.
    assert respuesta["Location"] == reverse("patients:ficha", args=[paciente.pk])
    assert not Consulta.de_todas_las_clinicas.filter(paciente=paciente).exists()


def test_un_paciente_inactivo_si_admite_consultas(client):
    """Que un animal llevara dos años sin venir es justamente lo que deja de ser
    verdad cuando entra por la puerta."""
    usuario = veterinario(client)
    paciente = PacienteFactory(clinic=usuario.clinic)
    paciente.cambiar_de_estado(EstadoDelPaciente.INACTIVO)

    abrir(client, paciente, motivo="Volvió después de dos años")

    assert Consulta.de_todas_las_clinicas.filter(paciente=paciente).exists()


def test_las_consultas_de_un_paciente_que_muere_se_conservan(client):
    """Lo que ya está escrito no se toca: lo que deja de poder hacerse es abrir
    otra."""
    usuario = veterinario(client)
    consulta = ConsultaFactory(paciente__clinic=usuario.clinic, veterinario=usuario)

    consulta.paciente.cambiar_de_estado(EstadoDelPaciente.FALLECIDO)

    respuesta = client.get(reverse("records:consulta", args=[consulta.pk]))
    assert respuesta.status_code == 200


def test_la_ficha_de_un_fallecido_no_ofrece_abrir_una_consulta(client):
    usuario = veterinario(client)
    paciente = PacienteFactory(clinic=usuario.clinic)
    paciente.cambiar_de_estado(EstadoDelPaciente.FALLECIDO)

    respuesta = client.get(reverse("patients:ficha", args=[paciente.pk]))

    assert reverse("records:abrir", args=[paciente.pk]) not in respuesta.content.decode()


# --- No existe borrado de Consulta ----------------------------------------


def test_un_paciente_con_consultas_no_se_puede_borrar():
    """El Paciente la protege (`PROTECT`): borrar la ficha de un animal atendido
    falla en la base de datos, y tiene que fallar. No hay vista de borrado de
    Consulta, y esto es lo que lo sostiene aunque alguien escriba una."""
    consulta = ConsultaFactory()

    with pytest.raises(IntegrityError), transaction.atomic():
        Paciente.de_todas_las_clinicas.filter(pk=consulta.paciente.pk).delete()

    assert Consulta.de_todas_las_clinicas.filter(pk=consulta.pk).exists()


def test_no_hay_ninguna_url_que_borre_una_consulta():
    """Lo que no está enrutado no existe, como el registro de `allauth`."""
    from apps.records import urls

    assert [ruta.name for ruta in urls.urlpatterns] == ["abrir", "consulta", "escribir"]


# --- Registro de acceso (ADR-0004) ---------------------------------------


def test_abrir_la_pagina_de_una_consulta_queda_en_el_registro(client):
    """Es un dato de salud, el más protegido que guarda el sistema."""
    usuario = recepcion(client)
    consulta = ConsultaFactory(paciente__clinic=usuario.clinic)

    client.get(reverse("records:consulta", args=[consulta.pk]))

    assert anotaciones_sobre(consulta, Accion.LECTURA).filter(usuario=usuario).exists()
    # La página dice de qué animal se trata: cada ficha servida es una lectura.
    assert anotaciones_sobre(consulta.paciente, Accion.LECTURA).filter(usuario=usuario).exists()


def test_abrir_una_consulta_queda_en_el_registro_como_creacion(client):
    usuario = veterinario(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    abrir(client, paciente, **LO_QUE_SE_ESCRIBE)

    consulta = Consulta.de_todas_las_clinicas.get(paciente=paciente)
    assert anotaciones_sobre(consulta, Accion.CREACION).filter(usuario=usuario).exists()
    # Y la Historia clínica del Paciente cambió: tiene una Consulta más.
    assert anotaciones_sobre(paciente, Accion.MODIFICACION).filter(usuario=usuario).exists()


def test_guardar_una_consulta_queda_en_el_registro_como_modificacion(client):
    usuario = veterinario(client)
    consulta = ConsultaFactory(paciente__clinic=usuario.clinic, veterinario=usuario)

    escribir(client, consulta, plan="Reposo")

    assert anotaciones_sobre(consulta, Accion.MODIFICACION).filter(usuario=usuario).exists()


def test_la_consulta_de_otra_clinica_no_deja_rastro_en_el_registro(client):
    """Un 404 no sirvió ningún dato, y anotarlo llenaría de accesos falsos justo
    la tabla que tiene que valer como prueba."""
    usuario = veterinario(client)
    consulta = ConsultaFactory()

    client.get(reverse("records:consulta", args=[consulta.pk]))

    assert not anotaciones_sobre(consulta, Accion.LECTURA).exists()


# --- Aislamiento por Clínica (ADR-0001, ADR-0003) -------------------------


def test_la_consulta_de_otra_clinica_da_404(client):
    """404 y nunca 403 con contenido: la existencia ya es información, y aquí lo
    que existiría es que ese animal fue atendido."""
    veterinario(client)
    consulta = ConsultaFactory()

    respuesta = client.get(reverse("records:consulta", args=[consulta.pk]))

    assert respuesta.status_code == 404


def test_no_se_escribe_en_la_consulta_de_otra_clinica(client):
    veterinario(client)
    consulta = ConsultaFactory(plan="Lo de la otra Clínica")

    respuesta = escribir(client, consulta, plan="Lo mío")

    assert respuesta.status_code == 404
    assert Consulta.de_todas_las_clinicas.get(pk=consulta.pk).plan == "Lo de la otra Clínica"


def test_no_se_abre_una_consulta_a_un_paciente_de_otra_clinica(client):
    """Aunque sea el mismo animal: no hay deduplicación por microchip entre
    Clínicas, y cada una tiene su propia Historia clínica (ADR-0001)."""
    veterinario(client)
    ajeno = PacienteFactory()

    respuesta = abrir(client, ajeno, **LO_QUE_SE_ESCRIBE)

    assert respuesta.status_code == 404
    assert not Consulta.de_todas_las_clinicas.filter(paciente=ajeno).exists()


def test_la_consulta_no_se_ve_desde_la_clinica_de_al_lado_ni_por_el_manager(client):
    from apps.tenancy.aislamiento import activar_clinica

    consulta = ConsultaFactory()
    otra = PacienteFactory().clinic

    with activar_clinica(otra):
        assert not Consulta.objects.filter(pk=consulta.pk).exists()
    with activar_clinica(consulta.clinic):
        assert Consulta.objects.filter(pk=consulta.pk).exists()

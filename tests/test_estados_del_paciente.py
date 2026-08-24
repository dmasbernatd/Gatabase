"""Cuando un Paciente muere o deja de venir: qué se conserva y qué deja de poder hacerse.

Es el ticket que evita el peor error posible de cara al Tutor —tratar como
activo a un animal que ya no está— sin caer en el otro: borrarlo. Los tests
entran por HTTP como entra recepción y miran las dos mitades, lo que la página
dice y lo que queda guardado.

Lo que la Clínica de al lado no ve está en `test_aislamiento_por_clinica.py`;
aquí solo se comprueba que el cambio de estado tampoco cruza la frontera.
"""

import datetime

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.audit.models import Accion, RegistroDeAcceso
from apps.patients.estados import EstadoDelPaciente
from apps.patients.models import Paciente
from tests.factories import PacienteFactory, TutorFactory, UsuarioFactory, VinculoFactory

pytestmark = pytest.mark.django_db

AYER = datetime.date.today() - datetime.timedelta(days=1)
MANANA = datetime.date.today() + datetime.timedelta(days=1)


def recepcion(client):
    """Quien está en el mostrador: el rol que registra y corrige fichas."""
    usuario = UsuarioFactory(rol="recepcion")
    client.force_login(usuario)
    return usuario


def anotaciones_sobre(objeto, accion):
    return RegistroDeAcceso.de_todas_las_clinicas.filter(
        tipo_de_objeto=objeto._meta.label, identificador=str(objeto.pk), accion=accion
    )


def cambiar_el_estado(client, paciente, estado, **cambios):
    """Deja constancia del estado desde la página del Paciente, como recepción."""
    return client.post(
        reverse("patients:estado", args=[paciente.pk]),
        {"estado": estado, "fecha_de_fallecimiento": "", **cambios},
    )


def pacientes_de(client, tutor, **consulta):
    """La ficha del Tutor, con lo que se le pida al filtro de estado."""
    return client.get(reverse("tutors:ficha", args=[tutor.pk]), consulta)


# --- Los tres estados -----------------------------------------------------


def test_un_paciente_nace_activo():
    """Se registra porque está delante del mostrador: no hay un cuarto valor
    para «no se sabe», como sí lo hay en el Estado de identificación."""
    paciente = PacienteFactory()

    assert paciente.estado == EstadoDelPaciente.ACTIVO
    assert paciente.esta_activo


def test_marcar_fallecido_guarda_la_fecha():
    paciente = PacienteFactory()

    paciente.cambiar_de_estado(EstadoDelPaciente.FALLECIDO, AYER)

    guardado = Paciente.de_todas_las_clinicas.get(pk=paciente.pk)
    assert guardado.esta_fallecido
    assert guardado.fecha_de_fallecimiento == AYER


def test_un_fallecido_puede_no_traer_fecha():
    """El Tutor avisa a veces meses después y no siempre recuerda el día:
    exigirla sería obligar a inventársela."""
    paciente = PacienteFactory()

    paciente.cambiar_de_estado(EstadoDelPaciente.FALLECIDO)

    guardado = Paciente.de_todas_las_clinicas.get(pk=paciente.pk)
    assert guardado.esta_fallecido
    assert guardado.fecha_de_fallecimiento is None


def test_salir_de_fallecido_limpia_la_fecha():
    """Deshacer un fallecimiento marcado por error no puede dejar una fecha de
    muerte en un animal vivo: la ficha diría dos cosas a la vez."""
    paciente = PacienteFactory()
    paciente.cambiar_de_estado(EstadoDelPaciente.FALLECIDO, AYER)

    paciente.cambiar_de_estado(EstadoDelPaciente.ACTIVO)

    guardado = Paciente.de_todas_las_clinicas.get(pk=paciente.pk)
    assert guardado.esta_activo
    assert guardado.fecha_de_fallecimiento is None


def test_la_base_de_datos_rechaza_una_fecha_de_muerte_sin_fallecimiento():
    """La única combinación imposible, y no depende de que nadie se acuerde."""
    with pytest.raises(IntegrityError), transaction.atomic():
        PacienteFactory(estado=EstadoDelPaciente.INACTIVO, fecha_de_fallecimiento=AYER)


def test_inactivo_es_reversible():
    """El animal que dejó de venir sin que se sepa qué pasó, y que vuelve."""
    paciente = PacienteFactory()

    paciente.cambiar_de_estado(EstadoDelPaciente.INACTIVO)
    paciente.cambiar_de_estado(EstadoDelPaciente.ACTIVO)

    assert Paciente.de_todas_las_clinicas.get(pk=paciente.pk).esta_activo


# --- Lo que el estado impide ----------------------------------------------


def test_un_paciente_fallecido_no_admite_citas():
    """La regla queda en el modelo; quien la ejercita al dar una Cita es H3."""
    paciente = PacienteFactory(estado=EstadoDelPaciente.FALLECIDO)

    assert not paciente.admite_citas
    assert paciente.nombre in str(paciente.por_que_no_admite_citas)


def test_un_paciente_inactivo_si_admite_citas():
    """Que lleve dos años sin venir es justamente la razón de citarlo."""
    paciente = PacienteFactory(estado=EstadoDelPaciente.INACTIVO)

    assert paciente.admite_citas
    assert paciente.por_que_no_admite_citas is None


def test_un_paciente_fallecido_conserva_toda_su_informacion():
    """Nunca se borra: ni la ficha, ni quién respondía por él."""
    tutor = TutorFactory()
    paciente = PacienteFactory(clinic=tutor.clinic, nombre="Rocco", color="Negro")
    tutor.se_hace_cargo_de(paciente, responsable=True)

    paciente.cambiar_de_estado(EstadoDelPaciente.FALLECIDO, AYER)

    guardado = Paciente.de_todas_las_clinicas.get(pk=paciente.pk)
    assert guardado.nombre == "Rocco"
    assert guardado.color == "Negro"
    assert guardado.responsable == tutor


# --- Desde el mostrador ---------------------------------------------------


def test_recepcion_deja_constancia_de_que_un_paciente_fallecio(client):
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    respuesta = cambiar_el_estado(
        client, paciente, EstadoDelPaciente.FALLECIDO, fecha_de_fallecimiento=str(AYER)
    )

    guardado = Paciente.de_todas_las_clinicas.get(pk=paciente.pk)
    assert respuesta.status_code == 302
    assert guardado.esta_fallecido
    assert guardado.fecha_de_fallecimiento == AYER


def test_el_cambio_de_estado_queda_en_el_registro_de_acceso(client):
    """A quién se dio por muerto, quién lo hizo y cuándo: es lo que habrá que
    poder demostrar si alguien reclama (ADR-0004)."""
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    cambiar_el_estado(client, paciente, EstadoDelPaciente.FALLECIDO)

    assert anotaciones_sobre(paciente, Accion.MODIFICACION).get().usuario == usuario


def test_abrir_la_pagina_del_estado_deja_constancia_de_la_lectura(client):
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    client.get(reverse("patients:estado", args=[paciente.pk]))

    assert anotaciones_sobre(paciente, Accion.LECTURA).get().usuario == usuario


def test_la_ficha_de_un_fallecido_lo_dice_con_todas_sus_letras(client):
    usuario = recepcion(client)
    paciente = PacienteFactory(
        clinic=usuario.clinic, estado=EstadoDelPaciente.FALLECIDO, fecha_de_fallecimiento=AYER
    )

    contenido = client.get(reverse("patients:ficha", args=[paciente.pk])).content.decode()

    assert "Fallecido" in contenido


def test_la_ficha_de_un_fallecido_no_ofrece_corregirla(client):
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic, estado=EstadoDelPaciente.FALLECIDO)

    contenido = client.get(reverse("patients:ficha", args=[paciente.pk])).content.decode()

    assert reverse("patients:editar", args=[paciente.pk]) not in contenido


def test_la_ficha_de_un_paciente_activo_si_ofrece_corregirla(client):
    """Que el enlace desaparezca es de los fallecidos, no de todos."""
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    contenido = client.get(reverse("patients:ficha", args=[paciente.pk])).content.decode()

    assert reverse("patients:editar", args=[paciente.pk]) in contenido


def test_la_ficha_de_un_fallecido_no_se_corrige_ni_con_la_url_en_la_mano(client):
    """En solo lectura de verdad: esconder el enlace no basta para quien llega
    con una pestaña abierta de antes."""
    usuario = recepcion(client)
    paciente = PacienteFactory(
        clinic=usuario.clinic, nombre="Rocco", estado=EstadoDelPaciente.FALLECIDO
    )

    abierta = client.get(reverse("patients:editar", args=[paciente.pk]))
    guardada = client.post(
        reverse("patients:editar", args=[paciente.pk]),
        {"nombre": "Otro nombre", "especie": paciente.especie},
    )

    assert abierta.status_code == 302
    assert guardada.status_code == 302
    assert Paciente.de_todas_las_clinicas.get(pk=paciente.pk).nombre == "Rocco"


def test_marcar_por_error_a_quien_no_era_se_puede_deshacer(client):
    """Es lo bastante fácil de hacer, y lo bastante grave, como para que volver
    atrás no dependa de tocar la base de datos a mano."""
    usuario = recepcion(client)
    paciente = PacienteFactory(
        clinic=usuario.clinic, estado=EstadoDelPaciente.FALLECIDO, fecha_de_fallecimiento=AYER
    )
    # Con su Tutor, que es como es un fallecido de verdad: marcar la muerte no
    # cierra ningún Vínculo. Un Paciente sin nadie que responda por él no vuelve
    # a activo —es la regla del ticket 10— y sin esta línea el escenario probaría
    # otra cosa.
    TutorFactory(clinic=usuario.clinic).se_hace_cargo_de(paciente, responsable=True)

    cambiar_el_estado(client, paciente, EstadoDelPaciente.ACTIVO)

    guardado = Paciente.de_todas_las_clinicas.get(pk=paciente.pk)
    assert guardado.esta_activo
    assert guardado.fecha_de_fallecimiento is None
    assert guardado.se_puede_corregir


def test_nadie_fallece_manana(client):
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    respuesta = cambiar_el_estado(
        client, paciente, EstadoDelPaciente.FALLECIDO, fecha_de_fallecimiento=str(MANANA)
    )

    assert respuesta.status_code == 200
    assert not Paciente.de_todas_las_clinicas.get(pk=paciente.pk).esta_fallecido


def test_nadie_fallece_antes_de_nacer(client):
    """La otra mitad del mismo error de tecleo: el año equivocado hacia atrás."""
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic, fecha_de_nacimiento=AYER)

    respuesta = cambiar_el_estado(
        client,
        paciente,
        EstadoDelPaciente.FALLECIDO,
        fecha_de_fallecimiento=str(AYER - datetime.timedelta(days=365)),
    )

    assert respuesta.status_code == 200
    assert not Paciente.de_todas_las_clinicas.get(pk=paciente.pk).esta_fallecido


def test_el_estado_de_un_paciente_de_otra_clinica_no_se_toca(client):
    """No existe para esta consulta, y por eso es 404 y no 403."""
    recepcion(client)
    ajeno = PacienteFactory()

    respuesta = cambiar_el_estado(client, ajeno, EstadoDelPaciente.FALLECIDO)

    assert respuesta.status_code == 404
    assert Paciente.de_todas_las_clinicas.get(pk=ajeno.pk).esta_activo


# --- Lo que enseña una lista ----------------------------------------------


def escenario_de_los_tres_estados(usuario):
    """Un Tutor con un Paciente de cada estado, que es lo que separa las listas."""
    tutor = TutorFactory(clinic=usuario.clinic)
    pacientes = {
        estado: PacienteFactory(clinic=usuario.clinic, nombre=f"Animal {estado}", estado=estado)
        for estado in EstadoDelPaciente
    }
    for paciente in pacientes.values():
        VinculoFactory(tutor=tutor, paciente=paciente)
    return tutor, pacientes


def test_la_ficha_del_tutor_enseña_solo_los_activos_por_defecto(client):
    usuario = recepcion(client)
    tutor, pacientes = escenario_de_los_tres_estados(usuario)

    contenido = pacientes_de(client, tutor).content.decode()

    assert pacientes[EstadoDelPaciente.ACTIVO].nombre in contenido
    assert pacientes[EstadoDelPaciente.INACTIVO].nombre not in contenido
    assert pacientes[EstadoDelPaciente.FALLECIDO].nombre not in contenido


def test_el_filtro_enseña_a_los_que_ya_no_estan(client):
    usuario = recepcion(client)
    tutor, pacientes = escenario_de_los_tres_estados(usuario)

    contenido = pacientes_de(client, tutor, estado="todos").content.decode()

    for paciente in pacientes.values():
        assert paciente.nombre in contenido


def test_el_filtro_puede_pedir_solo_los_fallecidos(client):
    usuario = recepcion(client)
    tutor, pacientes = escenario_de_los_tres_estados(usuario)

    contenido = pacientes_de(client, tutor, estado="fallecidos").content.decode()

    assert pacientes[EstadoDelPaciente.FALLECIDO].nombre in contenido
    assert pacientes[EstadoDelPaciente.ACTIVO].nombre not in contenido


def test_un_filtro_que_no_existe_enseña_lo_de_siempre(client):
    """Una URL escrita a mano no merece una página de fallo: se responde con lo
    que quien miraba esperaba ver."""
    usuario = recepcion(client)
    tutor, pacientes = escenario_de_los_tres_estados(usuario)

    contenido = pacientes_de(client, tutor, estado="cualquier-cosa").content.decode()

    assert pacientes[EstadoDelPaciente.ACTIVO].nombre in contenido
    assert pacientes[EstadoDelPaciente.FALLECIDO].nombre not in contenido


def test_el_que_ya_no_esta_sale_marcado_en_la_lista(client):
    """En «Todos» comparte lista con los vivos, y ahí el nombre solo no dice a
    cuál se puede citar."""
    usuario = recepcion(client)
    tutor, _pacientes = escenario_de_los_tres_estados(usuario)

    contenido = pacientes_de(client, tutor, estado="todos").content.decode()

    assert "Fallecido" in contenido
    assert "Inactivo" in contenido


def test_no_se_anota_la_lectura_de_un_paciente_que_no_se_enseño(client):
    """El Registro dice lo que se sirvió, y un Paciente filtrado no se sirvió."""
    usuario = recepcion(client)
    tutor, pacientes = escenario_de_los_tres_estados(usuario)

    pacientes_de(client, tutor)

    assert anotaciones_sobre(pacientes[EstadoDelPaciente.ACTIVO], Accion.LECTURA).exists()
    assert not anotaciones_sobre(pacientes[EstadoDelPaciente.FALLECIDO], Accion.LECTURA).exists()

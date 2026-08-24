"""Cuando un Paciente cambia de manos: qué se conserva y quién responde ahora.

La información del animal sigue al animal, que es de lo que va el ticket: el
Paciente es el mismo, con la misma ficha y la misma Historia clínica (ADR-0001),
y lo único que cambia es el Vínculo — quién responde por él. Y el de antes no se
borra: se cierra con fecha, porque quién lo trajo hasta marzo es lo que hará
falta el día que alguien pregunte por lo que se le hizo en marzo.

Los tests entran por HTTP como entra recepción, y miran las dos mitades: lo que
la página dice y lo que queda guardado. Lo que la Clínica de al lado no ve está
en `test_aislamiento_por_clinica.py`; aquí solo se comprueba que el cambio de
manos tampoco cruza la frontera.
"""

import datetime

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.audit.models import Accion, RegistroDeAcceso
from apps.patients.estados import EstadoDelPaciente
from apps.patients.models import Paciente
from apps.tutors.models import Vinculo
from apps.tutors.traspaso import traspasar
from tests.factories import PacienteFactory, TutorFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

HOY = datetime.date.today()
AYER = HOY - datetime.timedelta(days=1)
MANANA = HOY + datetime.timedelta(days=1)


def recepcion(client):
    """Quien está en el mostrador: el rol que registra y corrige fichas."""
    usuario = UsuarioFactory(rol="recepcion")
    client.force_login(usuario)
    return usuario


def anotaciones_sobre(objeto, accion):
    return RegistroDeAcceso.de_todas_las_clinicas.filter(
        tipo_de_objeto=objeto._meta.label, identificador=str(objeto.pk), accion=accion
    )


def con_tutor(clinica, **datos):
    """Un Paciente como los de verdad: con alguien que responde por él."""
    paciente = PacienteFactory(clinic=clinica, **datos)
    tutor = TutorFactory(clinic=clinica)
    tutor.se_hace_cargo_de(paciente, responsable=True)
    return paciente, tutor


def cambiar_de_tutor(client, paciente, tutor, fecha=HOY):
    """El cambio de manos desde la página del Paciente, como recepción."""
    return client.post(
        reverse("patients:traspasar", args=[paciente.pk]),
        {"tutor": tutor.pk, "fecha": str(fecha)},
    )


def cerrar(client, vinculo, fecha=HOY):
    return client.post(
        reverse("patients:cerrar_vinculo", args=[vinculo.paciente.pk, vinculo.pk]),
        {"fecha": str(fecha)},
    )


def guardado(vinculo):
    return Vinculo.de_todas_las_clinicas.get(pk=vinculo.pk)


# --- El Vínculo se cierra, no se borra ------------------------------------


def test_cerrar_un_vinculo_lo_deja_con_fecha_y_no_lo_borra():
    """Es toda la decisión del ticket: quién lo trajo antes hace falta después."""
    paciente, responsable = con_tutor(TutorFactory().clinic)
    otra = TutorFactory(clinic=paciente.clinic)
    vinculo = otra.se_hace_cargo_de(paciente)

    vinculo.cerrar(AYER)

    assert guardado(vinculo).fecha_de_cierre == AYER
    assert Vinculo.de_todas_las_clinicas.filter(pk=vinculo.pk).exists()


def test_un_vinculo_cerrado_no_sale_entre_quienes_responden():
    paciente, responsable = con_tutor(TutorFactory().clinic)
    otra = TutorFactory(clinic=paciente.clinic)
    vinculo = otra.se_hace_cargo_de(paciente)

    vinculo.cerrar(AYER)

    assert [v.tutor for v in paciente.quienes_responden] == [responsable]
    assert [v.tutor for v in paciente.quienes_respondieron] == [otra]


def test_cerrar_sin_fecha_toma_la_de_hoy():
    """Es lo que se dice en el mostrador el día que pasa."""
    paciente, _ = con_tutor(TutorFactory().clinic)
    vinculo = TutorFactory(clinic=paciente.clinic).se_hace_cargo_de(paciente)

    vinculo.cerrar()

    assert guardado(vinculo).fecha_de_cierre == HOY


def test_la_base_de_datos_no_admite_un_responsable_con_el_vinculo_cerrado():
    """Sin esto, cerrar y olvidar el cargo dejaría a la clínica llamando a quien
    ya no tiene al animal. No depende de que nadie abra dos pestañas."""
    paciente, responsable = con_tutor(TutorFactory().clinic)

    with pytest.raises(IntegrityError), transaction.atomic():
        Vinculo.de_todas_las_clinicas.filter(paciente=paciente, responsable=True).update(
            fecha_de_cierre=AYER
        )


# --- El cambio de manos, de una vez ---------------------------------------


def test_el_traspaso_cierra_el_vinculo_anterior_y_abre_el_nuevo(client):
    usuario = recepcion(client)
    paciente, antes = con_tutor(usuario.clinic)
    ahora = TutorFactory(clinic=usuario.clinic)

    respuesta = cambiar_de_tutor(client, paciente, ahora, AYER)

    assert respuesta.status_code == 302
    assert paciente.responsable == ahora
    assert [v.tutor for v in paciente.quienes_respondieron] == [antes]
    assert paciente.quienes_respondieron.get().fecha_de_cierre == AYER


def test_el_traspaso_no_deja_ningun_instante_sin_responsable(client):
    """Cerrar uno y abrir otro es una sola operación: si fueran dos, entre una y
    otra habría un animal activo del que no responde nadie."""
    usuario = recepcion(client)
    paciente, _ = con_tutor(usuario.clinic)
    ahora = TutorFactory(clinic=usuario.clinic)

    cambiar_de_tutor(client, paciente, ahora)

    assert paciente.quienes_responden.filter(responsable=True).count() == 1


def test_traspasar_a_quien_ya_era_uno_de_sus_tutores_le_pasa_el_cargo(client):
    """Una pareja que se separa y uno de los dos se queda con el animal: no hay
    Vínculo nuevo que abrir, el que tenía sigue valiendo."""
    usuario = recepcion(client)
    paciente, antes = con_tutor(usuario.clinic)
    la_otra = TutorFactory(clinic=usuario.clinic)
    vinculo = la_otra.se_hace_cargo_de(paciente)

    cambiar_de_tutor(client, paciente, la_otra)

    assert paciente.responsable == la_otra
    assert paciente.quienes_responden.get().pk == vinculo.pk
    assert [v.tutor for v in paciente.quienes_respondieron] == [antes]


def test_traspasar_a_quien_ya_responde_por_el_no_es_un_cambio_de_manos(client):
    """Es una pantalla enviada dos veces, y ni siquiera se ofrece."""
    usuario = recepcion(client)
    paciente, responsable = con_tutor(usuario.clinic)

    respuesta = cambiar_de_tutor(client, paciente, responsable)

    assert respuesta.status_code == 200
    assert paciente.responsable == responsable
    assert not paciente.quienes_respondieron.exists()


def test_el_animal_que_vuelve_a_su_tutor_de_siempre_son_dos_tramos(client):
    """No es una corrección del primero: estuvo con él, no estuvo, y volvió."""
    usuario = recepcion(client)
    paciente, siempre = con_tutor(usuario.clinic)
    otro = TutorFactory(clinic=usuario.clinic)
    cambiar_de_tutor(client, paciente, otro, AYER)

    cambiar_de_tutor(client, paciente, siempre, HOY)

    assert paciente.responsable == siempre
    assert Vinculo.de_todas_las_clinicas.filter(paciente=paciente, tutor=siempre).count() == 2
    # Y en su ficha sale una vez, no una por tramo: son dos Vínculos con el
    # mismo animal, y el animal es uno.
    assert list(siempre.de_quienes_se_hace_cargo) == [paciente]


def test_el_cambio_de_manos_no_puede_ser_del_futuro(client):
    usuario = recepcion(client)
    paciente, antes = con_tutor(usuario.clinic)

    respuesta = cambiar_de_tutor(client, paciente, TutorFactory(clinic=usuario.clinic), MANANA)

    assert respuesta.status_code == 200
    assert paciente.responsable == antes


# --- La información del animal sigue al animal ----------------------------


def test_el_paciente_traspasado_es_el_mismo_paciente(client):
    """Ni ficha nueva ni datos que se quedan atrás: lo único que cambia es quién
    responde por él (ADR-0001)."""
    usuario = recepcion(client)
    paciente, _ = con_tutor(
        usuario.clinic, nombre="Rocco", microchip="900123456789012", color="Negro"
    )

    cambiar_de_tutor(client, paciente, TutorFactory(clinic=usuario.clinic))

    despues = Paciente.de_todas_las_clinicas.get(pk=paciente.pk)
    assert Paciente.de_todas_las_clinicas.count() == 1
    assert (despues.nombre, despues.microchip, despues.color) == ("Rocco", "900123456789012", "Negro")


# --- Nadie se queda sin responsable ---------------------------------------


def test_el_vinculo_del_responsable_de_un_paciente_activo_no_se_cierra():
    """Su ficha no diría a quién llamar: para eso está el cambio de Tutor."""
    paciente, responsable = con_tutor(TutorFactory().clinic)
    vinculo = paciente.vinculo_responsable

    with pytest.raises(ValidationError):
        vinculo.cerrar(HOY)

    assert paciente.responsable == responsable


def test_recepcion_no_puede_cerrar_el_vinculo_del_responsable_por_la_url(client):
    """Esconder el enlace no basta para quien llega con la URL en la mano."""
    usuario = recepcion(client)
    paciente, responsable = con_tutor(usuario.clinic)

    respuesta = cerrar(client, paciente.vinculo_responsable)

    assert respuesta.status_code == 200
    assert paciente.responsable == responsable


def test_el_responsable_de_un_fallecido_si_puede_dejar_de_responder(client):
    """El animal ya no está: nadie va a llamar a nadie, y exigir un responsable
    obligaría a dejar puesto a un Tutor que no tiene nada que ver."""
    usuario = recepcion(client)
    paciente, tutor = con_tutor(usuario.clinic)
    paciente.cambiar_de_estado(EstadoDelPaciente.FALLECIDO, AYER)

    cerrar(client, paciente.vinculo_responsable)

    assert paciente.responsable is None
    assert [v.tutor for v in paciente.quienes_respondieron] == [tutor]


def test_un_paciente_sin_responsable_no_vuelve_a_activo(client):
    """La misma regla por el otro lado: volver a activo dejaría una ficha de
    trabajo sin teléfono al que llamar."""
    usuario = recepcion(client)
    paciente, _ = con_tutor(usuario.clinic)
    paciente.cambiar_de_estado(EstadoDelPaciente.INACTIVO)
    paciente.vinculo_responsable.cerrar(AYER)

    respuesta = client.post(
        reverse("patients:estado", args=[paciente.pk]),
        {"estado": EstadoDelPaciente.ACTIVO, "fecha_de_fallecimiento": ""},
    )

    assert respuesta.status_code == 200
    assert not Paciente.de_todas_las_clinicas.get(pk=paciente.pk).esta_activo


def test_la_ficha_avisa_de_que_no_hay_quien_responda(client):
    usuario = recepcion(client)
    paciente, _ = con_tutor(usuario.clinic)
    paciente.cambiar_de_estado(EstadoDelPaciente.INACTIVO)
    paciente.vinculo_responsable.cerrar(AYER)
    paciente.cambiar_de_estado(EstadoDelPaciente.ACTIVO)

    contenido = client.get(reverse("patients:ficha", args=[paciente.pk])).content.decode()

    assert "Nadie responde por él" in contenido


# --- Las dos fichas cuentan lo que pasó -----------------------------------


def test_la_ficha_del_paciente_enseña_a_los_de_ahora_y_a_los_de_antes(client):
    usuario = recepcion(client)
    paciente, antes = con_tutor(usuario.clinic)
    ahora = TutorFactory(clinic=usuario.clinic, nombre="Ignacio", apellidos="Fuentes")
    cambiar_de_tutor(client, paciente, ahora, AYER)

    contenido = client.get(reverse("patients:ficha", args=[paciente.pk])).content.decode()

    assert "Ignacio Fuentes" in contenido
    assert str(antes) in contenido
    assert reverse("tutors:ficha", args=[antes.pk]) in contenido


def test_la_ficha_del_tutor_anterior_sigue_diciendo_que_el_paciente_fue_suyo(client):
    """Llama preguntando por lo que se le hizo mientras lo tuvo, y la clínica
    tiene que poder decir hasta cuándo fue suyo."""
    usuario = recepcion(client)
    paciente, antes = con_tutor(usuario.clinic, nombre="Rocco")
    cambiar_de_tutor(client, paciente, TutorFactory(clinic=usuario.clinic), AYER)

    contenido = client.get(reverse("tutors:ficha", args=[antes.pk])).content.decode()

    assert "Rocco" in contenido
    assert reverse("patients:ficha", args=[paciente.pk]) in contenido


def test_el_paciente_traspasado_deja_de_salir_entre_los_de_ahora_del_tutor_anterior(client):
    """Quien atiende necesita ver de un vistazo de qué animales se hace cargo
    hoy: uno que entregó no está entre ellos."""
    usuario = recepcion(client)
    paciente, antes = con_tutor(usuario.clinic, nombre="Rocco")
    cambiar_de_tutor(client, paciente, TutorFactory(clinic=usuario.clinic), AYER)

    assert list(antes.de_quienes_se_hace_cargo) == []
    assert [v.paciente for v in antes.de_quienes_se_hizo_cargo] == [paciente]


# --- Todo consta ----------------------------------------------------------


def test_el_cambio_de_manos_queda_en_el_registro_de_acceso(client):
    """A quién se le dejó de cobrar y a quién se le empezó a cobrar es lo que
    habrá que poder demostrar si alguien reclama (ADR-0004)."""
    usuario = recepcion(client)
    paciente, antes = con_tutor(usuario.clinic)
    ahora = TutorFactory(clinic=usuario.clinic)

    cambiar_de_tutor(client, paciente, ahora)

    assert anotaciones_sobre(paciente, Accion.MODIFICACION).get().usuario == usuario
    assert anotaciones_sobre(antes, Accion.MODIFICACION).exists()
    assert anotaciones_sobre(ahora, Accion.MODIFICACION).exists()


def test_cerrar_un_vinculo_desde_el_mostrador_queda_en_el_registro(client):
    usuario = recepcion(client)
    paciente, _ = con_tutor(usuario.clinic)
    otra = TutorFactory(clinic=usuario.clinic)
    vinculo = otra.se_hace_cargo_de(paciente)

    cerrar(client, vinculo, AYER)

    assert anotaciones_sobre(paciente, Accion.MODIFICACION).exists()
    assert anotaciones_sobre(otra, Accion.MODIFICACION).get().usuario == usuario


def test_abrir_el_cambio_de_tutor_deja_constancia_de_lo_que_enseña(client):
    """Dice de qué animal se habla, quién responde ahora por él y, en el
    desplegable, el fichero de Tutores entero."""
    usuario = recepcion(client)
    paciente, antes = con_tutor(usuario.clinic)

    client.get(reverse("patients:traspasar", args=[paciente.pk]))

    assert anotaciones_sobre(paciente, Accion.LECTURA).exists()
    assert anotaciones_sobre(antes, Accion.LECTURA).exists()


def test_la_ficha_anota_la_lectura_de_los_tutores_de_antes(client):
    """Un nombre servido es una lectura aunque el Vínculo esté cerrado."""
    usuario = recepcion(client)
    paciente, antes = con_tutor(usuario.clinic)
    cambiar_de_tutor(client, paciente, TutorFactory(clinic=usuario.clinic), AYER)
    # El Registro no se vacía ni para un test: es inalterable (ADR-0004), así
    # que lo que se mira es que la ficha sume una anotación más.
    hasta_ahora = anotaciones_sobre(antes, Accion.LECTURA).count()

    client.get(reverse("patients:ficha", args=[paciente.pk]))

    assert anotaciones_sobre(antes, Accion.LECTURA).count() == hasta_ahora + 1


# --- Nada de esto cruza la frontera de la Clínica -------------------------


def test_no_se_puede_traspasar_a_un_tutor_de_otra_clinica(client):
    """Ni ofreciéndolo en el desplegable ni enviando su identificador a mano."""
    usuario = recepcion(client)
    paciente, antes = con_tutor(usuario.clinic)
    ajeno = TutorFactory(nombre="Ignacio", apellidos="Fuentes")

    ofrecidos = client.get(reverse("patients:traspasar", args=[paciente.pk])).content.decode()
    respuesta = cambiar_de_tutor(client, paciente, ajeno)

    assert "Ignacio Fuentes" not in ofrecidos
    assert respuesta.status_code == 200
    assert paciente.responsable == antes


def test_cerrar_un_vinculo_de_otra_clinica_da_404(client):
    usuario = recepcion(client)
    ajeno, _ = con_tutor(TutorFactory().clinic)
    vinculo = TutorFactory(clinic=ajeno.clinic).se_hace_cargo_de(ajeno)

    respuesta = cerrar(client, vinculo)

    assert respuesta.status_code == 404
    assert guardado(vinculo).esta_abierto


def test_un_vinculo_ya_cerrado_no_se_vuelve_a_cerrar(client):
    """No es una fila que se edite: fue verdad hasta ese día y ahí se queda."""
    usuario = recepcion(client)
    paciente, _ = con_tutor(usuario.clinic)
    vinculo = TutorFactory(clinic=usuario.clinic).se_hace_cargo_de(paciente)
    vinculo.cerrar(AYER)

    respuesta = cerrar(client, vinculo, HOY)

    assert respuesta.status_code == 404
    assert guardado(vinculo).fecha_de_cierre == AYER


def test_el_traspaso_no_toca_nada_si_algo_falla():
    """Las dos mitades van juntas: o cambia de manos o no cambia nada."""
    paciente, antes = con_tutor(TutorFactory().clinic)

    with pytest.raises(ValidationError):
        traspasar(paciente, antes, HOY)

    assert paciente.responsable == antes
    assert not paciente.quienes_respondieron.exists()

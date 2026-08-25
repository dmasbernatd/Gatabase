"""El Consentimiento de contacto: por dónde acepta el Tutor que se le escriba.

En H1 no se envía nada todavía, y aun así el dato se recoge desde el primer día:
pedirlo retroactivamente a toda la base de clientes es un trabajo que nadie hace.
Lo que sí existe ya es la pregunta que H3 y H4 harán antes de cada envío —
`se_puede_contactar`—, y estos tests son su contrato.

Se prueba por dos puertas distintas a propósito. Por HTTP, lo que recepción hace
y ve: registrar lo que el Tutor dijo, revocarlo, y encontrarlo en la ficha antes
de pensar en llamar. Y por la función a secas, lo que hará el envío: preguntar
sin pantalla, sin petición y sin Clínica activa.
"""

import datetime as dt

import pytest
from django.urls import reverse
from django.utils.formats import date_format

from apps.audit.models import Accion, RegistroDeAcceso
from apps.tutors.consentimiento import Canal, LoQueDijo, como_esta, se_puede_contactar
from apps.tutors.models import Consentimiento
from tests.factories import ClinicaFactory, TutorFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


def como_se_lee(fecha):
    """La fecha como la escribe la plantilla, en el idioma de la aplicación."""
    return date_format(fecha)


def recepcion(client):
    """Quien está en el mostrador: el rol que pregunta y registra lo que le dicen."""
    usuario = UsuarioFactory(rol="recepcion")
    client.force_login(usuario)
    return usuario


# --- La función que consultan H3 y H4 --------------------------------------


def test_lo_que_no_consta_no_autoriza_a_contactar():
    """Un Tutor recién registrado no ha dicho que sí por ningún canal.

    Es la diferencia entre no saber y saber que no, y las dos niegan el envío:
    lo que nadie preguntó tampoco autoriza a nadie.
    """
    tutor = TutorFactory()

    assert not any(se_puede_contactar(tutor, canal) for canal in Canal)


def test_el_consentimiento_es_de_un_canal_y_no_de_todos():
    tutor = TutorFactory()

    tutor.deja_dicho_sobre_el_contacto(Canal.WHATSAPP, otorgado=True)

    assert se_puede_contactar(tutor, Canal.WHATSAPP)
    assert not se_puede_contactar(tutor, Canal.CORREO)
    assert not se_puede_contactar(tutor, Canal.TELEFONO)


def test_tras_una_revocacion_la_funcion_niega_el_contacto():
    """El test que sostiene todo lo demás: revocar tiene que llegar al envío."""
    tutor = TutorFactory()
    tutor.deja_dicho_sobre_el_contacto(Canal.WHATSAPP, otorgado=True)

    tutor.deja_dicho_sobre_el_contacto(Canal.WHATSAPP, otorgado=False)

    assert not se_puede_contactar(tutor, Canal.WHATSAPP)


def test_la_revocacion_no_borra_que_se_habia_otorgado():
    """Queda cuándo se otorgó y cuándo se revocó, no solo el valor de hoy."""
    tutor = TutorFactory()
    tutor.deja_dicho_sobre_el_contacto(Canal.CORREO, otorgado=True, fecha=dt.date(2026, 3, 1))

    tutor.deja_dicho_sobre_el_contacto(Canal.CORREO, otorgado=False, fecha=dt.date(2026, 8, 20))

    dicho = list(Consentimiento.de_todas_las_clinicas.order_by("fecha"))
    assert [(uno.otorgado, uno.fecha) for uno in dicho] == [
        (True, dt.date(2026, 3, 1)),
        (False, dt.date(2026, 8, 20)),
    ]


def test_volver_a_autorizar_despues_de_revocar_vuelve_a_permitir_el_contacto():
    """El Tutor cambia de opinión, y lo último que dijo es lo que vale."""
    tutor = TutorFactory()
    tutor.deja_dicho_sobre_el_contacto(Canal.WHATSAPP, otorgado=True, fecha=dt.date(2026, 3, 1))
    tutor.deja_dicho_sobre_el_contacto(Canal.WHATSAPP, otorgado=False, fecha=dt.date(2026, 4, 1))

    tutor.deja_dicho_sobre_el_contacto(Canal.WHATSAPP, otorgado=True, fecha=dt.date(2026, 5, 1))

    assert se_puede_contactar(tutor, Canal.WHATSAPP)
    assert Consentimiento.de_todas_las_clinicas.count() == 3


def test_dos_declaraciones_del_mismo_dia_se_ordenan_por_orden_de_llegada():
    """Preguntar y desdecirse en la misma visita es lo normal en un mostrador."""
    tutor = TutorFactory()
    hoy = dt.date(2026, 8, 25)
    tutor.deja_dicho_sobre_el_contacto(Canal.TELEFONO, otorgado=True, fecha=hoy)

    tutor.deja_dicho_sobre_el_contacto(Canal.TELEFONO, otorgado=False, fecha=hoy)

    assert not se_puede_contactar(tutor, Canal.TELEFONO)


def test_repetir_lo_que_ya_consta_no_deja_una_declaracion_nueva():
    """Volver a decir que sí no es una decisión: es la misma de siempre.

    Sin esto, cada visita al formulario dejaría una fila más y la historia del
    consentimiento —que es lo que hay que poder enseñar— se llenaría de ruido.
    """
    tutor = TutorFactory()
    tutor.deja_dicho_sobre_el_contacto(Canal.CORREO, otorgado=True)

    assert tutor.deja_dicho_sobre_el_contacto(Canal.CORREO, otorgado=True) is None
    assert Consentimiento.de_todas_las_clinicas.count() == 1


def test_una_declaracion_con_fecha_anterior_se_guarda_aunque_repita_lo_de_hoy():
    """El papel que llega tarde es evidencia, no un duplicado.

    Lo que se calla es repetir lo que vale **hoy**; completar la historia hacia
    atrás no, aunque diga lo mismo: es el trozo que faltaba de cuándo lo dijo.
    """
    tutor = TutorFactory()
    tutor.deja_dicho_sobre_el_contacto(Canal.CORREO, otorgado=True, fecha=dt.date(2026, 8, 1))

    dicho = tutor.deja_dicho_sobre_el_contacto(
        Canal.CORREO, otorgado=True, fecha=dt.date(2026, 3, 1)
    )

    assert dicho is not None
    # Y lo que vale sigue siendo lo último: rellenar hacia atrás no cambia hoy.
    assert se_puede_contactar(tutor, Canal.CORREO)
    assert Consentimiento.de_todas_las_clinicas.count() == 2


def test_preguntar_por_el_consentimiento_no_necesita_clinica_activa():
    """Lo pregunta el envío, que corre en una tarea y no en una petición HTTP.

    Si la respuesta dependiera del manager filtrado, fuera de una petición diría
    siempre que no y ningún Aviso de cita saldría nunca.
    """
    tutor = TutorFactory()
    tutor.deja_dicho_sobre_el_contacto(Canal.WHATSAPP, otorgado=True)

    assert se_puede_contactar(tutor, Canal.WHATSAPP)


def test_el_consentimiento_nace_en_la_clinica_del_tutor():
    tutor = TutorFactory()

    dicho = tutor.deja_dicho_sobre_el_contacto(Canal.WHATSAPP, otorgado=True)

    assert dicho.clinic == tutor.clinic


def test_lo_que_dijo_otro_tutor_no_autoriza_a_contactar_a_este():
    otro = TutorFactory()
    otro.deja_dicho_sobre_el_contacto(Canal.WHATSAPP, otorgado=True)

    tutor = TutorFactory(clinic=otro.clinic)

    assert not se_puede_contactar(tutor, Canal.WHATSAPP)


def test_como_esta_dice_los_tres_canales_aunque_no_conste_ninguno():
    """La ficha enseña los tres siempre: el canal que falta es el que hay que
    preguntar, y esconderlo es lo que deja la pregunta sin hacer para siempre."""
    tutor = TutorFactory()

    assert [estado.canal for estado in como_esta(tutor)] == [canal.value for canal in Canal]


# --- Lo que hace y ve recepción --------------------------------------------


def test_la_ficha_dice_lo_que_consta_de_cada_canal(client):
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)
    tutor.deja_dicho_sobre_el_contacto(Canal.WHATSAPP, otorgado=True, fecha=dt.date(2026, 3, 1))
    tutor.deja_dicho_sobre_el_contacto(Canal.CORREO, otorgado=False, fecha=dt.date(2026, 4, 2))

    contenido = client.get(reverse("tutors:ficha", args=[tutor.pk])).content.decode()

    assert "WhatsApp" in contenido
    # Los tres estados posibles se distinguen en la página, y con su fecha:
    # autorizado, revocado y el que nadie ha preguntado todavía.
    assert como_se_lee(dt.date(2026, 3, 1)) in contenido
    assert como_se_lee(dt.date(2026, 4, 2)) in contenido
    assert "No consta" in contenido


def test_recepcion_registra_el_consentimiento_desde_la_ficha(client):
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)

    client.post(reverse("tutors:consentimiento", args=[tutor.pk]), {Canal.WHATSAPP: LoQueDijo.SI})

    assert se_puede_contactar(tutor, Canal.WHATSAPP)


def test_recepcion_revoca_el_consentimiento_desde_la_ficha(client):
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)
    tutor.deja_dicho_sobre_el_contacto(Canal.WHATSAPP, otorgado=True)

    client.post(reverse("tutors:consentimiento", args=[tutor.pk]), {Canal.WHATSAPP: LoQueDijo.NO})

    assert not se_puede_contactar(tutor, Canal.WHATSAPP)


def test_el_canal_que_no_se_contesta_se_queda_como_estaba(client):
    """Recepción pregunta por lo que puede preguntar, no por los tres a la vez.

    Un canal en blanco no es una revocación: es que de ese no se habló.
    """
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)
    tutor.deja_dicho_sobre_el_contacto(Canal.CORREO, otorgado=True)

    client.post(reverse("tutors:consentimiento", args=[tutor.pk]), {Canal.WHATSAPP: LoQueDijo.SI})

    assert se_puede_contactar(tutor, Canal.CORREO)
    assert Consentimiento.de_todas_las_clinicas.filter(canal=Canal.CORREO).count() == 1


def test_el_formulario_llega_con_lo_que_ya_constaba_puesto(client):
    """Quien abre la página no tiene que acordarse de lo que dijo el Tutor."""
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)
    tutor.deja_dicho_sobre_el_contacto(Canal.CORREO, otorgado=True)

    formulario = client.get(
        reverse("tutors:consentimiento", args=[tutor.pk])
    ).context["formulario"]

    assert formulario[Canal.CORREO].initial == LoQueDijo.SI
    assert formulario[Canal.WHATSAPP].initial == ""


def test_el_cambio_de_consentimiento_queda_en_el_registro_de_acceso(client):
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)

    client.post(reverse("tutors:consentimiento", args=[tutor.pk]), {Canal.WHATSAPP: LoQueDijo.SI})

    assert RegistroDeAcceso.de_todas_las_clinicas.filter(
        usuario=usuario,
        accion=Accion.MODIFICACION,
        tipo_de_objeto="tutors.Tutor",
        identificador=str(tutor.pk),
    ).exists()


def test_abrir_la_pagina_del_consentimiento_queda_como_lectura(client):
    """La página dice de quién se habla, con su nombre: eso es servir un dato
    personal, y consta aunque no se cambie nada (ADR-0004)."""
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)

    client.get(reverse("tutors:consentimiento", args=[tutor.pk]))

    assert RegistroDeAcceso.de_todas_las_clinicas.filter(
        usuario=usuario, accion=Accion.LECTURA, identificador=str(tutor.pk)
    ).exists()


def test_tocar_el_consentimiento_de_un_tutor_de_otra_clinica_da_404(client):
    usuario = recepcion(client)
    ajeno = TutorFactory(clinic=ClinicaFactory())

    respuesta = client.post(
        reverse("tutors:consentimiento", args=[ajeno.pk]), {Canal.WHATSAPP: LoQueDijo.SI}
    )

    assert respuesta.status_code == 404
    assert not se_puede_contactar(ajeno, Canal.WHATSAPP)


def test_la_pagina_del_consentimiento_ensena_todo_lo_que_el_tutor_ha_dicho(client):
    """«Queda registro» solo significa algo si alguien lo puede mirar.

    Lo que hay que poder enseñar si un Tutor reclama por un mensaje no es qué
    acepta hoy: es que el día que se le escribió lo aceptaba.
    """
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)
    tutor.deja_dicho_sobre_el_contacto(Canal.WHATSAPP, otorgado=True, fecha=dt.date(2026, 3, 1))
    tutor.deja_dicho_sobre_el_contacto(Canal.WHATSAPP, otorgado=False, fecha=dt.date(2026, 6, 4))

    contenido = client.get(reverse("tutors:consentimiento", args=[tutor.pk])).content.decode()

    # Las dos, la vieja incluida: la que ya no vale es justamente la que prueba
    # que el mensaje de abril salió con consentimiento.
    assert como_se_lee(dt.date(2026, 3, 1)) in contenido
    assert como_se_lee(dt.date(2026, 6, 4)) in contenido

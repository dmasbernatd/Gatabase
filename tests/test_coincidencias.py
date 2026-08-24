"""Detección de coincidencias: la ficha que se va a crear puede ser una que ya existe.

Recepción está a punto de registrar a alguien que ya está registrado —el mismo
Tutor con el RUT tecleado de otra forma, el animal que trajo su hermana el año
pasado— y el sistema se lo pone delante **antes** de guardar. Es la prevención
barata que evita la mayoría de las fichas duplicadas, dado que fusionar dos
fichas se pospone a propósito.

Los tests entran por HTTP porque la funcionalidad es lo que se ve mientras se
escribe: qué avisa el fragmento que devuelve la detección, adónde enlaza, y que
no impide guardar cuando quien está delante insiste.

Lo que ocurre **al guardar** un RUT o un microchip repetidos se prueba donde
siempre —`test_fichas_de_tutor.py` y `test_microchip_e_identificacion.py`—: ahí
no se trata de un parecido sino de una restricción de la base de datos, y sigue
sin poder guardarse (ADR-0001).
"""

import pytest
from django.urls import reverse

from apps.coincidencias import FormularioQueSeParece
from apps.audit.models import Accion, RegistroDeAcceso
from apps.patients.catalogo import Especie
from apps.patients.models import Paciente
from apps.tutors.models import Tutor
from tests.factories import ClinicaFactory, PacienteFactory, TutorFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

# Un RUT de verdad, tal como se guarda y tal como se dicta.
RUT_GUARDADO = "123456785"
RUT_ESCRITO = "12.345.678-5"

# Un microchip de quince dígitos, como el que trae el lector de un tirón.
CHIP = "900123456789012"

# El número de una casa, tal como se guarda: una familia lo comparte.
TELEFONO = "+56987654321"


def recepcion(client, clinica=None):
    """Quien está en el mostrador registrando la ficha."""
    usuario = UsuarioFactory(rol="recepcion", **({"clinic": clinica} if clinica else {}))
    client.force_login(usuario)
    return usuario


def coincidencias_de_tutor(client, **escrito):
    """Lo que la detección responde a una ficha de Tutor a medio escribir."""
    return client.get(reverse("tutors:coincidencias"), escrito).content.decode()


def anotaciones_sobre(ficha):
    return RegistroDeAcceso.de_todas_las_clinicas.filter(
        tipo_de_objeto=type(ficha)._meta.label,
        identificador=str(ficha.pk),
        accion=Accion.LECTURA,
    )


def coincidencias_de_paciente(client, **escrito):
    """Lo mismo para la ficha de un Paciente."""
    return client.get(reverse("patients:coincidencias"), escrito).content.decode()


# --- El RUT de un Tutor que ya está ---------------------------------------


def test_al_escribir_un_rut_que_ya_esta_avisa_y_enlaza_a_la_ficha(client):
    usuario = recepcion(client)
    ya_registrada = TutorFactory(
        clinic=usuario.clinic, nombre="Camila", apellidos="Rojas", rut=RUT_GUARDADO
    )

    aviso = coincidencias_de_tutor(client, rut=RUT_ESCRITO)

    assert "Camila Rojas" in aviso
    assert reverse("tutors:ficha", args=[ya_registrada.pk]) in aviso
    # Solo el hueco de los avisos: es lo que htmx sustituye sin recargar nada, y
    # nada de esto ha guardado ninguna ficha.
    assert "<html" not in aviso
    assert not Tutor.de_todas_las_clinicas.filter(nombre="").exists()


# --- El teléfono de una familia -------------------------------------------


def test_al_escribir_un_telefono_que_ya_esta_ensena_a_quien_lo_tiene(client):
    """Una familia comparte número, así que esto no es un error: es lo que hay
    que poner delante por si son la misma persona registrada dos veces."""
    usuario = recepcion(client)
    ya_registrada = TutorFactory(
        clinic=usuario.clinic, nombre="Camila", apellidos="Rojas", telefono="+56987654321"
    )

    aviso = coincidencias_de_tutor(client, telefono="9 8765 4321")

    assert "Camila Rojas" in aviso
    assert reverse("tutors:ficha", args=[ya_registrada.pk]) in aviso


def test_el_telefono_ensena_a_todos_los_que_lo_comparten(client):
    """Son las fichas entre las que hay que elegir, y elegir la primera de dos
    sin decir que había otra es peor que no avisar."""
    usuario = recepcion(client)
    for apellidos in ("Rojas", "Rojas Pizarro"):
        TutorFactory(clinic=usuario.clinic, apellidos=apellidos, telefono="+56987654321")

    aviso = coincidencias_de_tutor(client, telefono="+56987654321")

    assert "Rojas Pizarro" in aviso
    assert aviso.count("<a ") == 2


# --- Mientras se escribe, sin guardar --------------------------------------


def test_el_alta_de_tutor_pregunta_mientras_se_escribe(client):
    """Sin guardar y sin recargar: la ficha que ya existe tiene que estar
    delante **antes** de que haya dos."""
    recepcion(client)

    pagina = client.get(reverse("tutors:crear")).content.decode()

    assert reverse("tutors:coincidencias") in pagina
    assert "delay:" in pagina
    # El hueco donde se pintan los avisos existe en la página, o htmx no
    # tendría dónde dejarlos.
    assert f'id="{FormularioQueSeParece.CAJA}"' in pagina


def test_corregir_una_ficha_no_pregunta_por_ella_misma(client):
    """Un Tutor no se parece a sí mismo: tocarle una letra al apellido no puede
    avisar de que su RUT ya es suyo."""
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic, rut=RUT_GUARDADO)

    pagina = client.get(reverse("tutors:editar", args=[tutor.pk])).content.decode()
    aviso = client.get(
        reverse("tutors:coincidencias", args=[tutor.pk]), {"rut": RUT_ESCRITO}
    ).content.decode()

    assert reverse("tutors:coincidencias", args=[tutor.pk]) in pagina
    assert "<a " not in aviso


# --- El microchip de un Paciente que ya está ------------------------------


def test_al_escribir_un_microchip_que_ya_esta_avisa_y_enlaza_a_la_ficha(client):
    """El mismo número es el mismo animal, y registrarlo dos veces parte su
    Historia clínica en dos (ADR-0001)."""
    usuario = recepcion(client)
    ya_registrado = PacienteFactory(clinic=usuario.clinic, nombre="Rocco", microchip=CHIP)

    aviso = coincidencias_de_paciente(client, microchip="900 123 456 789 012")

    assert "Rocco" in aviso
    assert reverse("patients:ficha", args=[ya_registrado.pk]) in aviso


def test_el_microchip_de_otra_clinica_no_es_una_coincidencia(client):
    """El chip identifica al animal en todo Chile, pero cada Clínica tiene su
    propio Paciente: detectarlo sería cruzar datos entre tenants (ADR-0001)."""
    recepcion(client)
    PacienteFactory(clinic=ClinicaFactory(), nombre="Rocco", microchip=CHIP)

    assert "Rocco" not in coincidencias_de_paciente(client, microchip=CHIP)


def test_el_alta_de_paciente_pregunta_mientras_se_escribe(client):
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)

    pagina = client.get(reverse("patients:crear", args=[tutor.pk])).content.decode()

    assert reverse("patients:coincidencias") in pagina
    assert f'id="{FormularioQueSeParece.CAJA}"' in pagina


# --- Los Pacientes que ese Tutor ya tiene ---------------------------------


def test_el_alta_ensena_los_pacientes_que_el_tutor_ya_tiene(client):
    """El animal que se va a registrar puede ser uno de los suyos con el nombre
    escrito de otra forma, y aquí no hay que buscar nada: se sabe de quién va a
    ser la ficha antes de teclear la primera letra."""
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)
    ya_registrado = PacienteFactory(clinic=usuario.clinic, nombre="Rocco", especie=Especie.GATO)
    tutor.se_hace_cargo_de(ya_registrado, responsable=True)

    pagina = client.get(reverse("patients:crear", args=[tutor.pk])).content.decode()

    assert "Rocco" in pagina
    assert "gato" in pagina
    assert reverse("patients:ficha", args=[ya_registrado.pk]) in pagina


def test_el_alta_para_un_tutor_sin_pacientes_no_ensena_ninguno(client):
    """Es lo normal: un Tutor se registra casi siempre para registrar a un
    animal, y un aviso vacío se acaba mirando como parte del decorado."""
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)

    pagina = client.get(reverse("patients:crear", args=[tutor.pk])).content.decode()

    assert "Ya responde por" not in pagina


# --- El aviso no impide guardar -------------------------------------------


def test_el_telefono_compartido_no_impide_registrar_al_segundo_tutor(client):
    """Una familia comparte número. Bloquear ahí obligaría a recepción a
    inventarse un teléfono para el segundo, y un dato falso no se distingue de
    uno bueno."""
    usuario = recepcion(client)
    TutorFactory(clinic=usuario.clinic, nombre="Camila", apellidos="Rojas", telefono=TELEFONO)

    respuesta = client.post(
        reverse("tutors:crear"),
        {"nombre": "Ignacio", "apellidos": "Rojas", "telefono": TELEFONO},
        follow=True,
    )

    assert Tutor.de_todas_las_clinicas.filter(telefono=TELEFONO).count() == 2
    # Y se guardó **avisando**: la ficha de la otra queda enlazada por si eran
    # la misma persona registrada dos veces.
    assert "Camila Rojas" in respuesta.content.decode()


def test_un_paciente_con_nombre_parecido_al_de_la_casa_se_registra_igual(client):
    """Dos animales de la misma familia pueden llamarse parecido, y la ficha que
    la página pone delante es un aviso: quien está en el mostrador decide."""
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)
    tutor.se_hace_cargo_de(
        PacienteFactory(clinic=usuario.clinic, nombre="Rocco"), responsable=True
    )

    client.post(
        reverse("patients:crear", args=[tutor.pk]),
        {"nombre": "Roco", "especie": Especie.PERRO},
    )

    suyos = {str(paciente) for paciente in tutor.de_quienes_se_hace_cargo}

    assert suyos == {"Rocco", "Roco"}


# --- Ninguna coincidencia con otra Clínica --------------------------------


def test_el_rut_de_otra_clinica_no_es_una_coincidencia(client):
    """Dos Clínicas atienden a la misma persona sin saber la una de la otra, y
    avisar aquí sería decir que esa persona existe en otra parte (ADR-0003)."""
    recepcion(client)
    TutorFactory(clinic=ClinicaFactory(), nombre="Camila", apellidos="Rojas", rut=RUT_GUARDADO)

    assert "Camila Rojas" not in coincidencias_de_tutor(client, rut=RUT_ESCRITO)


# --- Lo que queda anotado --------------------------------------------------


def test_avisar_de_una_coincidencia_deja_constancia_de_la_lectura(client):
    """El aviso dice el nombre de la otra ficha y enlaza a ella: quien lo lee ha
    visto un dato personal suyo sin haber abierto nada (ADR-0004)."""
    usuario = recepcion(client)
    ya_registrada = TutorFactory(clinic=usuario.clinic, rut=RUT_GUARDADO)

    coincidencias_de_tutor(client, rut=RUT_ESCRITO)

    assert anotaciones_sobre(ya_registrada).get().usuario == usuario


def test_una_ficha_a_medio_escribir_no_anota_nada(client):
    """La detección corre a cada pocas teclas, así que lo que no llegó a nombrar
    a nadie no puede dejar rastro: un RUT sin terminar no es el de nadie."""
    usuario = recepcion(client)
    TutorFactory(clinic=usuario.clinic, rut=RUT_GUARDADO)

    coincidencias_de_tutor(client, rut="12.345.6")

    assert not RegistroDeAcceso.de_todas_las_clinicas.exists()


def test_corregir_un_paciente_no_pregunta_por_el_mismo(client):
    """Tocarle una letra al nombre no puede avisar de que su chip ya es suyo."""
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic, microchip=CHIP)

    pagina = client.get(reverse("patients:editar", args=[paciente.pk])).content.decode()
    aviso = client.get(
        reverse("patients:coincidencias", args=[paciente.pk]), {"microchip": CHIP}
    ).content.decode()

    assert reverse("patients:coincidencias", args=[paciente.pk]) in pagina
    assert "<a " not in aviso


def test_la_deteccion_no_guarda_ninguna_ficha(client):
    """Preguntar a quién se parece esto no es guardarlo: la detección corre con
    la ficha a medio escribir y no puede dejar nada registrado."""
    usuario = recepcion(client)
    TutorFactory(clinic=usuario.clinic, rut=RUT_GUARDADO)
    cuantos = Tutor.de_todas_las_clinicas.count()

    coincidencias_de_tutor(client, nombre="Camila", rut=RUT_ESCRITO, telefono=TELEFONO)
    coincidencias_de_paciente(client, nombre="Rocco", especie=Especie.PERRO, microchip=CHIP)

    assert Tutor.de_todas_las_clinicas.count() == cuantos
    assert not Paciente.de_todas_las_clinicas.exists()


def test_el_formulario_rechazado_solo_anota_la_ficha_que_nombra(client):
    """La página que vuelve trae el aviso del RUT al lado de su campo, y nada
    más: el hueco de los avisos vuelve vacío. Lo que no se llegó a servir no se
    anota (ADR-0004)."""
    usuario = recepcion(client)
    la_del_rut = TutorFactory(clinic=usuario.clinic, rut=RUT_GUARDADO, telefono="+56911111111")
    la_del_telefono = TutorFactory(clinic=usuario.clinic, telefono=TELEFONO)

    client.post(
        reverse("tutors:crear"),
        {"nombre": "Camila", "rut": RUT_ESCRITO, "telefono": TELEFONO},
    )

    assert anotaciones_sobre(la_del_rut).exists()
    assert not anotaciones_sobre(la_del_telefono).exists()

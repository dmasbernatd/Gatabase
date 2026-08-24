"""La caja única del mostrador: encontrar al Paciente con lo primero que haya a mano.

Recepción está al teléfono con un Tutor y escribe lo que tiene delante — un
nombre, un teléfono, un RUT o el número que trae el lector de chips — sin elegir
antes en qué campo busca. Es la funcionalidad que hace que el sistema gane al
archivador, así que los tests entran por HTTP y miran lo que la página enseña.

Lo que el Registro de acceso guarda de todo esto se comprueba también aquí, y no
en `test_registro_de_acceso.py`, porque la decisión es de esta pantalla: una
búsqueda que se repinta a cada tecla no puede anotar un acceso por resultado.
"""

import html as marcado
import re

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.audit.models import EL_CONJUNTO, Accion, RegistroDeAcceso
from apps.patients.catalogo import Especie
from apps.patients.estados import EstadoDelPaciente
from apps.patients.models import Paciente
from apps.tutors.models import Tutor, Vinculo
from apps.tutors.rut import digito_verificador
from tests.factories import (
    ClinicaFactory,
    PacienteFactory,
    TutorFactory,
    UsuarioFactory,
    VinculoFactory,
)

pytestmark = pytest.mark.django_db

MARCADO = re.compile(r"<[^>]*>", re.S)


def recepcion(client, clinica=None):
    """Quien está en el mostrador: el rol que atiende el teléfono."""
    usuario = UsuarioFactory(rol="recepcion", **({"clinic": clinica} if clinica else {}))
    client.force_login(usuario)
    return usuario


def buscar(client, escrito, **cabeceras):
    return client.get(reverse("buscar"), {"q": escrito}, **cabeceras)


def _sin_marcado(fragmento):
    return " ".join(marcado.unescape(MARCADO.sub(" ", fragmento)).split())


def resultados(respuesta):
    """Lo que dice cada fila de resultados, ya sin marcado."""
    cuerpo = re.search(r"<tbody.*?</tbody>", respuesta.content.decode(), re.S)
    assert cuerpo, "La página no trae ninguna tabla de resultados"
    filas = re.findall(r"<tr\b.*?</tr>", cuerpo.group(), re.S)
    return [texto for fila in filas if (texto := _sin_marcado(fila))]


def encuentra(respuesta, nombre):
    return any(nombre in fila for fila in resultados(respuesta))


def con_tutor(nombre="Camila", apellidos="Rojas", clinica=None, paciente="Rocco", **datos):
    """Un Paciente con quien responde por él, que es como llegan al mostrador."""
    clinica = clinica or ClinicaFactory()
    tutor = TutorFactory(clinic=clinica, nombre=nombre, apellidos=apellidos, **datos)
    animal = PacienteFactory(clinic=clinica, nombre=paciente)
    VinculoFactory(tutor=tutor, paciente=animal, responsable=True)
    return tutor, animal


def anotaciones_sobre(objeto):
    return RegistroDeAcceso.de_todas_las_clinicas.filter(
        tipo_de_objeto=objeto._meta.label, identificador=str(objeto.pk)
    )


def anotaciones_del_conjunto(modelo):
    return RegistroDeAcceso.de_todas_las_clinicas.filter(
        tipo_de_objeto=modelo._meta.label, identificador=EL_CONJUNTO
    )


# --- Una sola caja para todo ----------------------------------------------


def test_la_pagina_ofrece_una_sola_caja_de_busqueda(client):
    recepcion(client)

    contenido = client.get(reverse("buscar")).content.decode()

    assert contenido.count('type="search"') == 1


def test_encuentra_al_paciente_por_su_nombre(client):
    usuario = recepcion(client)
    con_tutor(clinica=usuario.clinic, paciente="Rocco")

    assert encuentra(buscar(client, "rocco"), "Rocco")


def test_encuentra_al_paciente_por_el_nombre_de_su_tutor(client):
    usuario = recepcion(client)
    con_tutor(clinica=usuario.clinic, nombre="Camila", apellidos="Rojas", paciente="Rocco")

    assert encuentra(buscar(client, "camila rojas"), "Rocco")


def test_no_lo_encuentra_si_falta_una_de_las_palabras(client):
    usuario = recepcion(client)
    con_tutor(clinica=usuario.clinic, nombre="Camila", apellidos="Pérez", paciente="Rocco")

    assert not encuentra(buscar(client, "camila rojas"), "Rocco")


@pytest.mark.parametrize(
    "escrito",
    ["+56 9 8765 4321", "56987654321", "987654321", "09 8765 4321", "8765 4321"],
)
def test_encuentra_por_el_telefono_escrito_de_cualquier_forma(client, escrito):
    usuario = recepcion(client)
    con_tutor(clinica=usuario.clinic, telefono="+56987654321", paciente="Rocco")

    assert encuentra(buscar(client, escrito), "Rocco")


@pytest.mark.parametrize("escrito", ["12.345.678-5", "12345678-5", "123456785", "12345678"])
def test_encuentra_por_el_rut_con_puntos_y_sin_ellos(client, escrito):
    usuario = recepcion(client)
    con_tutor(clinica=usuario.clinic, rut="12.345.678-5", paciente="Rocco")

    assert encuentra(buscar(client, escrito), "Rocco")


@pytest.mark.parametrize("escrito", ["900123456789012", "900 123 456 789 012", "900123456"])
def test_encuentra_por_el_microchip_de_corrido_y_en_grupos(client, escrito):
    usuario = recepcion(client)
    tutor, paciente = con_tutor(clinica=usuario.clinic, paciente="Rocco")
    paciente.microchip = "900123456789012"
    paciente.save()

    assert encuentra(buscar(client, escrito), "Rocco")


def test_un_rut_entero_trae_a_esa_persona_y_no_a_quien_lo_lleva_dentro(client):
    """Dictado entero, el RUT identifica a uno solo.

    Es lo que separa la búsqueda rápida —una igualdad que el índice resuelve— de
    un barrido por dentro del campo: «1234567-K» está contenido en un RUT de
    ocho dígitos que empiece igual, y ese no es el Tutor por el que preguntan.
    """
    usuario = recepcion(client)
    corto = "1234567" + digito_verificador("1234567")
    largo = corto + digito_verificador(corto)
    con_tutor(clinica=usuario.clinic, rut=corto, paciente="Rocco")
    con_tutor(clinica=usuario.clinic, rut=largo, paciente="Nala")

    respuesta = buscar(client, corto)

    assert encuentra(respuesta, "Rocco")
    assert not encuentra(respuesta, "Nala")


def test_un_numero_no_se_busca_por_dentro_de_los_nombres(client):
    """Lo escrito es un número dictado o es un nombre, y no las dos cosas.

    Ningún campo por el que se busca guarda números dentro del nombre, así que
    buscar también por ahí solo traería al Tutor cuyo correo lleva esos dígitos
    por casualidad — una fila que recepción tendría que descartar leyéndola.
    """
    usuario = recepcion(client)
    con_tutor(clinica=usuario.clinic, telefono="+56987654321", paciente="Rocco")
    con_tutor(clinica=usuario.clinic, email="tutor98765@correo.example", paciente="Nala")

    respuesta = buscar(client, "98765")

    assert encuentra(respuesta, "Rocco")
    assert not encuentra(respuesta, "Nala")


# --- Tolerante a como se teclea -------------------------------------------


@pytest.mark.parametrize("escrito", ["muñoz", "MUÑOZ", "munoz", "MUNOZ"])
def test_no_distingue_tildes_ni_mayusculas_en_el_tutor(client, escrito):
    usuario = recepcion(client)
    con_tutor(clinica=usuario.clinic, nombre="Íñigo", apellidos="Muñoz", paciente="Rocco")

    assert encuentra(buscar(client, escrito), "Rocco")


@pytest.mark.parametrize("escrito", ["ñoño", "nono", "ÑOÑO"])
def test_no_distingue_tildes_ni_mayusculas_en_el_paciente(client, escrito):
    usuario = recepcion(client)
    con_tutor(clinica=usuario.clinic, paciente="Ñoño")

    assert encuentra(buscar(client, escrito), "Ñoño")


def test_el_fichero_de_tutores_tambien_tolera_las_tildes(client):
    """La misma mecánica sirve a las dos búsquedas, y aquí se ve."""
    usuario = recepcion(client)
    TutorFactory(clinic=usuario.clinic, nombre="Íñigo", apellidos="Muñoz")

    contenido = client.get(reverse("tutors:lista"), {"q": "inigo munoz"}).content.decode()

    assert "Muñoz" in contenido


# --- Lo que hace falta para confirmar por voz ------------------------------


def test_el_resultado_dice_especie_tutor_responsable_y_telefono(client):
    usuario = recepcion(client)
    tutor, paciente = con_tutor(
        clinica=usuario.clinic,
        nombre="Camila",
        apellidos="Rojas",
        telefono="+56987654321",
        paciente="Rocco",
    )
    paciente.especie = Especie.GATO
    paciente.save()

    fila = next(fila for fila in resultados(buscar(client, "rocco")) if "Rocco" in fila)

    assert "gato" in fila
    assert "Camila Rojas" in fila
    assert "+56987654321" in fila


def test_los_fallecidos_y_los_inactivos_salen_marcados_y_no_escondidos(client):
    usuario = recepcion(client)
    for nombre, estado in (("Rocco", EstadoDelPaciente.FALLECIDO),
                           ("Roco", EstadoDelPaciente.INACTIVO)):
        _, paciente = con_tutor(clinica=usuario.clinic, paciente=nombre)
        paciente.cambiar_de_estado(estado)

    filas = resultados(buscar(client, "roc"))

    assert any("Rocco" in fila and "Fallecido" in fila for fila in filas)
    assert any("Roco" in fila and "nactivo" in fila for fila in filas)


def test_al_fallecido_no_lo_deja_fuera_una_busqueda_amplia(client):
    """El corte de la lista no puede tener preferencias.

    Ordenar «los vivos primero» parece de sentido común y esconde justo a quien
    la casilla del ticket protege: como la lista se corta, el fallecido se cae
    siempre que la búsqueda es amplia. Aquí hay más coincidencias de las que
    caben y el fallecido sigue saliendo, porque el orden es alfabético y no
    sabe de estados.
    """
    usuario = recepcion(client)
    _, muerto = con_tutor(clinica=usuario.clinic, paciente="Rocco 00")
    muerto.cambiar_de_estado(EstadoDelPaciente.FALLECIDO)
    for numero in range(1, 26):
        con_tutor(clinica=usuario.clinic, paciente=f"Rocco {numero:02d}")

    respuesta = buscar(client, "rocco")

    assert encuentra(respuesta, "Rocco 00")
    assert "afine" in _sin_marcado(respuesta.content.decode()).lower()


def test_el_tutor_que_dejo_de_responder_ya_no_lo_encuentra(client):
    """La caja busca a quien responde hoy, que es quien está al teléfono.

    De quién fue el animal antes no se pierde —lo dicen las dos fichas— pero no
    es por donde se le busca: el resultado diría un Tutor responsable que no es
    el que se acaba de teclear.
    """
    usuario = recepcion(client)
    tutor, paciente = con_tutor(clinica=usuario.clinic, nombre="Camila", paciente="Rocco")
    otro = TutorFactory(clinic=usuario.clinic, nombre="Josefa", apellidos="Díaz")
    otro.se_hace_cargo_de(paciente, responsable=True)
    paciente.quienes_responden.get(tutor=tutor).cerrar()

    assert not encuentra(buscar(client, "camila"), "Rocco")
    assert encuentra(buscar(client, "josefa"), "Rocco")


# --- Ningún resultado de otra Clínica --------------------------------------


def test_no_encuentra_al_paciente_de_otra_clinica(client):
    recepcion(client)
    con_tutor(paciente="Rocco")

    assert not encuentra(buscar(client, "rocco"), "Rocco")


def test_no_encuentra_al_paciente_por_el_tutor_de_otra_clinica(client):
    recepcion(client)
    con_tutor(nombre="Camila", apellidos="Rojas", paciente="Rocco")

    assert not encuentra(buscar(client, "camila rojas"), "Rocco")


# --- Lo que queda anotado --------------------------------------------------


def test_la_busqueda_no_anota_una_lectura_por_cada_resultado(client):
    usuario = recepcion(client)
    tutor, paciente = con_tutor(clinica=usuario.clinic, paciente="Rocco")

    buscar(client, "rocco")

    assert not anotaciones_sobre(paciente).exists()
    assert not anotaciones_sobre(tutor).exists()


def test_la_busqueda_anota_que_se_consulto_el_conjunto(client):
    usuario = recepcion(client)
    con_tutor(clinica=usuario.clinic, paciente="Rocco")

    buscar(client, "rocco")

    assert anotaciones_del_conjunto(Paciente).filter(accion=Accion.LECTURA).count() == 1
    assert anotaciones_del_conjunto(Tutor).filter(accion=Accion.LECTURA).count() == 1


def test_la_caja_vacia_no_anota_nada(client):
    recepcion(client)

    client.get(reverse("buscar"))

    assert not RegistroDeAcceso.de_todas_las_clinicas.exists()


def test_abrir_la_ficha_desde_un_resultado_si_anota_la_lectura(client):
    usuario = recepcion(client)
    _, paciente = con_tutor(clinica=usuario.clinic, paciente="Rocco")

    client.get(reverse("patients:ficha", args=[paciente.pk]))

    assert anotaciones_sobre(paciente).filter(accion=Accion.LECTURA).exists()


# --- Incremental, y sin recargar la página ---------------------------------


def test_htmx_recibe_solo_los_resultados(client):
    usuario = recepcion(client)
    con_tutor(clinica=usuario.clinic, paciente="Rocco")

    respuesta = buscar(client, "rocco", HTTP_HX_REQUEST="true")

    assert encuentra(respuesta, "Rocco")
    assert b"<html" not in respuesta.content


def test_la_caja_se_repinta_a_si_misma_mientras_se_escribe(client):
    recepcion(client)

    contenido = client.get(reverse("buscar")).content.decode()

    assert "hx-get" in contenido
    assert "delay:" in contenido


# --- Rápida con el volumen de una clínica de verdad ------------------------


def _clinica_llena(clinica, cuantos):
    """Una Clínica con Pacientes y Tutores como para que buscar cueste algo."""
    tutores = Tutor.de_todas_las_clinicas.bulk_create(
        Tutor(
            clinic=clinica,
            nombre=f"Tutor {numero}",
            apellidos=f"Apellido {numero}",
            telefono=f"+5692{numero:07d}",
        )
        for numero in range(cuantos)
    )
    pacientes = Paciente.de_todas_las_clinicas.bulk_create(
        Paciente(clinic=clinica, nombre=f"Animal {numero}", especie=Especie.PERRO)
        for numero in range(cuantos)
    )
    Vinculo.de_todas_las_clinicas.bulk_create(
        Vinculo(clinic=clinica, tutor=tutor, paciente=paciente, responsable=True)
        for tutor, paciente in zip(tutores, pacientes)
    )


def _consultas_al_buscar(client, escrito):
    with CaptureQueriesContext(connection) as capturadas:
        buscar(client, escrito)
    return len(capturadas)


def test_el_numero_de_consultas_no_crece_con_los_resultados(client):
    """Un `N+1` al pintar la tabla pasaría entero y en verde sin este test.

    Cada fila dice quién responde por el animal, y preguntarlo fila a fila es
    exactamente el fallo que no se nota con tres Pacientes de prueba.
    """
    usuario = recepcion(client)
    con_tutor(clinica=usuario.clinic, paciente="Animal único")
    una = _consultas_al_buscar(client, "animal")

    _clinica_llena(usuario.clinic, 60)
    muchas = _consultas_al_buscar(client, "animal")

    assert muchas == una


def test_encuentra_con_el_volumen_de_una_clinica_de_verdad(client):
    usuario = recepcion(client)
    _clinica_llena(usuario.clinic, 800)
    con_tutor(clinica=usuario.clinic, nombre="Camila", apellidos="Rojas", paciente="Rocco")

    respuesta = buscar(client, "rocco")

    assert encuentra(respuesta, "Rocco")
    assert len(resultados(respuesta)) == 1


def test_una_busqueda_demasiado_amplia_no_trae_la_clinica_entera(client):
    """Con la caja a medio escribir, lo que hace falta es responder rápido.

    Se enseña un puñado y se dice que hay más, en vez de contar y paginar: el
    `COUNT(*)` de la consulta completa se paga en cada tecla y no lo mira nadie.
    """
    usuario = recepcion(client)
    _clinica_llena(usuario.clinic, 800)

    respuesta = buscar(client, "animal")

    assert len(resultados(respuesta)) <= 20
    assert "afine" in _sin_marcado(respuesta.content.decode()).lower()

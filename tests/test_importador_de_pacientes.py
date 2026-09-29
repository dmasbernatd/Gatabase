"""Importar la planilla con la que una clínica lleva hoy sus animales.

Es la segunda mitad de la migración y la difícil: la planilla de animales
identifica al dueño por un nombre escrito a mano, no por un identificador, así
que lo que estos tests miran una y otra vez es **a quién quedó vinculado** cada
Paciente — y qué pasa cuando eso no se puede saber sin adivinar.

Se entra por HTTP como entra el admin, igual que en `test_importador_de_tutores.py`:
sube el archivo, mira qué le dice la página que va a pasar, y solo entonces
confirma. Lo que ese archivo tiene de CSV —separador, codificación, nombres de
columna— se prueba aparte, en `test_planilla.py`.
"""

import csv
import io

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import Accion, RegistroDeAcceso
from apps.imports.models import Importacion, LoQueSeImporta
from apps.patients.catalogo import Especie
from apps.patients.models import Paciente, Sexo
from apps.tutors.derechos import anonimizar
from apps.tutors.models import Tutor, Vinculo
from apps.tutors.rut import formateado
from apps.tutors.traspaso import traspasar
from tests.factories import (
    ClinicaFactory,
    PacienteFactory,
    TutorFactory,
    UsuarioFactory,
    VinculoFactory,
    rut_de_prueba,
)

pytestmark = pytest.mark.django_db

CABECERA = (
    "nombre,especie,raza,sexo,fecha_de_nacimiento,color,microchip,"
    "rut_tutor,telefono_tutor,tutor"
)

CHIP = "900123456789012"
OTRO_CHIP = "900123456789013"


def admin(client, clinica=None):
    """Quien sube la planilla: la importación es de administración, no del mostrador."""
    usuario = UsuarioFactory(rol="admin", **({"clinic": clinica} if clinica else {}))
    client.force_login(usuario)
    return usuario


def fila(
    nombre="Fido",
    especie="perro",
    raza="",
    sexo="",
    nacimiento="",
    color="",
    chip="",
    rut="",
    telefono="",
    tutor="",
):
    """Una fila de la planilla de Pacientes, en el orden de `CABECERA`."""
    return ",".join(
        [nombre, especie, raza, sexo, nacimiento, color, chip, rut, telefono, tutor]
    )


def planilla(*filas, cabecera=CABECERA):
    """Un CSV subido, tal como llega del navegador."""
    return io.BytesIO(("\n".join([cabecera, *filas]) + "\n").encode("utf-8"))


def subir(client, archivo, nombre="animales.csv", a="imports:pacientes"):
    """Sube la planilla y devuelve la vista previa, siguiendo la redirección."""
    archivo.name = nombre
    return client.post(reverse(a), {"archivo": archivo}, follow=True)


def confirmar(client):
    return client.post(reverse("imports:confirmar"), follow=True)


def importar(client, *filas, cabecera=CABECERA):
    """El gesto entero: subir, mirar la vista previa y confirmar."""
    previa = subir(client, planilla(*filas, cabecera=cabecera))
    return previa, confirmar(client)


def informe_descargado(client):
    """El informe de errores como lo abre el Excel del admin: filas de celdas."""
    descarga = client.get(reverse("imports:informe"))
    assert descarga.status_code == 200
    return list(csv.reader(io.StringIO(descarga.content.decode("utf-8-sig")), delimiter=";"))


def tutor_de(usuario, **kwargs):
    return TutorFactory(clinic=usuario.clinic, **kwargs)


# --- La fila que entra ----------------------------------------------------


def test_una_fila_valida_se_convierte_en_un_paciente_a_cargo_de_su_tutor(client):
    usuario = admin(client)
    camila = tutor_de(usuario, nombre="Camila", apellidos="Rojas", rut=rut_de_prueba(1))

    importar(
        client,
        fila(
            nombre="Fido",
            especie="perro",
            raza="Poodle",
            sexo="macho",
            nacimiento="13/05/2019",
            color="Negro",
            chip=CHIP,
            rut=camila.rut,
        ),
    )

    paciente = Paciente.de_todas_las_clinicas.get()
    assert paciente.clinic == usuario.clinic
    assert paciente.nombre == "Fido"
    assert paciente.especie == Especie.PERRO
    assert paciente.raza == "Poodle"
    assert paciente.sexo == Sexo.MACHO
    assert str(paciente.fecha_de_nacimiento) == "2019-05-13"
    assert paciente.color == "Negro"
    assert paciente.microchip == CHIP
    assert paciente.responsable == camila


def test_el_historico_clinico_no_se_importa_ni_se_ofrece_importarlo(client):
    """No hay columna que lo traiga, y una que lo intente se ignora como
    cualquier otra desconocida: la digitalización empieza en la primera Consulta
    nueva."""
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))

    importar(
        client,
        fila(rut=camila.rut) + ",Le operaron la rodilla en 2021",
        cabecera=CABECERA + ",historia",
    )

    assert Paciente.de_todas_las_clinicas.count() == 1
    pagina = client.get(reverse("imports:pacientes")).content.decode()
    assert "<code>historia</code>" not in pagina
    assert "histórico clínico no se importa" in pagina


def test_la_vista_previa_no_guarda_nada(client):
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))

    respuesta = subir(client, planilla(fila(rut=camila.rut)))

    assert not Paciente.de_todas_las_clinicas.exists()
    assert respuesta.status_code == 200


# --- De quién es cada animal ----------------------------------------------


def test_el_tutor_se_resuelve_por_su_rut(client):
    usuario = admin(client)
    camila = tutor_de(usuario, nombre="Camila", apellidos="Rojas", rut=rut_de_prueba(1))
    tutor_de(usuario, nombre="Diego", apellidos="Muñoz", rut=rut_de_prueba(2))

    importar(client, fila(rut=f"{camila.rut[:-1]}-{camila.rut[-1]}"))

    assert Paciente.de_todas_las_clinicas.get().responsable == camila


def test_el_tutor_se_resuelve_por_su_telefono(client):
    usuario = admin(client)
    camila = tutor_de(usuario, telefono="+56912345678", rut=rut_de_prueba(1))
    tutor_de(usuario, telefono="+56987654321", rut=rut_de_prueba(2))

    importar(client, fila(telefono="9 1234 5678"))

    assert Paciente.de_todas_las_clinicas.get().responsable == camila


def test_el_tutor_se_resuelve_por_su_nombre_escrito_a_mano(client):
    """Es como identifica al dueño la planilla de verdad: sin tildes, y a veces
    con el apellido delante."""
    usuario = admin(client)
    camila = tutor_de(usuario, nombre="Camila", apellidos="Muñoz", rut=rut_de_prueba(1))

    importar(client, fila(nombre="Fido", tutor="Munoz Camila"))

    assert Paciente.de_todas_las_clinicas.get().responsable == camila


@pytest.mark.parametrize(
    "escrito",
    ["Camila Muñoz", "Munoz Camila", "MUÑOZ CAMILA", '"Muñoz, Camila"'],
)
def test_el_nombre_del_tutor_se_reconoce_como_lo_escriba_una_planilla(client, escrito):
    """Con tildes o sin ellas, en cualquier orden y con la coma con que un Excel
    separa el apellido del nombre. El último va entre comillas porque así es como
    una coma viaja dentro de una celda de un CSV."""
    usuario = admin(client)
    camila = tutor_de(usuario, nombre="Camila", apellidos="Muñoz", rut=rut_de_prueba(1))

    importar(client, fila(tutor=escrito))

    assert Paciente.de_todas_las_clinicas.get().responsable == camila


def test_un_tratamiento_no_nombra_a_nadie_y_la_fila_no_entra(client):
    """«Sra. Rojas» se parece a media clínica, y colgarle el animal a la primera
    sería el error que nadie ve."""
    usuario = admin(client)
    tutor_de(usuario, nombre="Camila", apellidos="Rojas", rut=rut_de_prueba(1))

    previa, _ = importar(client, fila(tutor="Sra. Rojas"))

    assert not Paciente.de_todas_las_clinicas.exists()
    assert "No hay ningún Tutor" in previa.content.decode()


def test_el_nombre_desempata_entre_los_tutores_que_comparten_telefono(client):
    """Una familia comparte número, y por eso el teléfono solo no siempre basta."""
    usuario = admin(client)
    tutor_de(usuario, nombre="Camila", apellidos="Rojas", telefono="+56912345678",
             rut=rut_de_prueba(1))
    diego = tutor_de(usuario, nombre="Diego", apellidos="Rojas", telefono="+56912345678",
                     rut=rut_de_prueba(2))

    importar(client, fila(telefono="912345678", tutor="Diego Rojas"))

    assert Paciente.de_todas_las_clinicas.get().responsable == diego


def test_cuando_dos_tutores_se_llaman_igual_la_fila_se_rechaza_diciendo_entre_cuales_dudo(client):
    usuario = admin(client)
    tutor_de(usuario, nombre="Camila", apellidos="Rojas", rut=rut_de_prueba(1),
             telefono="+56911111111")
    tutor_de(usuario, nombre="Camila", apellidos="Rojas", rut=rut_de_prueba(2),
             telefono="+56922222222")

    previa, _ = importar(client, fila(tutor="Camila Rojas"))

    assert not Paciente.de_todas_las_clinicas.exists()
    contenido = previa.content.decode()
    assert "Camila Rojas" in contenido
    # Con el RUT de cada una al lado: dos personas del mismo nombre no se
    # distinguen por el nombre, que es justo lo que las hizo dudosas.
    for cual in (1, 2):
        assert formateado(rut_de_prueba(cual)) in contenido


def test_un_tutor_anonimizado_no_se_alcanza_por_el_nombre_con_que_consta(client):
    """«Tutor anonimizado» es lo que dice su ficha, no un nombre que nadie lleve.

    Vincularle un animal sería atribuírselo a quien pidió dejar de constar, que
    es lo que ni el formulario de vínculo ni el cambio de Tutor dejan hacer.
    """
    usuario = admin(client)
    suprimido = tutor_de(usuario, nombre="Camila", apellidos="Rojas", rut=rut_de_prueba(1))
    anonimizar(suprimido, usuario)

    previa, _ = importar(client, fila(tutor="Tutor anonimizado"))

    assert not Paciente.de_todas_las_clinicas.exists()
    assert not Vinculo.de_todas_las_clinicas.exists()
    assert "No hay ningún Tutor que se llame o conteste así" in previa.content.decode()


def test_los_tutores_anonimizados_no_se_enumeran_como_dudas(client):
    usuario = admin(client)
    for cual in (1, 2):
        anonimizar(tutor_de(usuario, rut=rut_de_prueba(cual)), usuario)

    previa, _ = importar(client, fila(tutor="Tutor anonimizado"))

    assert not Paciente.de_todas_las_clinicas.exists()
    assert "Hay 2 Tutores que podrían ser" not in previa.content.decode()


def test_una_fila_cuyo_tutor_no_esta_en_la_clinica_no_entra(client):
    admin(client)

    previa, _ = importar(client, fila(tutor="Quien No Existe"))

    assert not Paciente.de_todas_las_clinicas.exists()
    assert "Quien No Existe" in previa.content.decode()


def test_una_fila_que_no_dice_de_quien_es_el_animal_no_entra(client):
    usuario = admin(client)
    tutor_de(usuario, rut=rut_de_prueba(1))

    previa, _ = importar(client, fila())

    assert not Paciente.de_todas_las_clinicas.exists()
    assert "no dice de quién es el animal" in previa.content.decode()


def test_el_rut_del_tutor_manda_sobre_el_nombre(client):
    """Dos personas de la misma casa se llaman igual; el RUT es lo único que lo
    dice sin adivinar."""
    usuario = admin(client)
    camila = tutor_de(usuario, nombre="Camila", apellidos="Rojas", rut=rut_de_prueba(1))
    tutor_de(usuario, nombre="Camila", apellidos="Rojas", rut=rut_de_prueba(2))

    importar(client, fila(rut=camila.rut, tutor="Camila Rojas"))

    assert Paciente.de_todas_las_clinicas.get().responsable == camila


def test_un_rut_que_no_es_de_nadie_de_la_clinica_no_se_resuelve_por_el_nombre(client):
    usuario = admin(client)
    tutor_de(usuario, nombre="Camila", apellidos="Rojas", rut=rut_de_prueba(1))

    previa, _ = importar(client, fila(rut=rut_de_prueba(9), tutor="Camila Rojas"))

    assert not Paciente.de_todas_las_clinicas.exists()
    assert "Ningún Tutor de la Clínica tiene el RUT" in previa.content.decode()


def test_el_tutor_de_otra_clinica_no_se_alcanza(client):
    usuario = admin(client)
    ajena = TutorFactory(clinic=ClinicaFactory(nombre="Clínica ajena"), rut=rut_de_prueba(5))

    importar(client, fila(rut=ajena.rut))

    assert not Paciente.de_todas_las_clinicas.exists()


# --- La especie, la raza y el resto de la ficha ---------------------------


def test_una_especie_que_no_esta_en_el_catalogo_rechaza_la_fila_y_dice_cuales_valen(client):
    """El catálogo es cerrado por diseño: de la especie dependen protocolos y
    formularios."""
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))

    previa, _ = importar(client, fila(especie="canino", rut=camila.rut))

    assert not Paciente.de_todas_las_clinicas.exists()
    contenido = previa.content.decode()
    assert "perro" in contenido and "gato" in contenido


def test_una_raza_que_no_esta_en_el_catalogo_entra_como_otra_con_el_texto_original(client):
    """Un catálogo de razas nunca está completo, y rechazar la fila por eso sería
    pedirle a la clínica que mienta."""
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))

    importar(client, fila(raza="Quiltro overo", rut=camila.rut))

    paciente = Paciente.de_todas_las_clinicas.get()
    assert paciente.raza == "Quiltro overo"
    assert not paciente.raza_del_catalogo


def test_una_raza_del_catalogo_mal_tecleada_se_guarda_con_la_ortografia_del_catalogo(client):
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))

    importar(client, fila(raza="bulldog frances", rut=camila.rut))

    paciente = Paciente.de_todas_las_clinicas.get()
    assert paciente.raza == "Bulldog Francés"
    assert paciente.raza_del_catalogo


def test_el_sexo_entra_como_lo_escribe_una_planilla(client):
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))

    importar(
        client,
        fila(nombre="Fido", sexo="M", rut=camila.rut),
        fila(nombre="Luna", sexo="Hembra", rut=camila.rut),
    )

    sexos = {p.nombre: p.sexo for p in Paciente.de_todas_las_clinicas.all()}
    assert sexos == {"Fido": Sexo.MACHO, "Luna": Sexo.HEMBRA}


def test_el_estado_de_identificacion_no_se_deduce_del_chip(client):
    """Tener el número apuntado no es estar inscrito, y la planilla no dice cuál
    de las dos cosas pasó."""
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))

    importar(client, fila(chip=CHIP, rut=camila.rut))

    assert Paciente.de_todas_las_clinicas.get().estado_de_identificacion == ""


def test_un_microchip_ilegible_rechaza_la_fila(client):
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))

    previa, _ = importar(client, fila(chip="no tiene", rut=camila.rut))

    assert not Paciente.de_todas_las_clinicas.exists()
    assert "dígitos" in previa.content.decode()


# --- Las fechas de una planilla -------------------------------------------


@pytest.mark.parametrize(
    "escrita",
    ["13/05/2019", "13-05-2019", "2019-05-13", "13.05.2019", "13/5/2019"],
)
def test_la_fecha_de_nacimiento_entra_en_los_formatos_habituales_de_una_planilla(
    client, escrita
):
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))

    importar(client, fila(nacimiento=escrita, rut=camila.rut))

    assert str(Paciente.de_todas_las_clinicas.get().fecha_de_nacimiento) == "2019-05-13"


def test_la_fecha_de_nacimiento_ausente_no_rompe_nada(client):
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))

    importar(client, fila(nacimiento="", rut=camila.rut))

    assert Paciente.de_todas_las_clinicas.get().fecha_de_nacimiento is None


def test_una_fecha_que_no_se_entiende_rechaza_la_fila_en_vez_de_inventarla(client):
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))

    importar(client, fila(nacimiento="el verano pasado", rut=camila.rut))

    assert not Paciente.de_todas_las_clinicas.exists()


# --- El microchip repetido ------------------------------------------------


def test_un_microchip_que_ya_es_de_otro_paciente_rechaza_la_fila_y_dice_de_quien_es(client):
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))
    PacienteFactory(clinic=usuario.clinic, nombre="Rocky", microchip=CHIP)

    previa, _ = importar(client, fila(nombre="Fido", chip=CHIP, rut=camila.rut))

    assert not Paciente.de_todas_las_clinicas.filter(nombre="Fido").exists()
    assert "Rocky" in previa.content.decode()


def test_el_mismo_chip_dos_veces_en_la_propia_planilla_entra_una_sola_vez(client):
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))

    previa, _ = importar(
        client,
        fila(nombre="Fido", chip=CHIP, rut=camila.rut),
        fila(nombre="Rocky", chip=CHIP, rut=camila.rut),
    )

    assert [p.nombre for p in Paciente.de_todas_las_clinicas.all()] == ["Fido"]
    assert "Fido" in previa.content.decode()


def test_el_mismo_chip_en_otra_clinica_no_estorba(client):
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))
    PacienteFactory(clinic=ClinicaFactory(nombre="Clínica ajena"), microchip=CHIP)

    importar(client, fila(chip=CHIP, rut=camila.rut))

    assert Paciente.de_todas_las_clinicas.filter(clinic=usuario.clinic).count() == 1


# --- Que no se dupliquen --------------------------------------------------


def test_reimportar_la_misma_planilla_no_crea_ni_un_paciente_ni_un_vinculo_mas(client):
    usuario = admin(client)
    camila = tutor_de(usuario, nombre="Camila", apellidos="Rojas", rut=rut_de_prueba(1))
    filas = (
        fila(nombre="Fido", chip=CHIP, rut=camila.rut),
        fila(nombre="Luna", tutor="Camila Rojas"),
    )
    importar(client, *filas)

    previa, _ = importar(client, *filas)

    assert Paciente.de_todas_las_clinicas.count() == 2
    assert Vinculo.de_todas_las_clinicas.count() == 2
    assert "Ya está en la Clínica" in previa.content.decode()


def test_el_animal_sin_chip_se_reconoce_por_su_nombre_y_su_tutor(client):
    """Dos animales que se llaman igual y son de dueños distintos son dos
    animales; el mismo nombre en el mismo dueño es el mismo animal."""
    usuario = admin(client)
    camila = tutor_de(usuario, nombre="Camila", apellidos="Rojas", rut=rut_de_prueba(1))
    diego = tutor_de(usuario, nombre="Diego", apellidos="Muñoz", rut=rut_de_prueba(2))

    importar(
        client,
        fila(nombre="Fido", rut=camila.rut),
        fila(nombre="Fido", rut=diego.rut),
        fila(nombre="Fido", rut=camila.rut),
    )

    assert Paciente.de_todas_las_clinicas.count() == 2


def test_el_animal_que_cambio_de_manos_no_se_duplica_al_volver_a_subir_la_planilla(client):
    """El Vínculo con su Tutor de antes está cerrado, pero el animal sigue siendo
    el mismo: una planilla vieja que lo nombra con ese Tutor habla de él."""
    usuario = admin(client)
    camila = tutor_de(usuario, nombre="Camila", apellidos="Rojas", rut=rut_de_prueba(1))
    diego = tutor_de(usuario, nombre="Diego", apellidos="Muñoz", rut=rut_de_prueba(2))
    importar(client, fila(nombre="Fido", rut=camila.rut))
    traspasar(Paciente.de_todas_las_clinicas.get(), diego, timezone.localdate())

    previa, _ = importar(client, fila(nombre="Fido", rut=camila.rut))

    assert Paciente.de_todas_las_clinicas.count() == 1
    assert "Ya está en la Clínica" in previa.content.decode()
    assert Paciente.de_todas_las_clinicas.get().responsable == diego


def test_reimportar_no_le_cambia_el_tutor_a_un_animal_que_ya_estaba(client):
    """Que un animal cambie de manos es un Traspaso —con su fecha y su Vínculo
    cerrado—, no un efecto de volver a subir una planilla."""
    usuario = admin(client)
    camila = tutor_de(usuario, nombre="Camila", apellidos="Rojas", rut=rut_de_prueba(1))
    diego = tutor_de(usuario, nombre="Diego", apellidos="Muñoz", rut=rut_de_prueba(2))
    importar(client, fila(nombre="Fido", chip=CHIP, rut=camila.rut))

    importar(client, fila(nombre="Fido", chip=CHIP, rut=diego.rut))

    assert Paciente.de_todas_las_clinicas.count() == 1
    assert Paciente.de_todas_las_clinicas.get().responsable == camila
    assert Vinculo.de_todas_las_clinicas.count() == 1


def test_el_paciente_que_ya_estaba_no_se_pisa_con_lo_que_traiga_la_planilla(client):
    """Reimportar no es corregir: la ficha que ya existe puede haberse corregido a
    mano, y la planilla vieja no tiene por qué ganarle."""
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))
    PacienteFactory(clinic=usuario.clinic, nombre="Fido", microchip=CHIP, color="Blanco")

    importar(client, fila(nombre="Fido", color="Negro", chip=CHIP, rut=camila.rut))

    assert Paciente.de_todas_las_clinicas.get().color == "Blanco"


def test_una_tanda_nueva_entra_al_lado_de_lo_que_ya_estaba(client):
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))
    importar(client, fila(nombre="Fido", chip=CHIP, rut=camila.rut))

    importar(
        client,
        fila(nombre="Fido", chip=CHIP, rut=camila.rut),
        fila(nombre="Luna", chip=OTRO_CHIP, rut=camila.rut),
    )

    assert Paciente.de_todas_las_clinicas.count() == 2


# --- El informe y el formato documentado ----------------------------------


def test_el_informe_dice_el_numero_de_linea_y_el_motivo_de_cada_fila_que_no_entra(client):
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))
    subir(
        client,
        planilla(
            fila(nombre="Fido", rut=camila.rut),
            fila(nombre="Luna", especie="dragón", rut=camila.rut),
        ),
    )

    lineas = informe_descargado(client)

    assert lineas[0] == ["línea", "fila", "qué pasa", "motivo"]
    # La cabecera es la línea 1 y Fido la 2, así que Luna es la 3.
    assert lineas[1][0] == "3"
    assert "Luna" in lineas[1][1]
    assert len(lineas) == 2


def test_las_dos_planillas_de_ejemplo_se_importan_una_detras_de_otra(client):
    """El ejemplo de Pacientes apunta a los Tutores del ejemplo de Tutores: lo
    que se documenta, lo que se descarga y lo que el importador reconoce salen de
    la misma definición, y una migración de verdad va en ese orden."""
    admin(client)
    tutores = client.get(reverse("imports:ejemplo_de_tutores"))
    subir(client, io.BytesIO(tutores.content), nombre="tutores.csv", a="imports:tutores")
    confirmar(client)

    pacientes = client.get(reverse("imports:ejemplo_de_pacientes"))
    assert pacientes.status_code == 200
    subir(client, io.BytesIO(pacientes.content), nombre="pacientes.csv")
    confirmar(client)

    assert Tutor.de_todas_las_clinicas.count() == 3
    assert Paciente.de_todas_las_clinicas.count() == 3
    assert all(p.responsable is not None for p in Paciente.de_todas_las_clinicas.all())


def test_la_pagina_de_subida_documenta_las_columnas_y_ofrece_el_ejemplo(client):
    admin(client)

    contenido = client.get(reverse("imports:pacientes")).content.decode()

    for columna in ("nombre", "especie", "raza", "microchip", "rut_tutor", "tutor"):
        assert f"<code>{columna}</code>" in contenido
    assert reverse("imports:ejemplo_de_pacientes") in contenido


def test_una_planilla_sin_la_columna_de_la_especie_no_importa_nada_y_lo_dice(client):
    admin(client)

    respuesta = subir(client, planilla("Fido,12345678-5", cabecera="nombre,rut_tutor"))

    assert not Paciente.de_todas_las_clinicas.exists()
    assert "especie" in respuesta.content.decode()


def test_una_planilla_que_no_dice_de_quien_es_ningun_animal_no_se_lee(client):
    """Sin ninguna de las tres columnas del Tutor, ninguna fila podría entrar: es
    un problema del archivo y no de cada fila."""
    admin(client)

    respuesta = subir(client, planilla("Fido,perro", cabecera="nombre,especie"))

    assert not Paciente.de_todas_las_clinicas.exists()
    assert "tutor" in respuesta.content.decode().lower()


# --- Quién puede, y qué queda anotado -------------------------------------


def test_el_mostrador_no_importa_planillas_de_pacientes(client):
    client.force_login(UsuarioFactory(rol="recepcion"))

    assert client.get(reverse("imports:pacientes")).status_code == 403


def test_la_importacion_queda_en_el_registro_de_acceso_con_quien_cuando_y_cuantas(client):
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))

    importar(
        client,
        fila(nombre="Fido", rut=camila.rut),
        fila(nombre="Luna", especie="dragón", rut=camila.rut),
    )

    importacion = Importacion.de_todas_las_clinicas.get()
    assert importacion.usuario == usuario
    assert importacion.que_se_importo == LoQueSeImporta.PACIENTES
    assert importacion.planilla == "animales.csv"
    assert (importacion.filas_leidas, importacion.filas_creadas) == (2, 1)
    assert (importacion.filas_repetidas, importacion.filas_con_error) == (0, 1)

    anotacion = RegistroDeAcceso.de_todas_las_clinicas.get(tipo_de_objeto="imports.Importacion")
    assert anotacion.usuario == usuario
    assert anotacion.accion == Accion.CREACION


def test_importar_no_anota_una_creacion_por_cada_paciente(client):
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))

    importar(client, fila(nombre="Fido", rut=camila.rut), fila(nombre="Luna", rut=camila.rut))

    assert not RegistroDeAcceso.de_todas_las_clinicas.filter(
        tipo_de_objeto="patients.Paciente", accion=Accion.CREACION
    ).exists()


def test_la_vista_previa_que_nombra_a_un_paciente_que_ya_esta_deja_constancia(client):
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))
    paciente = PacienteFactory(clinic=usuario.clinic, nombre="Fido", microchip=CHIP)
    VinculoFactory(tutor=camila, paciente=paciente, responsable=True)

    subir(client, planilla(fila(nombre="Fido", chip=CHIP, rut=camila.rut)))

    assert RegistroDeAcceso.de_todas_las_clinicas.filter(
        tipo_de_objeto="patients.Paciente", accion=Accion.LECTURA
    ).exists()


def test_la_vista_previa_que_duda_entre_dos_tutores_deja_constancia_de_que_los_nombro(client):
    usuario = admin(client)
    tutor_de(usuario, nombre="Camila", apellidos="Rojas", rut=rut_de_prueba(1))
    tutor_de(usuario, nombre="Camila", apellidos="Rojas", rut=rut_de_prueba(2))

    subir(client, planilla(fila(tutor="Camila Rojas")))

    assert RegistroDeAcceso.de_todas_las_clinicas.filter(
        tipo_de_objeto="tutors.Tutor", accion=Accion.LECTURA
    ).exists()


def test_una_vista_previa_que_no_nombra_a_nadie_no_anota_ninguna_lectura(client):
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))

    subir(client, planilla(fila(nombre="Fido", rut=camila.rut)))

    assert not RegistroDeAcceso.de_todas_las_clinicas.filter(
        accion=Accion.LECTURA
    ).exists()


# --- La planilla que espera -----------------------------------------------


def test_la_planilla_de_pacientes_no_se_confirma_como_si_fuera_de_tutores(client):
    """Lo que espera confirmación se acuerda de qué traía: confirmar es una sola
    página para las dos planillas."""
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))

    importar(client, fila(nombre="Fido", rut=camila.rut))

    assert Tutor.de_todas_las_clinicas.count() == 1
    assert Paciente.de_todas_las_clinicas.count() == 1


def test_cada_pagina_enseña_sus_propias_tandas_y_no_las_de_la_otra(client):
    """Una migración va por tandas de las dos cosas a la vez, y lo que hace falta
    saber en cada página es por dónde iba **esa**."""
    usuario = admin(client)
    camila = tutor_de(usuario, rut=rut_de_prueba(1))
    subir(
        client,
        planilla(f"Camila,Rojas,{camila.rut}", cabecera="nombre,apellidos,rut"),
        nombre="clientes.csv",
        a="imports:tutores",
    )
    confirmar(client)
    importar(client, fila(nombre="Fido", rut=camila.rut))

    pacientes = client.get(reverse("imports:pacientes")).content.decode()
    tutores = client.get(reverse("imports:tutores")).content.decode()

    assert "animales.csv" in pacientes and "clientes.csv" not in pacientes
    assert "clientes.csv" in tutores and "animales.csv" not in tutores

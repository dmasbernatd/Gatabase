"""Importar la planilla con la que una clínica lleva hoy sus Tutores.

Es la primera media hora de una clínica que llega, así que los tests entran por
HTTP como entra el admin: sube un archivo, mira lo que la página le dice que va a
pasar, y solo entonces confirma. Lo que se comprueba de cada caso es lo mismo que
el admin comprueba —qué quedó en la Clínica y qué dice el informe—, porque la
promesa del ticket es justamente que las dos cosas coincidan.

Cómo se lee un CSV con las manías de un Excel chileno —separador, codificación,
nombres de columna— se prueba aparte, en `test_planilla.py`: son casos que no se
ven desde un archivo bien formado.
"""

import csv
import io

import pytest
from django.urls import reverse

from apps.audit.models import Accion, RegistroDeAcceso
from apps.imports.models import Importacion
from apps.imports.tutores import ejemplo
from apps.tutors.models import Tutor
from tests.factories import ClinicaFactory, TutorFactory, UsuarioFactory, rut_de_prueba

pytestmark = pytest.mark.django_db

CABECERA = "nombre,apellidos,rut,telefono,correo,direccion"

# Un RUT que cuadra, y el mismo con el último dígito cambiado: es el error de
# tecleo que trae una planilla de verdad, y el que el ticket manda probar.
RUT_BUENO = rut_de_prueba(1)
RUT_ROTO = RUT_BUENO[:-1] + ("0" if RUT_BUENO[-1] != "0" else "1")


def admin(client, clinica=None):
    """Quien sube la planilla: la importación es de administración, no del mostrador."""
    usuario = UsuarioFactory(rol="admin", **({"clinic": clinica} if clinica else {}))
    client.force_login(usuario)
    return usuario


def planilla(*filas, cabecera=CABECERA):
    """Un CSV subido, tal como llega del navegador."""
    contenido = "\n".join([cabecera, *filas]) + "\n"
    return io.BytesIO(contenido.encode("utf-8"))


def subir(client, archivo, nombre="clientes.csv"):
    """Sube la planilla y devuelve la vista previa, siguiendo la redirección."""
    archivo.name = nombre
    return client.post(reverse("imports:tutores"), {"archivo": archivo}, follow=True)


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
    texto = descarga.content.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(texto), delimiter=";"))


# --- La fila que entra ----------------------------------------------------


def test_una_fila_valida_se_convierte_en_un_tutor_de_la_clinica_de_quien_importa(client):
    usuario = admin(client)

    importar(
        client,
        f"Camila,Rojas Pizarro,{RUT_BUENO},9 1234 5678,camila@correo.example,Av. Providencia 1234",
    )

    tutor = Tutor.de_todas_las_clinicas.get()
    assert tutor.clinic == usuario.clinic
    assert tutor.nombre == "Camila"
    assert tutor.apellidos == "Rojas Pizarro"
    assert tutor.rut == RUT_BUENO
    assert tutor.telefono == "+56912345678"
    assert tutor.email == "camila@correo.example"
    assert tutor.direccion == "Av. Providencia 1234"


def test_el_rut_y_el_telefono_se_guardan_con_las_reglas_del_mostrador(client):
    """Se dictan como se dictan y se guardan como se guardan: no hay una segunda
    idea de qué es un RUT dentro del importador."""
    admin(client)

    importar(client, f"Camila,Rojas,{RUT_BUENO[:-1]}-{RUT_BUENO[-1]},+56 9 8765 4321,,")

    tutor = Tutor.de_todas_las_clinicas.get()
    assert tutor.rut == RUT_BUENO
    assert tutor.telefono == "+56987654321"


def test_la_vista_previa_no_guarda_nada(client):
    admin(client)

    respuesta = subir(client, planilla(f"Camila,Rojas,{RUT_BUENO},,,"))

    assert not Tutor.de_todas_las_clinicas.exists()
    assert b"1" in respuesta.content
    assert respuesta.status_code == 200


def test_la_planilla_no_deja_elegir_la_clinica(client):
    """Lo importado es de la Clínica de quien importa, y no hay columna que diga
    otra cosa: una columna «clinica» se ignora como cualquier otra desconocida."""
    usuario = admin(client)
    otra = ClinicaFactory(nombre="Clínica ajena")

    importar(
        client,
        f"Camila,Rojas,{RUT_BUENO},,,,{otra.pk}",
        cabecera=CABECERA + ",clinica",
    )

    assert Tutor.de_todas_las_clinicas.get().clinic == usuario.clinic


# --- Las filas que no entran ----------------------------------------------


def test_una_fila_con_el_rut_invalido_no_entra_y_las_demas_si(client):
    admin(client)

    previa, _ = importar(
        client,
        f"Camila,Rojas,{RUT_ROTO},,,",
        f"Diego,Muñoz,{RUT_BUENO},,,",
    )

    assert [tutor.nombre for tutor in Tutor.de_todas_las_clinicas.all()] == ["Diego"]
    assert "dígito verificador" in previa.content.decode()


def test_una_fila_con_el_telefono_ilegible_no_entra_y_las_demas_si(client):
    admin(client)

    previa, _ = importar(
        client,
        "Camila,Rojas,,no tiene,,",
        f"Diego,Muñoz,{RUT_BUENO},,,",
    )

    assert [tutor.nombre for tutor in Tutor.de_todas_las_clinicas.all()] == ["Diego"]
    assert "teléfono" in previa.content.decode().lower()


def test_una_fila_sin_nombre_no_entra(client):
    admin(client)

    importar(client, f",Rojas,{RUT_BUENO},,,")

    assert not Tutor.de_todas_las_clinicas.exists()


def test_una_fila_sin_rut_y_sin_telefono_no_entra_porque_no_habria_como_reconocerla(client):
    """No es una ficha mala —el mostrador registra a diario Tutores así— pero
    aceptarla sería prometer que reimportar no duplica y no cumplirlo."""
    admin(client)

    previa, _ = importar(client, "Camila,Rojas,,,,")

    assert not Tutor.de_todas_las_clinicas.exists()
    assert "no hay manera de reconocer" in previa.content.decode()


def test_el_informe_dice_el_numero_de_linea_y_el_motivo_de_cada_fila_que_no_entra(client):
    admin(client)
    subir(client, planilla(f"Camila,Rojas,{RUT_BUENO},,,", f"Diego,Muñoz,{RUT_ROTO},,,"))

    lineas = informe_descargado(client)

    cabecera, fila = lineas[0], lineas[1]
    assert cabecera == ["línea", "fila", "qué pasa", "motivo"]
    # La cabecera de la planilla es la línea 1 y Camila la 2, así que Diego es la 3.
    assert fila[0] == "3"
    assert fila[1] == "Diego Muñoz"
    assert "dígito verificador" in fila[3]
    assert len(lineas) == 2, "solo la fila que no entra tiene que aparecer en el informe"


# --- Que no se dupliquen --------------------------------------------------


def test_una_fila_repetida_dentro_de_la_propia_planilla_entra_una_sola_vez(client):
    admin(client)

    previa, _ = importar(
        client,
        f"Camila,Rojas,{RUT_BUENO},,,",
        f"Camila,Rojas Pizarro,{RUT_BUENO},9 1234 5678,,",
    )

    assert Tutor.de_todas_las_clinicas.count() == 1
    assert "ya venía en la línea 2" in previa.content.decode()


def test_dos_personas_sin_rut_se_distinguen_por_el_nombre_y_el_telefono(client):
    admin(client)

    importar(
        client,
        "Camila,Rojas,,9 1234 5678,,",
        "Diego,Muñoz,,9 1234 5678,,",
        "Camila,Rojas,,9 1234 5678,,",
    )

    assert sorted(t.nombre for t in Tutor.de_todas_las_clinicas.all()) == ["Camila", "Diego"]


def test_el_nombre_se_reconoce_con_tilde_y_sin_ella(client):
    """La misma persona aparece en dos planillas como «Muñoz» y como «Munoz»."""
    admin(client)

    importar(client, "Diego,Muñoz,,9 1234 5678,,", "Diego,Munoz,,9 1234 5678,,")

    assert Tutor.de_todas_las_clinicas.count() == 1


def test_reimportar_la_misma_planilla_entera_no_crea_ni_un_tutor_mas(client):
    admin(client)
    filas = (
        f"Camila,Rojas,{RUT_BUENO},,,",
        f"Diego,Muñoz,{rut_de_prueba(2)},,,",
        "Ignacia,Vera,,9 1234 5678,,",
    )
    importar(client, *filas)

    previa, _ = importar(client, *filas)

    assert Tutor.de_todas_las_clinicas.count() == 3
    assert "Ya está en la Clínica" in previa.content.decode()


def test_una_tanda_nueva_entra_al_lado_de_lo_que_ya_estaba(client):
    """Es para lo que sirve la idempotencia: importar por tandas sin llevar la
    cuenta de por dónde se iba."""
    admin(client)
    importar(client, f"Camila,Rojas,{RUT_BUENO},,,")

    importar(client, f"Camila,Rojas,{RUT_BUENO},,,", f"Diego,Muñoz,{rut_de_prueba(2)},,,")

    assert Tutor.de_todas_las_clinicas.count() == 2


def test_una_segunda_tanda_sin_la_columna_del_rut_no_duplica_a_quien_entro_con_el(client):
    """La segunda planilla casi nunca trae las mismas columnas que la primera, y
    reconocer solo por el RUT duplicaría a media clínica en cuanto falte."""
    admin(client)
    importar(client, f"Camila,Rojas,{RUT_BUENO},9 1234 5678,,")

    previa, _ = importar(
        client, "Camila,Rojas,9 1234 5678", cabecera="nombre,apellidos,telefono"
    )

    assert Tutor.de_todas_las_clinicas.count() == 1
    assert "Ya está en la Clínica" in previa.content.decode()


def test_una_segunda_tanda_con_el_rut_no_duplica_a_quien_entro_sin_el(client):
    """Y al revés: la primera planilla no traía RUT y la segunda sí."""
    admin(client)
    importar(client, "Camila,Rojas,9 1234 5678", cabecera="nombre,apellidos,telefono")

    importar(client, f"Camila,Rojas,{RUT_BUENO},9 1234 5678,,")

    assert Tutor.de_todas_las_clinicas.count() == 1


def test_dos_ruts_distintos_son_dos_personas_aunque_compartan_nombre_y_telefono(client):
    """Una madre y una hija que se llaman igual y viven en la misma casa. El RUT
    es lo único que lo dice sin adivinar, y fundirlas sería un daño que no se
    deshace."""
    admin(client)

    importar(
        client,
        f"Camila,Rojas,{RUT_BUENO},9 1234 5678,,",
        f"Camila,Rojas,{rut_de_prueba(2)},9 1234 5678,,",
    )

    assert Tutor.de_todas_las_clinicas.count() == 2


def test_el_tutor_que_ya_estaba_no_se_pisa_con_lo_que_traiga_la_planilla(client):
    """Reimportar no es corregir: la ficha que ya existe puede haberse corregido a
    mano, y la planilla vieja no tiene por qué ganarle."""
    usuario = admin(client)
    TutorFactory(clinic=usuario.clinic, nombre="Camila", apellidos="Rojas Pizarro", rut=RUT_BUENO)

    importar(client, f"Camila,Rojas,{RUT_BUENO},,,")

    assert Tutor.de_todas_las_clinicas.get().apellidos == "Rojas Pizarro"


def test_el_mismo_rut_en_otra_clinica_no_estorba(client):
    usuario = admin(client)
    TutorFactory(clinic=ClinicaFactory(nombre="Otra clínica"), rut=RUT_BUENO)

    importar(client, f"Camila,Rojas,{RUT_BUENO},,,")

    assert Tutor.de_todas_las_clinicas.filter(clinic=usuario.clinic).count() == 1


# --- El formato documentado -----------------------------------------------


def test_la_planilla_de_ejemplo_se_descarga_y_se_importa_entera(client):
    """Lo que se documenta, lo que se descarga y lo que el importador reconoce
    salen de la misma definición: el ejemplo tiene que entrar sin tocar nada."""
    admin(client)
    descarga = client.get(reverse("imports:ejemplo_de_tutores"))

    assert descarga.status_code == 200
    subir(client, io.BytesIO(descarga.content), nombre="ejemplo.csv")
    confirmar(client)

    assert Tutor.de_todas_las_clinicas.count() == 3


def test_la_pagina_de_subida_documenta_las_columnas_y_ofrece_el_ejemplo(client):
    admin(client)

    respuesta = client.get(reverse("imports:tutores"))
    contenido = respuesta.content.decode()

    for columna in ("nombre", "apellidos", "rut", "telefono", "correo", "direccion"):
        assert f"<code>{columna}</code>" in contenido
    assert reverse("imports:ejemplo_de_tutores") in contenido


def test_una_planilla_sin_la_columna_del_nombre_no_importa_nada_y_lo_dice(client):
    admin(client)

    respuesta = subir(client, planilla("Rojas,+56912345678", cabecera="apellidos,telefono"))

    assert not Tutor.de_todas_las_clinicas.exists()
    assert "falta la columna nombre" in respuesta.content.decode()


# --- Quién puede, y qué queda anotado -------------------------------------


def test_el_mostrador_no_importa_planillas(client):
    client.force_login(UsuarioFactory(rol="recepcion"))

    assert client.get(reverse("imports:tutores")).status_code == 403


def test_la_importacion_queda_en_el_registro_de_acceso_con_quien_cuando_y_cuantas(client):
    usuario = admin(client)

    importar(client, f"Camila,Rojas,{RUT_BUENO},,,", f"Diego,Muñoz,{RUT_ROTO},,,")

    importacion = Importacion.de_todas_las_clinicas.get()
    assert importacion.usuario == usuario
    assert importacion.clinic == usuario.clinic
    assert importacion.planilla == "clientes.csv"
    assert (importacion.filas_leidas, importacion.filas_creadas) == (2, 1)
    assert (importacion.filas_repetidas, importacion.filas_con_error) == (0, 1)

    anotacion = RegistroDeAcceso.de_todas_las_clinicas.get(tipo_de_objeto="imports.Importacion")
    assert anotacion.usuario == usuario
    assert anotacion.accion == Accion.CREACION
    assert anotacion.identificador == str(importacion.pk)
    assert anotacion.momento is not None


def test_importar_no_anota_una_creacion_por_cada_tutor(client):
    """Un gesto es una anotación: tres mil por una planilla enterrarían en ruido
    la tabla que tiene que valer como prueba. La lectura del listado al que se
    vuelve después sí se anota, como se anotaría entrando en él por su enlace."""
    admin(client)

    importar(client, f"Camila,Rojas,{RUT_BUENO},,,", f"Diego,Muñoz,{rut_de_prueba(2)},,,")

    assert not RegistroDeAcceso.de_todas_las_clinicas.filter(
        tipo_de_objeto="tutors.Tutor", accion=Accion.CREACION
    ).exists()


def test_la_vista_previa_que_nombra_a_un_tutor_que_ya_esta_deja_constancia(client):
    usuario = admin(client)
    TutorFactory(clinic=usuario.clinic, nombre="Camila", apellidos="Rojas", rut=RUT_BUENO)

    subir(client, planilla(f"Camila,Rojas,{RUT_BUENO},,,"))

    assert RegistroDeAcceso.de_todas_las_clinicas.filter(
        tipo_de_objeto="tutors.Tutor", accion=Accion.LECTURA
    ).exists()


def test_una_vista_previa_que_no_nombra_a_nadie_no_anota_ninguna_lectura(client):
    admin(client)

    subir(client, planilla(f"Camila,Rojas,{RUT_BUENO},,,"))

    assert not RegistroDeAcceso.de_todas_las_clinicas.filter(
        tipo_de_objeto="tutors.Tutor"
    ).exists()


# --- La planilla que espera -----------------------------------------------


def test_confirmar_sin_haber_subido_nada_no_revienta(client):
    admin(client)

    respuesta = confirmar(client)

    assert respuesta.status_code == 200
    assert not Importacion.de_todas_las_clinicas.exists()


def test_confirmar_dos_veces_no_importa_dos_veces(client):
    admin(client)
    subir(client, planilla(f"Camila,Rojas,{RUT_BUENO},,,"))
    confirmar(client)

    confirmar(client)

    assert Tutor.de_todas_las_clinicas.count() == 1
    assert Importacion.de_todas_las_clinicas.count() == 1


def test_descartar_la_planilla_la_deja_sin_efecto(client):
    admin(client)
    subir(client, planilla(f"Camila,Rojas,{RUT_BUENO},,,"))

    client.post(reverse("imports:descartar"))
    confirmar(client)

    assert not Tutor.de_todas_las_clinicas.exists()


def test_la_planilla_de_otro_no_se_alcanza_desde_otra_sesion(client, django_user_model):
    """Lo que espera confirmación cuelga de la sesión de quien lo subió, y ninguna
    URL del importador lleva identificador de nada."""
    admin(client)
    subir(client, planilla(f"Camila,Rojas,{RUT_BUENO},,,"))

    from django.test import Client

    otro = Client()
    admin(otro)
    respuesta = otro.post(reverse("imports:confirmar"), follow=True)

    assert not Tutor.de_todas_las_clinicas.exists()
    assert respuesta.status_code == 200


def test_la_pagina_de_subida_enseña_lo_que_se_importo_antes_y_cuantas_filas(client):
    """Es donde «cuántas filas» se vuelve legible: el Registro anota que hubo una
    importación y apunta a ella, pero no sabe guardar «ciento veinte filas»."""
    usuario = admin(client)
    importar(client, f"Camila,Rojas,{RUT_BUENO},,,", f"Diego,Muñoz,{RUT_ROTO},,,")

    contenido = client.get(reverse("imports:tutores")).content.decode()

    assert "clientes.csv" in contenido
    assert str(usuario) in contenido


def test_las_importaciones_de_otra_clinica_no_se_ven(client):
    admin(client, clinica=ClinicaFactory(nombre="Clínica ajena"))
    subir(client, planilla(f"Camila,Rojas,{RUT_BUENO},,,"), nombre="de-la-otra.csv")
    confirmar(client)

    admin(client)
    contenido = client.get(reverse("imports:tutores")).content.decode()

    assert "de-la-otra.csv" not in contenido

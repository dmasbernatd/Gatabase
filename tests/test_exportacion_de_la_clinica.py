"""El admin se lleva los datos de su Clínica, y la Clínica que se va se cierra.

Los tests entran por HTTP como entra el admin: pulsa un botón y recibe un
archivo. Lo que se comprueba de él es lo que comprobaría quien lo recibe —que se
abre con cualquier programa de planillas, que están sus Tutores y que no está
ninguno de la clínica de al lado—, porque la promesa del ticket es justamente esa
y no la de un formato interno bien formado.

Lo que **no** se puede comprobar así es la casilla de la memoria: para que se
notara la diferencia entre juntar el zip entero y soltarlo por trozos harían
falta los tres mil Tutores de una clínica de verdad, y eso no cabe en un test.
Se comprueba en la costura, que es donde vive la decisión: las filas se leen de a
una (`hojas`) y el archivo sale de a trozos (`paquete`).
"""

import csv
import datetime as dt
import io
import zipfile

import pytest
from django.contrib.auth import get_user_model
from django.http import StreamingHttpResponse
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import EL_CONJUNTO, Accion, RegistroDeAcceso
from apps.exports.hojas import HOJAS, _de_la_clinica, de_quienes_son_los_datos
from apps.exports.paquete import LEEME, como_un_zip, se_llama
from apps.patients.estados import EstadoDelPaciente
from apps.tenancy.models import Clinica, Rol
from apps.tutors.models import Tutor
from apps.tutors.consentimiento import Canal
from tests.factories import (
    ClinicaDeDerivacionFactory,
    ClinicaFactory,
    ExcepcionDeAtencionFactory,
    FranjaDeAtencionFactory,
    PacienteFactory,
    SedeFactory,
    TutorFactory,
    UsuarioFactory,
    VinculoFactory,
)

pytestmark = pytest.mark.django_db

EXPORTACION = "exports:exportacion"
DESCARGA = "exports:descarga"
CIERRE = "exports:cerrar"


def _ayer():
    return timezone.localdate() - dt.timedelta(days=1)


def admin(client, clinica=None):
    """Quien exporta: es el acceso masivo a los datos, y es cosa del admin."""
    usuario = UsuarioFactory(rol=Rol.ADMIN, **({"clinic": clinica} if clinica else {}))
    client.force_login(usuario)
    return usuario


def descargar(client):
    """El zip descargado, ya abierto."""
    respuesta = client.post(reverse(DESCARGA))
    assert respuesta.status_code == 200
    return zipfile.ZipFile(io.BytesIO(b"".join(respuesta.streaming_content)))


def planilla(zip_de_la_clinica, archivo):
    """Una de las planillas de dentro, como la abre el Excel del admin."""
    texto = zip_de_la_clinica.read(archivo).decode("utf-8-sig")
    return list(csv.reader(io.StringIO(texto), delimiter=";"))


def columna(filas, rotulo):
    """Los valores de esa columna, sin la cabecera."""
    cual = filas[0].index(rotulo)
    return [fila[cual] for fila in filas[1:]]


def una_clinica_poblada(nombre):
    """Una Clínica con algo de cada cosa que la exportación promete llevarse."""
    clinica = ClinicaFactory(nombre=nombre)
    sede = SedeFactory(clinic=clinica, nombre=f"Sede de {nombre}")
    tutor = TutorFactory(clinic=clinica, nombre=nombre, apellidos="Rojas")
    paciente = PacienteFactory(clinic=clinica, nombre=f"Perro de {nombre}")
    tutor.se_hace_cargo_de(paciente)
    tutor.deja_dicho_sobre_el_contacto(Canal.WHATSAPP, otorgado=True)
    FranjaDeAtencionFactory(sede=sede)
    ExcepcionDeAtencionFactory(sede=sede)
    ClinicaDeDerivacionFactory(clinic=clinica, nombre=f"Urgencias de {nombre}")
    return clinica


# --- Lo que se descarga ----------------------------------------------------


def test_el_admin_se_descarga_un_zip_de_planillas(client):
    """La casilla del formato: no un volcado del sistema, sino algo que se abre
    con dos clics en el mismo Excel con que la clínica llevaba su archivador."""
    usuario = admin(client)
    TutorFactory(clinic=usuario.clinic, nombre="Camila", apellidos="Rojas")

    descarga = client.post(reverse(DESCARGA))

    assert descarga["Content-Type"] == "application/zip"
    assert "attachment" in descarga["Content-Disposition"]
    dentro = zipfile.ZipFile(io.BytesIO(b"".join(descarga.streaming_content)))
    assert dentro.testzip() is None


def test_van_dentro_todas_las_hojas_que_la_exportacion_declara(client):
    """La página documenta las hojas desde la misma lista que las escribe, así que
    una hoja que faltara aquí sería una que la página promete y el zip no trae."""
    admin(client)

    dentro = descargar(client)

    assert set(dentro.namelist()) == {LEEME, *(hoja.nombre for hoja in HOJAS)}


def test_los_tutores_y_sus_pacientes_salen_con_sus_datos(client):
    usuario = admin(client)
    tutor = TutorFactory(
        clinic=usuario.clinic, nombre="Camila", apellidos="Rojas", telefono="+56912345678"
    )
    paciente = PacienteFactory(clinic=usuario.clinic, nombre="Rocco")
    tutor.se_hace_cargo_de(paciente)

    dentro = descargar(client)

    tutores = planilla(dentro, "tutores.csv")
    assert columna(tutores, "nombre") == ["Camila"]
    assert columna(tutores, "RUT") == [tutor.rut_a_la_chilena]
    assert columna(tutores, "teléfono") == ["+56912345678"]
    assert columna(planilla(dentro, "pacientes.csv"), "nombre") == ["Rocco"]
    vinculos = planilla(dentro, "vinculos.csv")
    assert columna(vinculos, "id del Tutor") == [str(tutor.pk)]
    assert columna(vinculos, "id del Paciente") == [str(paciente.pk)]
    assert columna(vinculos, "es el responsable") == ["sí"]


def test_el_vinculo_cerrado_va_dentro_con_la_fecha_en_que_se_cerro(client):
    """Quién trajo al animal antes es parte de su Historia (ADR-0001): una
    exportación que solo trajera los Vínculos vivos se llevaría la clínica de hoy
    y dejaría atrás la de siempre."""
    usuario = admin(client)
    paciente = PacienteFactory(clinic=usuario.clinic, estado=EstadoDelPaciente.INACTIVO)
    tutor = TutorFactory(clinic=usuario.clinic, nombre="Camila")
    vinculo = tutor.se_hace_cargo_de(paciente)
    vinculo.cerrar(fecha=timezone.localdate())

    vinculos = planilla(descargar(client), "vinculos.csv")

    assert columna(vinculos, "hasta") == [timezone.localdate().isoformat()]
    assert columna(vinculos, "es el responsable") == ["no"]


def test_lo_que_el_tutor_dijo_del_contacto_va_entero_y_no_solo_lo_ultimo(client):
    """Lo exigible no es qué acepta hoy, sino desde cuándo lo aceptaba el día que
    se le escribió: una columna de sí o no dejaría sin nada detrás a los mensajes
    que ya salieron."""
    usuario = admin(client)
    tutor = TutorFactory(clinic=usuario.clinic, nombre="Camila")
    tutor.deja_dicho_sobre_el_contacto(Canal.WHATSAPP, otorgado=True, fecha=_ayer())
    tutor.deja_dicho_sobre_el_contacto(Canal.WHATSAPP, otorgado=False)

    dichos = planilla(descargar(client), "consentimientos.csv")

    assert columna(dichos, "autoriza") == ["no", "sí"]


def test_la_configuracion_de_las_sedes_va_dentro(client):
    usuario = admin(client)
    sede = SedeFactory(clinic=usuario.clinic, nombre="Sede Providencia")
    FranjaDeAtencionFactory(sede=sede)
    ExcepcionDeAtencionFactory(sede=sede, motivo="Fiestas Patrias")
    ClinicaDeDerivacionFactory(clinic=usuario.clinic, nombre="Urgencias Las Condes")

    dentro = descargar(client)

    assert "Sede Providencia" in columna(planilla(dentro, "sedes.csv"), "nombre")
    assert columna(planilla(dentro, "horarios.csv"), "día") == ["lunes"]
    assert columna(planilla(dentro, "excepciones.csv"), "motivo") == ["Fiestas Patrias"]
    assert columna(planilla(dentro, "clinicas_de_derivacion.csv"), "nombre") == [
        "Urgencias Las Condes"
    ]


def test_los_catalogos_van_dentro_para_que_se_entiendan_los_codigos(client):
    """La especie de `pacientes.csv` dice `perro`, y el catálogo es lo que dice
    qué valores existen y cómo se llaman."""
    admin(client)

    dentro = descargar(client)

    assert "perro" in columna(planilla(dentro, "especies.csv"), "código")
    assert "Mestizo" in columna(planilla(dentro, "razas.csv"), "raza")


def test_el_leeme_explica_el_archivo_a_quien_lo_abra_dentro_de_un_ano(client):
    usuario = admin(client)

    leeme = descargar(client).read(LEEME).decode("utf-8")

    assert usuario.clinic.nombre in leeme
    assert "vinculos.csv" in leeme


def test_la_descarga_se_llama_como_la_clinica_y_el_dia(client):
    usuario = admin(client)
    usuario.clinic.nombre = "Clínica Ñuñoa"
    usuario.clinic.save(update_fields=["nombre"])

    descarga = client.post(reverse(DESCARGA))

    assert se_llama(usuario.clinic, timezone.now()) in descarga["Content-Disposition"]
    assert "gatabase-clinica-nunoa-" in descarga["Content-Disposition"]


# --- Solo lo suyo ----------------------------------------------------------


def test_la_exportacion_solo_trae_datos_de_su_clinica(client):
    """La casilla del ticket, con las dos Clínicas pobladas: lo que se descarga
    tiene que ser irreconocible para la de al lado (ADR-0003)."""
    suya = una_clinica_poblada("Clínica del Parque")
    ajena = una_clinica_poblada("Clínica del Río")
    admin(client, clinica=suya)

    dentro = descargar(client)

    assert columna(planilla(dentro, "tutores.csv"), "nombre") == ["Clínica del Parque"]
    assert columna(planilla(dentro, "pacientes.csv"), "nombre") == ["Perro de Clínica del Parque"]
    assert columna(planilla(dentro, "vinculos.csv"), "Paciente") == [
        "Perro de Clínica del Parque"
    ]
    # Con `in` y no con `==`: el admin que se acaba de crear trae su propia Sede,
    # y lo que se comprueba aquí es de quién son las que salen, no cuántas hay.
    assert "Sede de Clínica del Parque" in columna(planilla(dentro, "sedes.csv"), "nombre")
    assert columna(planilla(dentro, "clinicas_de_derivacion.csv"), "nombre") == [
        "Urgencias de Clínica del Parque"
    ]
    entero = b"".join(dentro.read(nombre) for nombre in dentro.namelist())
    assert ajena.nombre.encode("utf-8") not in entero


# --- Quién puede -----------------------------------------------------------


@pytest.mark.parametrize("rol", [Rol.RECEPCION, Rol.VETERINARIO])
@pytest.mark.parametrize("url", [EXPORTACION, DESCARGA, CIERRE])
def test_quien_no_es_admin_no_exporta_ni_cierra(client, rol, url):
    client.force_login(UsuarioFactory(rol=rol))

    assert client.post(reverse(url)).status_code == 403


@pytest.mark.parametrize("url", [EXPORTACION, DESCARGA, CIERRE])
def test_sin_sesion_se_va_al_login(client, url):
    respuesta = client.post(reverse(url))

    assert respuesta.status_code == 302
    assert reverse("account_login") in respuesta["Location"]


def test_la_descarga_no_se_pide_por_una_direccion(client):
    """La casilla de la dirección adivinable: no hay ninguna. El archivo no queda
    en el disco ni en la base, se compone contra el POST de quien lo pide."""
    admin(client)

    assert client.get(reverse(DESCARGA)).status_code == 405


# --- Que salga de a poco ---------------------------------------------------


def test_los_objetos_de_la_clinica_se_piden_de_a_tandas(django_assert_num_queries):
    """La casilla de la memoria, en la costura por donde pasan los ocho lectores.

    Lo que se comprueba es lo único que se puede comprobar desde aquí: que lo
    devuelto es un cursor que todavía no ha leído nada, y no la tabla ya traída.
    Que además la memoria se quede donde tiene que quedarse con tres mil Tutores
    se mide aparte y a mano — está en `deuda-tecnica.md`, con el número —, porque
    poblar una clínica entera costaría minutos en cada ejecución de la suite.
    """
    clinica = una_clinica_poblada("Clínica del Parque")

    with django_assert_num_queries(0):
        leyendo = _de_la_clinica(Tutor, clinica)

    assert not isinstance(leyendo, list)
    assert next(leyendo).nombre == "Clínica del Parque"


def test_el_archivo_sale_por_trozos_y_ninguno_es_el_archivo_entero():
    """La otra mitad de la misma casilla: el zip se va soltando mientras se
    escribe. El tamaño del trozo se baja desde aquí porque comprobarlo con el
    tamaño de verdad pediría poblar una clínica entera dentro de un test."""
    clinica = una_clinica_poblada("Clínica del Parque")
    for cual in range(200):
        TutorFactory(clinic=clinica, nombre=f"Tutor {cual}")

    trozos = list(como_un_zip(HOJAS, clinica, timezone.now(), trozo=1024))

    assert len(trozos) > 3
    assert max(len(trozo) for trozo in trozos) < sum(len(trozo) for trozo in trozos)


def test_la_respuesta_va_saliendo_en_vez_de_componerse_entera(client):
    admin(client)

    descarga = client.post(reverse(DESCARGA))

    assert isinstance(descarga, StreamingHttpResponse)


def test_de_la_descarga_no_queda_copia_en_ninguna_cache(client):
    """La otra mitad de «ni una dirección permanente»: sin esto, el navegador o un
    proxy por medio pueden guardarse el zip y volver a servirlo."""
    admin(client)

    descarga = client.post(reverse(DESCARGA))

    assert descarga["Cache-Control"] == "private, no-store"


def test_la_descarga_se_llama_con_la_fecha_de_la_clinica_y_no_la_de_la_base(client):
    """Las horas se guardan en UTC y se presentan en `America/Santiago`
    (`CLAUDE.md`): una exportación de las nueve y media de la noche en Santiago
    no puede guardarse con la fecha de mañana."""
    usuario = admin(client)
    # Las diez de la noche del 26 en Santiago son ya el 27 en la base.
    de_noche = dt.datetime(2026, 8, 27, 2, 0, tzinfo=dt.timezone.utc)

    assert "2026-08-26" in se_llama(usuario.clinic, de_noche)
    assert "2026-08-27" not in se_llama(usuario.clinic, de_noche)


# --- El Registro de acceso -------------------------------------------------


def test_la_exportacion_queda_en_el_registro_de_acceso(client):
    """Es el acceso masivo a datos personales que más importa poder demostrar:
    este Usuario se llevó todos los Tutores de esta Clínica a esta hora."""
    usuario = admin(client)

    client.post(reverse(DESCARGA))

    anotados = RegistroDeAcceso.de_todas_las_clinicas.filter(usuario=usuario)
    assert set(anotados.values_list("tipo_de_objeto", flat=True)) == {
        modelo._meta.label for modelo in de_quienes_son_los_datos()
    }
    assert set(anotados.values_list("accion", flat=True)) == {Accion.LECTURA}
    assert set(anotados.values_list("identificador", flat=True)) == {EL_CONJUNTO}
    assert all(anotado.clinic == usuario.clinic for anotado in anotados)


def test_no_se_anota_la_lectura_de_los_catalogos(client):
    """Una especie no es dato de nadie, y anotarla sería ruido en la tabla que
    tiene que valer como prueba."""
    admin(client)

    client.post(reverse(DESCARGA))

    assert not RegistroDeAcceso.de_todas_las_clinicas.filter(
        tipo_de_objeto__startswith="patients.Especie"
    ).exists()


# --- Cerrar la Clínica -----------------------------------------------------


def test_la_pagina_ofrece_cerrar_la_clinica(client):
    """La casilla del ticket: que el sistema lo ofrezca, en vez de que el admin
    descubra el `IntegrityError` de intentar borrarla."""
    admin(client)

    pagina = client.get(reverse(EXPORTACION))

    assert pagina.status_code == 200
    assert reverse(CIERRE).encode("utf-8") in pagina.content


def test_cerrar_la_clinica_la_deja_sin_acceso(client):
    usuario = admin(client)
    recepcion = UsuarioFactory(clinic=usuario.clinic, rol=Rol.RECEPCION)

    respuesta = client.post(
        reverse(CIERRE), {"nombre": usuario.clinic.nombre}, follow=True
    )

    assert respuesta.status_code == 200
    clinica = Clinica.objects.get(pk=usuario.clinic.pk)
    assert clinica.esta_cerrada
    sin_acceso = get_user_model().objects.filter(clinic=clinica, is_active=False)
    assert set(sin_acceso.values_list("pk", flat=True)) == {usuario.pk, recepcion.pk}


def test_cerrar_la_clinica_no_borra_sus_datos(client):
    """«Se exporta y se cierra, no se borra»: los Tutores, los Pacientes y el
    Registro de acceso se quedan donde estaban."""
    usuario = admin(client)
    tutor = TutorFactory(clinic=usuario.clinic)
    vinculo = VinculoFactory(tutor=tutor)

    client.post(reverse(CIERRE), {"nombre": usuario.clinic.nombre})

    assert tutor.__class__.de_todas_las_clinicas.filter(pk=tutor.pk).exists()
    assert vinculo.paciente.__class__.de_todas_las_clinicas.filter(
        pk=vinculo.paciente_id
    ).exists()
    assert RegistroDeAcceso.de_todas_las_clinicas.filter(usuario=usuario).exists()


def test_el_cierre_queda_en_el_registro_de_acceso(client):
    usuario = admin(client)

    client.post(reverse(CIERRE), {"nombre": usuario.clinic.nombre})

    anotado = RegistroDeAcceso.de_todas_las_clinicas.get(
        usuario=usuario, accion=Accion.MODIFICACION
    )
    assert anotado.tipo_de_objeto == "tenancy.Clinica"
    assert anotado.identificador == str(usuario.clinic.pk)


def test_quien_cierra_su_clinica_deja_de_poder_entrar(client):
    usuario = admin(client)

    client.post(reverse(CIERRE), {"nombre": usuario.clinic.nombre})

    assert client.get(reverse(EXPORTACION)).status_code == 302
    assert not client.login(email=usuario.email, password="gatabase-de-prueba-2026")


def test_el_nombre_mal_escrito_no_cierra_nada(client):
    """Escribir el nombre no es una traba: es lo que obliga a mirar qué Clínica se
    está cerrando, que es la equivocación de quien administra dos."""
    usuario = admin(client)

    respuesta = client.post(reverse(CIERRE), {"nombre": "la de al lado"})

    assert respuesta.status_code == 200
    assert not Clinica.objects.get(pk=usuario.clinic.pk).esta_cerrada
    assert get_user_model().objects.get(pk=usuario.pk).is_active


def test_cerrar_una_clinica_no_toca_a_la_de_al_lado(client):
    usuario = admin(client)
    ajena = una_clinica_poblada("Clínica del Río")
    UsuarioFactory(clinic=ajena, rol=Rol.RECEPCION)

    client.post(reverse(CIERRE), {"nombre": usuario.clinic.nombre})

    assert not Clinica.objects.get(pk=ajena.pk).esta_cerrada
    assert get_user_model().objects.filter(clinic=ajena, is_active=True).exists()

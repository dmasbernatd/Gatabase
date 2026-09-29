"""Un Tutor pide sus datos, o pide que los borren, y la clínica lo atiende.

Los tests entran por HTTP como entra el admin: abre la ficha, pulsa un botón y
escribe un nombre. Lo que se comprueba es lo que la ley pide poder demostrar —que
los datos personales ya no están, que la Historia del animal sigue entera, que
consta quién lo hizo— y no cómo lo guarda la base.
"""

import io

import pytest
from django.db import models
from django.urls import reverse

from apps.audit.models import Accion, RegistroDeAcceso
from apps.patients.forms import TraspasoForm, VinculoForm
from apps.patients.models import Paciente
from apps.tenancy.models import Rol
from apps.tutors.consentimiento import Canal, se_puede_contactar
from apps.tutors.models import Suprimido, Tutor, Vinculo
from tests.factories import (
    ClinicaFactory,
    PacienteFactory,
    TutorFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db

DERECHOS = "tutors:derechos"
DATOS = "tutors:datos_del_titular"
ANONIMIZAR = "tutors:anonimizar"

ANONIMIZADO = "Tutor anonimizado"

# Datos que se reconocen en cualquier página: si alguno sigue a la vista después
# de anonimizar, el test lo encuentra buscando el texto tal cual.
DE_CAMILA = {
    "nombre": "Camila",
    "apellidos": "Rojas Pizarro",
    "rut": "123456785",
    "telefono": "+56987654321",
    "email": "camila.rojas@correo.example",
    "direccion": "Av. Grecia 2001, Ñuñoa",
}
RUT_A_LA_CHILENA = "12.345.678-5"


def entra(client, rol, clinica=None, **datos):
    datos = {"nombre": "Ignacio", "apellidos": "Soto"} | datos
    usuario = UsuarioFactory(rol=rol, **({"clinic": clinica} if clinica else {}), **datos)
    client.force_login(usuario)
    return usuario


def admin(client, clinica=None, **datos):
    """Quien atiende los derechos del titular: es cosa del admin.

    Con un nombre propio y no el de la fábrica, que es Camila Rojas: la cabecera
    de cada página dice quién está trabajando, y ahí «Camila» no sería el Tutor.
    """
    datos = {"nombre": "Paula", "apellidos": "Araya"} | datos
    return entra(client, Rol.ADMIN, clinica, **datos)


def camila_con_dos_animales(clinica):
    """El caso del ticket: un Tutor con dos Pacientes, uno de cada especie."""
    tutor = TutorFactory(clinic=clinica, **DE_CAMILA)
    rocco = PacienteFactory(clinic=clinica, nombre="Rocco", raza="Quiltro", color="Negro")
    luna = PacienteFactory(clinic=clinica, nombre="Luna", especie="gato", raza="Siamés")
    tutor.se_hace_cargo_de(rocco)
    tutor.se_hace_cargo_de(luna)
    tutor.deja_dicho_sobre_el_contacto(Canal.WHATSAPP, otorgado=True)
    return tutor, rocco, luna


def anonimizar(client, tutor, escrito=None):
    return client.post(
        reverse(ANONIMIZAR, args=[tutor.pk]),
        {"nombre": str(tutor) if escrito is None else escrito},
    )


def como_esta(paciente):
    """Todo lo que el Paciente guarda, para compararlo antes y después."""
    return {
        campo.name: getattr(paciente, campo.attname) for campo in Paciente._meta.concrete_fields
    }


def anotaciones_sobre(tutor, **condiciones):
    return RegistroDeAcceso.de_todas_las_clinicas.filter(
        tipo_de_objeto="tutors.Tutor", identificador=str(tutor.pk), **condiciones
    )


def documento(client, tutor):
    """El documento que se le entrega al Tutor, ya leído como texto."""
    respuesta = client.post(reverse(DATOS, args=[tutor.pk]))
    assert respuesta.status_code == 200
    return respuesta.content.decode()


# --- Anonimizar -----------------------------------------------------------


def test_anonimizar_suprime_sus_datos_y_deja_a_sus_dos_pacientes_enteros(client):
    """La casilla del ticket, entera: los datos personales desaparecen y los dos
    Pacientes siguen completos, a cargo del mismo Tutor —ahora anonimizado— y
    consultables desde su ficha."""
    usuario = admin(client)
    tutor, rocco, luna = camila_con_dos_animales(usuario.clinic)
    antes = {paciente.pk: como_esta(paciente) for paciente in (rocco, luna)}

    respuesta = anonimizar(client, tutor)

    assert respuesta.status_code == 302
    tutor.refresh_from_db()
    assert all(getattr(tutor, dato) == "" for dato in Tutor.DATOS_PERSONALES)
    assert tutor.esta_anonimizado
    for paciente in (rocco, luna):
        paciente.refresh_from_db()
        assert como_esta(paciente) == antes[paciente.pk]
        assert paciente.responsable == tutor

        ficha = client.get(reverse("patients:ficha", args=[paciente.pk]))
        assert ficha.status_code == 200
        contenido = ficha.content.decode()
        assert paciente.nombre in contenido
        assert ANONIMIZADO in contenido
        assert "Camila" not in contenido
        assert DE_CAMILA["telefono"] not in contenido


def test_los_vinculos_y_los_consentimientos_se_quedan(client):
    """Quién trajo al animal es parte de su Historia, y lo que el Tutor dijo del
    contacto es la evidencia de los mensajes que ya salieron: ninguno de los dos
    nombra ya a nadie, y ninguno se borra."""
    usuario = admin(client)
    tutor, rocco, _ = camila_con_dos_animales(usuario.clinic)
    # Un animal que fue suyo y ya no: lo trajo, y después lo tiene otro.
    toby = PacienteFactory(clinic=usuario.clinic, nombre="Toby")
    fue_suyo = tutor.se_hace_cargo_de(toby)
    TutorFactory(clinic=usuario.clinic).se_hace_cargo_de(toby, responsable=True)
    fue_suyo.refresh_from_db()
    fue_suyo.cerrar()

    anonimizar(client, tutor)

    assert Vinculo.de_todas_las_clinicas.filter(tutor=tutor).count() == 3
    assert tutor.lo_que_ha_dicho_del_contacto.count() == 1


def test_la_anonimizacion_consta_con_quien_la_hizo_y_cuando(client):
    usuario = admin(client)
    tutor, _, _ = camila_con_dos_animales(usuario.clinic)

    anonimizar(client, tutor)

    anotacion = anotaciones_sobre(tutor, accion=Accion.ANONIMIZACION).get()
    assert anotacion.usuario == usuario
    tutor.refresh_from_db()
    # El mismo instante en los dos sitios, de la misma transacción: la ficha dice
    # cuándo, y el Registro dice cuándo y quién.
    assert abs(anotacion.momento - tutor.anonimizado).total_seconds() < 1


def test_sin_escribir_su_nombre_no_se_anonimiza(client):
    """Es lo único de la aplicación que no se deshace, y por eso se confirma
    escribiendo de quién es la ficha."""
    usuario = admin(client)
    tutor, _, _ = camila_con_dos_animales(usuario.clinic)

    respuesta = anonimizar(client, tutor, escrito="Camila")

    assert respuesta.status_code == 200
    assert "No se ha anonimizado nada" in respuesta.content.decode()
    tutor.refresh_from_db()
    assert tutor.nombre == "Camila"
    assert not tutor.esta_anonimizado
    assert not anotaciones_sobre(tutor, accion=Accion.ANONIMIZACION).exists()


def test_el_nombre_se_confirma_sin_fijarse_en_los_espacios(client):
    usuario = admin(client)
    tutor, _, _ = camila_con_dos_animales(usuario.clinic)

    anonimizar(client, tutor, escrito="  Camila   Rojas Pizarro ")

    tutor.refresh_from_db()
    assert tutor.esta_anonimizado


def test_un_tutor_anonimizado_no_se_anonimiza_dos_veces(client):
    """La segunda vez no hay nombre que escribir ni nada que suprimir, y una
    segunda anotación diría que se hizo algo que no se hizo."""
    usuario = admin(client)
    tutor, _, _ = camila_con_dos_animales(usuario.clinic)
    anonimizar(client, tutor)
    tutor.refresh_from_db()

    respuesta = anonimizar(client, tutor, escrito=ANONIMIZADO)

    assert respuesta.status_code == 404
    assert anotaciones_sobre(tutor, accion=Accion.ANONIMIZACION).count() == 1


def test_la_anonimizacion_no_se_pide_por_un_enlace(client):
    usuario = admin(client)
    tutor, _, _ = camila_con_dos_animales(usuario.clinic)

    assert client.get(reverse(ANONIMIZAR, args=[tutor.pk])).status_code == 405


@pytest.mark.parametrize("rol", [Rol.RECEPCION, Rol.VETERINARIO])
def test_solo_el_admin_atiende_los_derechos_del_titular(client, rol):
    """Recepción y veterinario atienden al Tutor, pero no le entregan sus datos
    ni los suprimen: son dos gestos del admin, y uno no tiene vuelta atrás."""
    usuario = entra(client, rol)
    tutor, _, _ = camila_con_dos_animales(usuario.clinic)

    assert client.get(reverse(DERECHOS, args=[tutor.pk])).status_code == 403
    assert client.post(reverse(DATOS, args=[tutor.pk])).status_code == 403
    assert anonimizar(client, tutor).status_code == 403
    tutor.refresh_from_db()
    assert not tutor.esta_anonimizado


def test_la_ficha_solo_le_ofrece_los_derechos_al_admin(client):
    usuario = entra(client, Rol.RECEPCION)
    tutor, _, _ = camila_con_dos_animales(usuario.clinic)
    url_de_derechos = reverse(DERECHOS, args=[tutor.pk])

    assert url_de_derechos not in client.get(tutor.get_absolute_url()).content.decode()

    admin(client, usuario.clinic)
    assert url_de_derechos in client.get(tutor.get_absolute_url()).content.decode()


def test_un_tutor_de_otra_clinica_no_existe(client):
    admin(client)
    ajeno, _, _ = camila_con_dos_animales(ClinicaFactory())

    assert client.get(reverse(DERECHOS, args=[ajeno.pk])).status_code == 404
    assert client.post(reverse(DATOS, args=[ajeno.pk])).status_code == 404
    assert anonimizar(client, ajeno).status_code == 404
    ajeno.refresh_from_db()
    assert not ajeno.esta_anonimizado


# --- Lo que no se rompe ---------------------------------------------------


def test_el_fichero_de_tutores_lo_sigue_listando_con_su_ficha_a_un_clic(client):
    usuario = admin(client)
    tutor, _, _ = camila_con_dos_animales(usuario.clinic)
    anonimizar(client, tutor)

    listado = client.get(reverse("tutors:lista"))

    assert listado.status_code == 200
    contenido = listado.content.decode()
    assert f'href="{tutor.get_absolute_url()}">{ANONIMIZADO}<' in contenido
    assert "Camila" not in contenido


def test_nadie_lo_encuentra_por_lo_que_era(client):
    """Ni el fichero ni el mostrador: buscar por su nombre o su teléfono ya no
    trae nada suyo, y buscar al animal lo trae entero."""
    usuario = admin(client)
    tutor, _, _ = camila_con_dos_animales(usuario.clinic)
    anonimizar(client, tutor)

    en_el_fichero = client.get(reverse("tutors:lista"), {"q": "Rojas Pizarro"})
    assert tutor.get_absolute_url() not in en_el_fichero.content.decode()
    por_telefono = client.get(reverse("buscar"), {"q": DE_CAMILA["telefono"]})
    assert "Rocco" not in por_telefono.content.decode()

    por_el_animal = client.get(reverse("buscar"), {"q": "Rocco"})
    assert por_el_animal.status_code == 200
    assert "Rocco" in por_el_animal.content.decode()
    assert ANONIMIZADO in por_el_animal.content.decode()


def test_su_ficha_se_abre_y_no_ofrece_volver_a_llenarla(client):
    """Corregirla, tomarle el consentimiento o registrarle un animal sería
    volver a identificarlo: la ficha no lo ofrece, y las páginas no existen."""
    usuario = admin(client)
    tutor, rocco, _ = camila_con_dos_animales(usuario.clinic)
    anonimizar(client, tutor)

    ficha = client.get(tutor.get_absolute_url())

    assert ficha.status_code == 200
    contenido = ficha.content.decode()
    assert ANONIMIZADO in contenido
    assert "Rocco" in contenido
    for ruta in ("tutors:editar", "tutors:consentimiento", "patients:crear"):
        url = reverse(ruta, args=[tutor.pk])
        assert url not in contenido
        assert client.get(url).status_code == 404


def test_no_se_le_suma_ni_se_le_pasa_ningun_animal(client):
    usuario = admin(client)
    tutor, _, _ = camila_con_dos_animales(usuario.clinic)
    otro = PacienteFactory(clinic=usuario.clinic)
    anonimizar(client, tutor)

    sumar = VinculoForm(clinica=usuario.clinic, paciente=otro)
    traspasar = TraspasoForm(clinica=usuario.clinic, paciente=otro)

    assert tutor not in sumar.fields["tutor"].queryset
    assert tutor not in traspasar.fields["tutor"].queryset


def test_a_un_tutor_anonimizado_no_se_le_escribe(client):
    """Había dicho que sí por WhatsApp, y eso se conserva como evidencia de lo
    que ya se le mandó; no como permiso para lo siguiente."""
    usuario = admin(client)
    tutor, _, _ = camila_con_dos_animales(usuario.clinic)
    assert se_puede_contactar(tutor, Canal.WHATSAPP)

    anonimizar(client, tutor)
    tutor.refresh_from_db()

    assert not se_puede_contactar(tutor, Canal.WHATSAPP)


# --- El Registro sobrevive ------------------------------------------------


def test_el_registro_de_acceso_del_tutor_sobrevive_a_su_anonimizacion(client):
    """El Registro es la evidencia del tratamiento: quién vio los datos de esta
    persona mientras existieron. Anonimizarla no puede llevárselo, y el
    documento que se le entregue después tiene que seguir diciéndolo."""
    clinica = ClinicaFactory()
    tutor, _, _ = camila_con_dos_animales(clinica)
    entra(client, Rol.RECEPCION, clinica, nombre="Ignacio", apellidos="Soto")
    client.get(tutor.get_absolute_url())
    client.get(reverse("tutors:editar", args=[tutor.pk]))
    antes = set(anotaciones_sobre(tutor).values_list("pk", flat=True))
    assert len(antes) == 2

    admin(client, clinica)
    anonimizar(client, tutor)

    despues = set(anotaciones_sobre(tutor).values_list("pk", flat=True))
    assert antes <= despues
    contenido = documento(client, tutor)
    assert "Ignacio Soto" in contenido
    assert "Paula Araya" in contenido
    assert "anonimización" in contenido
    assert "Camila" not in contenido
    assert RUT_A_LA_CHILENA not in contenido


# --- Entregarle sus datos -------------------------------------------------


def test_el_admin_le_entrega_al_tutor_todo_lo_que_consta_de_el(client):
    usuario = admin(client)
    tutor, _, _ = camila_con_dos_animales(usuario.clinic)

    respuesta = client.post(reverse(DATOS, args=[tutor.pk]))

    assert respuesta["Content-Type"].startswith("text/html")
    assert "attachment" in respuesta["Content-Disposition"]
    # El nombre del archivo viaja en una cabecera: no lleva el de la persona.
    assert "Camila" not in respuesta["Content-Disposition"]
    assert "no-store" in respuesta["Cache-Control"]
    contenido = respuesta.content.decode()
    for dato in ("Camila", "Rojas Pizarro", RUT_A_LA_CHILENA, "+56987654321", "Ñuñoa"):
        assert dato in contenido
    assert "camila.rojas@correo.example" in contenido
    assert "Rocco" in contenido and "Luna" in contenido
    assert "WhatsApp" in contenido


def test_el_documento_trae_quien_vio_su_ficha_y_nada_de_los_demas(client):
    """Su Registro, y no el de la Clínica: lo que se vio de otro Tutor es dato de
    ese otro, y entregárselo a este sería otra filtración."""
    clinica = ClinicaFactory()
    tutor, _, _ = camila_con_dos_animales(clinica)
    otro = TutorFactory(clinic=clinica)
    entra(client, Rol.RECEPCION, clinica, nombre="Ignacio", apellidos="Soto")
    client.get(tutor.get_absolute_url())
    entra(client, Rol.VETERINARIO, clinica, nombre="Rodrigo", apellidos="Fuentes")
    client.get(otro.get_absolute_url())

    admin(client, clinica)
    contenido = documento(client, tutor)

    assert "Ignacio Soto" in contenido
    assert "Rodrigo Fuentes" not in contenido


def test_entregarle_sus_datos_queda_en_el_registro(client):
    usuario = admin(client)
    tutor, rocco, luna = camila_con_dos_animales(usuario.clinic)

    documento(client, tutor)

    assert anotaciones_sobre(tutor, accion=Accion.LECTURA, usuario=usuario).exists()
    nombrados = RegistroDeAcceso.de_todas_las_clinicas.filter(
        tipo_de_objeto="patients.Paciente", usuario=usuario
    ).values_list("identificador", flat=True)
    assert {str(rocco.pk), str(luna.pk)} <= set(nombrados)


def test_el_documento_no_se_pide_por_un_enlace(client):
    """Se compone contra el POST de quien lo pide y no queda en ninguna parte,
    igual que la exportación de la Clínica."""
    usuario = admin(client)
    tutor, _, _ = camila_con_dos_animales(usuario.clinic)

    assert client.get(reverse(DATOS, args=[tutor.pk])).status_code == 405


# --- Lo que no vuelve -----------------------------------------------------

# La planilla con la que la clínica llegó, que el README anima a volver a subir
# «las veces que haga falta».
CABECERA_DE_TUTORES = "nombre,apellidos,rut,telefono,correo,direccion"
CAMILA_EN_LA_PLANILLA = "Camila,Rojas Pizarro,12.345.678-5,9 8765 4321,,Av. Grecia 2001"
CAMILA_SIN_RUT = "Camila,Rojas Pizarro,,9 8765 4321,,Av. Grecia 2001"


def reimportar(client, *filas):
    """Sube la planilla de Tutores y la confirma, como el admin la vuelve a subir."""
    archivo = io.BytesIO(("\n".join([CABECERA_DE_TUTORES, *filas]) + "\n").encode("utf-8"))
    archivo.name = "clientes.csv"
    previa = client.post(reverse("imports:tutores"), {"archivo": archivo}, follow=True)
    client.post(reverse("imports:confirmar"), follow=True)
    return previa.content.decode()


def suprimida(client):
    """Camila pidió que la borraran, y el admin lo hizo."""
    usuario = admin(client)
    tutor, _, _ = camila_con_dos_animales(usuario.clinic)
    anonimizar(client, tutor)
    return usuario.clinic


def test_la_planilla_de_siempre_no_la_vuelve_a_registrar(client):
    """El caso de la deuda del 20: la clínica sube otra vez la planilla con la
    que llegó, y quien pidió que la borraran no vuelve a entrar como ficha nueva."""
    clinica = suprimida(client)

    previa = reimportar(client, CAMILA_EN_LA_PLANILLA)

    assert "pidió que se suprimieran sus datos" in previa
    assert not Tutor.de_todas_las_clinicas.filter(clinic=clinica, nombre="Camila").exists()


def test_tampoco_vuelve_por_su_nombre_y_su_telefono(client):
    """Una tanda sin la columna del RUT la reconoce igual que el importador
    reconoce a cualquiera: por el nombre completo con el teléfono."""
    clinica = suprimida(client)

    reimportar(client, CAMILA_SIN_RUT)

    assert not Tutor.de_todas_las_clinicas.filter(clinic=clinica, nombre="Camila").exists()


def test_otra_persona_de_la_misma_casa_y_el_mismo_nombre_si_entra(client):
    """La reserva del importador vale también aquí: mismo nombre y mismo
    teléfono con otro RUT es otra persona —la hija—, y no pidió nada."""
    clinica = suprimida(client)

    reimportar(client, "Camila,Rojas Pizarro,9.876.543-3,9 8765 4321,,Av. Grecia 2001")

    assert Tutor.de_todas_las_clinicas.filter(clinic=clinica, nombre="Camila").exists()


def test_rotar_la_llave_dejando_la_anterior_no_olvida_a_nadie(client, settings):
    """Las huellas se hicieron con la llave de entonces, y se comparan con cada
    una de las que el despliegue todavía acepta."""
    clinica = suprimida(client)
    settings.SECRET_KEY_FALLBACKS = [settings.SECRET_KEY]
    settings.SECRET_KEY = "la-llave-de-despues-de-rotar"

    reimportar(client, CAMILA_SIN_RUT)

    assert not Tutor.de_todas_las_clinicas.filter(clinic=clinica, nombre="Camila").exists()


def test_lo_que_se_recuerda_no_dice_quien_era(client):
    """Para reconocerla no se guarda lo que se suprimió: ni su RUT ni su nombre
    ni su teléfono están en ninguna columna, y lo guardado no apunta a su ficha."""
    clinica = suprimida(client)

    guardado = [
        str(valor)
        for fila in Suprimido.de_todas_las_clinicas.filter(clinic=clinica).values()
        for valor in fila.values()
    ]

    assert guardado
    for dato in ("123456785", "12.345.678", "Camila", "Rojas", "987654321"):
        assert not any(dato in valor for valor in guardado)
    assert not any(isinstance(campo, models.ForeignKey) and campo.related_model is Tutor
                   for campo in Suprimido._meta.get_fields())


def test_en_otra_clinica_no_se_la_reconoce(client):
    """Lo que pidió lo pidió a esta Clínica. Otra que la tenga en su planilla es
    otro responsable, y la huella de aquí ni siquiera coincide con la de allí."""
    suprimida(client)
    otra = ClinicaFactory()
    admin(client, otra)

    reimportar(client, CAMILA_EN_LA_PLANILLA)

    assert Tutor.de_todas_las_clinicas.filter(clinic=otra, nombre="Camila").exists()


def test_en_el_mostrador_si_se_la_puede_volver_a_registrar(client):
    """Si vuelve ella misma a la consulta, la ficha nueva es cosa suya: lo que
    se impide es que la planilla antigua la resucite sin que nadie se lo pida."""
    clinica = suprimida(client)

    client.post(reverse("tutors:crear"), {k: v for k, v in DE_CAMILA.items()})

    assert Tutor.de_todas_las_clinicas.filter(clinic=clinica, rut=DE_CAMILA["rut"]).exists()

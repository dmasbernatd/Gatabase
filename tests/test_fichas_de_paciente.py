"""La ficha de un Paciente: registrarlo, abrirla, corregirla y decir quién responde.

Es donde el sistema empieza a saber de qué animal habla un Tutor cuando llama.
Los tests entran por HTTP como entra recepción —con un Usuario autenticado— y
miran lo que la página enseña y lo que queda guardado.

Lo que no se ve de otra Clínica está en `test_aislamiento_por_clinica.py`, y lo
que el Registro de acceso guarda de todo esto, aquí y en
`test_registro_de_acceso.py`.
"""

import html as marcado
import re

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.audit.models import EL_CONJUNTO, Accion, RegistroDeAcceso
from apps.patients.catalogo import MESTIZO, RAZAS, Especie
from apps.patients.models import Paciente
from apps.tutors.models import Tutor
from tests.factories import PacienteFactory, TutorFactory, UsuarioFactory, VinculoFactory

pytestmark = pytest.mark.django_db

DATOS_DEL_PACIENTE = {
    "nombre": "Rocco",
    "especie": Especie.PERRO,
    "raza": MESTIZO,
    "sexo": "macho",
    "fecha_de_nacimiento": "2020-03-15",
    "color": "Negro con manchas blancas",
    "observaciones": "Muerde cuando le tocan la pata trasera.",
}


def recepcion(client):
    """Quien está en el mostrador: el rol que registra y corrige fichas."""
    usuario = UsuarioFactory(rol="recepcion")
    client.force_login(usuario)
    return usuario


def opciones_de(contenido, campo):
    """Los valores que un desplegable de la página ofrece elegir.

    Leerlos de lo servido y no de las `choices` del modelo es lo que comprueba
    que el catálogo cerrado llega cerrado hasta el navegador.
    """
    desplegable = re.search(rf'<select[^>]*name="{campo}".*?</select>', contenido, re.S)
    assert desplegable, f"La página no ofrece ningún desplegable «{campo}»"
    return [
        marcado.unescape(valor) for valor in re.findall(r'value="([^"]*)"', desplegable.group())
    ]


def sugerencias_de_raza(contenido):
    """Las razas que la página ofrece autocompletar."""
    lista = re.search(r"<datalist.*?</datalist>", contenido, re.S)
    assert lista, "La página no ofrece ninguna lista de razas"
    return [marcado.unescape(valor) for valor in re.findall(r'value="([^"]*)"', lista.group())]


def anotaciones_sobre(objeto, accion):
    return RegistroDeAcceso.de_todas_las_clinicas.filter(
        tipo_de_objeto=objeto._meta.label, identificador=str(objeto.pk), accion=accion
    )


def registrar(client, tutor, **cambios):
    """Registra un Paciente desde la ficha de ese Tutor, como recepción."""
    return client.post(reverse("patients:crear", args=[tutor.pk]), DATOS_DEL_PACIENTE | cambios)


# --- Registrar un Paciente ------------------------------------------------


def test_recepcion_registra_un_paciente_desde_la_ficha_de_su_tutor(client):
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic, nombre="Camila", apellidos="Rojas")

    respuesta = registrar(client, tutor)

    paciente = Paciente.de_todas_las_clinicas.get()
    assert respuesta.status_code == 302
    assert paciente.nombre == "Rocco"
    assert paciente.especie == Especie.PERRO
    assert paciente.raza == MESTIZO
    assert paciente.sexo == "macho"
    assert str(paciente.fecha_de_nacimiento) == "2020-03-15"
    assert paciente.color == "Negro con manchas blancas"
    assert paciente.observaciones.startswith("Muerde")


def test_el_tutor_que_trae_al_paciente_queda_como_responsable(client):
    """Un Paciente del que no responde nadie no dice a quién llamar, y el animal
    llega al mostrador con alguien: ese alguien es el responsable."""
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)

    registrar(client, tutor)

    paciente = Paciente.de_todas_las_clinicas.get()
    assert paciente.responsable == tutor


def test_registrar_un_paciente_deja_constancia_de_la_creacion(client):
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)

    registrar(client, tutor)

    paciente = Paciente.de_todas_las_clinicas.get()
    assert anotaciones_sobre(paciente, Accion.CREACION).get().usuario == usuario


def test_un_paciente_sin_nombre_no_se_guarda(client):
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)

    respuesta = registrar(client, tutor, nombre="")

    assert respuesta.status_code == 200
    assert not Paciente.de_todas_las_clinicas.exists()


def test_un_paciente_sin_especie_no_se_guarda(client):
    """De la especie dependen protocolos y formularios: no hay Paciente sin ella."""
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)

    respuesta = registrar(client, tutor, especie="")

    assert respuesta.status_code == 200
    assert not Paciente.de_todas_las_clinicas.exists()


def test_el_resto_de_los_datos_del_paciente_son_opcionales(client):
    """Un animal recogido en la calle llega sin fecha de nacimiento y sin que
    nadie le haya mirado el sexo. Exigirlo sería exigir que se lo inventen."""
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)

    respuesta = client.post(
        reverse("patients:crear", args=[tutor.pk]),
        {"nombre": "Sin nombre todavía", "especie": Especie.GATO},
    )

    assert respuesta.status_code == 302
    assert Paciente.de_todas_las_clinicas.get().raza == ""


def test_una_fecha_de_nacimiento_que_no_ha_llegado_no_se_guarda(client):
    """El año tecleado de más es el error más fácil de cometer y el más difícil
    de ver después: lo único raro queda siendo una edad imposible."""
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)

    respuesta = registrar(client, tutor, fecha_de_nacimiento="2099-01-01")

    assert respuesta.status_code == 200
    assert not Paciente.de_todas_las_clinicas.exists()


# --- Catálogo de especies -------------------------------------------------


def test_el_formulario_ofrece_las_especies_del_catalogo_y_ninguna_mas(client):
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)

    contenido = client.get(reverse("patients:crear", args=[tutor.pk])).content.decode()

    ofrecidas = {valor for valor in opciones_de(contenido, "especie") if valor}
    assert ofrecidas == set(Especie.values)


def test_los_desplegables_no_ensenan_el_rotulo_en_ingles_de_django(client):
    """El de la opción vacía lo pone Django y llega sin traducir al es-CL. Es el
    único texto de estas páginas que no pasa por el catálogo del proyecto, así
    que el test de plantillas no lo ve."""
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)

    contenido = client.get(reverse("patients:crear", args=[tutor.pk])).content.decode()

    assert "Select an option" not in contenido
    assert "Elija una especie" in contenido


def test_una_especie_que_no_esta_en_el_catalogo_no_se_guarda(client):
    """El catálogo es cerrado: «perrito» y «canino» serían dos especies para las
    estadísticas y ninguna para los protocolos."""
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)

    respuesta = registrar(client, tutor, especie="dragón")

    assert respuesta.status_code == 200
    assert not Paciente.de_todas_las_clinicas.exists()


# --- Catálogo de razas ----------------------------------------------------


def test_mestizo_es_una_raza_de_primera_clase_del_perro_y_del_gato():
    """En Chile es el caso más frecuente, no la excepción."""
    assert RAZAS[Especie.PERRO][0] == MESTIZO
    assert RAZAS[Especie.GATO][0] == MESTIZO


def test_las_razas_que_se_sugieren_son_las_de_la_especie(client):
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic, especie=Especie.GATO)

    contenido = client.get(reverse("patients:editar", args=[paciente.pk])).content.decode()

    sugeridas = sugerencias_de_raza(contenido)
    assert "Siamés" in sugeridas
    assert "Labrador Retriever" not in sugeridas


def test_la_casilla_de_la_raza_apunta_a_la_lista_que_la_pagina_pinta(client):
    """Si el `list` del campo y el `id` de la lista dejaran de llamarse igual, el
    autocompletado se apagaría sin que fallara nada más."""
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    contenido = client.get(reverse("patients:editar", args=[paciente.pk])).content.decode()

    lista = re.search(r'<datalist id="([^"]+)"', contenido)
    assert lista, "La página no ofrece ninguna lista de razas"
    assert re.search(rf'name="raza"[^>]*list="{lista.group(1)}"', contenido) or re.search(
        rf'list="{lista.group(1)}"[^>]*name="raza"', contenido
    )


def test_elegir_otra_especie_trae_sus_razas_sin_recargar_la_pagina(client):
    recepcion(client)

    contenido = client.get(reverse("patients:razas"), {"especie": Especie.GATO}).content.decode()

    sugeridas = sugerencias_de_raza(contenido)
    assert "Siamés" in sugeridas
    assert "Labrador Retriever" not in sugeridas


def test_una_raza_del_catalogo_se_guarda_con_la_ortografia_del_catalogo(client):
    """Nadie escribe «Bulldog Francés» con el acento a las siete de la tarde, y
    guardarlo como una raza distinta rompe el recuento que el catálogo salva."""
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)

    registrar(client, tutor, raza="bulldog frances")

    paciente = Paciente.de_todas_las_clinicas.get()
    assert paciente.raza == "Bulldog Francés"
    assert paciente.raza_del_catalogo


def test_una_raza_que_no_esta_en_el_catalogo_se_guarda_tal_cual(client):
    """La opción «otra»: un catálogo de razas nunca está completo, y bloquear el
    mostrador por una que falta sería pedirle a recepción que mienta."""
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)

    registrar(client, tutor, raza="Quiltro con algo de galgo")

    paciente = Paciente.de_todas_las_clinicas.get()
    assert paciente.raza == "Quiltro con algo de galgo"
    assert not paciente.raza_del_catalogo


def test_una_raza_de_otra_especie_no_cuenta_como_del_catalogo(client):
    """«Siamés» escrito en la ficha de un perro es texto libre, no una raza."""
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)

    registrar(client, tutor, especie=Especie.PERRO, raza="Siamés")

    assert not Paciente.de_todas_las_clinicas.get().raza_del_catalogo


# --- Vínculo con los Tutores ----------------------------------------------


def sumar_tutor(client, paciente, tutor, responsable=False):
    datos = {"tutor": tutor.pk}
    if responsable:
        datos["responsable"] = "on"
    return client.post(reverse("patients:vincular", args=[paciente.pk]), datos)


def test_un_paciente_puede_tener_varios_tutores(client):
    """Una pareja separada que se turna, una hija que lo trae al control."""
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)
    primero = TutorFactory(clinic=usuario.clinic, nombre="Camila", apellidos="Rojas")
    segunda = TutorFactory(clinic=usuario.clinic, nombre="Ignacio", apellidos="Fuentes")
    primero.se_hace_cargo_de(paciente)

    sumar_tutor(client, paciente, segunda)

    assert set(t.tutor for t in paciente.quienes_responden) == {primero, segunda}


def test_un_tutor_puede_tener_varios_pacientes(client):
    """Casi siempre tiene más de un animal."""
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)
    perro = PacienteFactory(clinic=usuario.clinic, nombre="Rocco")
    gata = PacienteFactory(clinic=usuario.clinic, nombre="Nube", especie=Especie.GATO)
    tutor.se_hace_cargo_de(perro)
    tutor.se_hace_cargo_de(gata)

    assert {p.nombre for p in tutor.de_quienes_se_hace_cargo} == {"Rocco", "Nube"}


def test_sumar_un_tutor_no_le_quita_el_cargo_al_responsable(client):
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)
    responsable = TutorFactory(clinic=usuario.clinic)
    responsable.se_hace_cargo_de(paciente)

    sumar_tutor(client, paciente, TutorFactory(clinic=usuario.clinic))

    assert paciente.responsable == responsable


def test_sumar_un_tutor_diciendo_que_es_el_responsable_releva_al_anterior(client):
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)
    antes = TutorFactory(clinic=usuario.clinic)
    antes.se_hace_cargo_de(paciente)
    ahora = TutorFactory(clinic=usuario.clinic)

    sumar_tutor(client, paciente, ahora, responsable=True)

    assert paciente.responsable == ahora
    assert paciente.quienes_responden.filter(responsable=True).count() == 1


def test_recepcion_pasa_el_cargo_a_otro_de_los_tutores_del_paciente(client):
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)
    antes = TutorFactory(clinic=usuario.clinic)
    antes.se_hace_cargo_de(paciente)
    ahora = TutorFactory(clinic=usuario.clinic)
    vinculo = ahora.se_hace_cargo_de(paciente)

    client.post(reverse("patients:responsable", args=[paciente.pk, vinculo.pk]))

    assert paciente.responsable == ahora
    assert paciente.quienes_responden.filter(responsable=True).count() == 1


def test_el_cargo_de_responsable_no_se_pasa_siguiendo_un_enlace(client):
    """Cambia a quién se llama y a quién se cobra: no puede pasar por un GET."""
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)
    vinculo = TutorFactory(clinic=usuario.clinic).se_hace_cargo_de(paciente)

    respuesta = client.get(reverse("patients:responsable", args=[paciente.pk, vinculo.pk]))

    assert respuesta.status_code == 405


def test_la_base_de_datos_no_admite_dos_responsables_a_la_vez():
    """La garantía no depende de que nadie abra dos pestañas."""
    paciente = PacienteFactory()
    TutorFactory(clinic=paciente.clinic).se_hace_cargo_de(paciente)

    with pytest.raises(IntegrityError), transaction.atomic():
        VinculoFactory(
            paciente=paciente, tutor=TutorFactory(clinic=paciente.clinic), responsable=True
        )


def test_un_tutor_que_ya_responde_por_el_paciente_no_se_vuelve_a_ofrecer(client):
    """Elegirlo dos veces no es un error del que avisar: es una opción que no
    debería haberse ofrecido."""
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)
    ya_esta = TutorFactory(clinic=usuario.clinic, nombre="Camila", apellidos="Rojas")
    ya_esta.se_hace_cargo_de(paciente)

    contenido = client.get(reverse("patients:vincular", args=[paciente.pk])).content.decode()

    assert str(ya_esta.pk) not in opciones_de(contenido, "tutor")


def test_volver_a_vincular_al_mismo_tutor_no_duplica_el_vinculo(client):
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)
    tutor = TutorFactory(clinic=usuario.clinic)
    tutor.se_hace_cargo_de(paciente)

    respuesta = sumar_tutor(client, paciente, tutor)

    assert respuesta.status_code == 200
    assert paciente.quienes_responden.count() == 1


# --- Las dos fichas se ven la una a la otra -------------------------------


def test_la_ficha_del_paciente_muestra_sus_datos_y_sus_tutores(client):
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic, nombre="Rocco", raza="Mestizo")
    tutor = TutorFactory(clinic=usuario.clinic, nombre="Camila", apellidos="Rojas")
    tutor.se_hace_cargo_de(paciente)

    contenido = client.get(reverse("patients:ficha", args=[paciente.pk])).content.decode()

    assert "Rocco" in contenido
    assert "Mestizo" in contenido
    assert "Camila Rojas" in contenido
    assert reverse("tutors:ficha", args=[paciente.responsable.pk]) in contenido


def test_la_ficha_del_tutor_muestra_sus_pacientes(client):
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)
    paciente = PacienteFactory(clinic=usuario.clinic, nombre="Rocco")
    tutor.se_hace_cargo_de(paciente)

    contenido = client.get(reverse("tutors:ficha", args=[tutor.pk])).content.decode()

    assert "Rocco" in contenido
    assert reverse("patients:ficha", args=[paciente.pk]) in contenido


def test_recepcion_corrige_la_ficha_de_un_paciente(client):
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic, nombre="Roco")

    client.post(
        reverse("patients:editar", args=[paciente.pk]), DATOS_DEL_PACIENTE | {"nombre": "Rocco"}
    )

    paciente.refresh_from_db()
    assert paciente.nombre == "Rocco"


# --- Registro de acceso ---------------------------------------------------


def test_abrir_la_ficha_de_un_paciente_deja_constancia(client):
    """La ley protege la ficha del animal igual que la de su Tutor: por ella se
    llega a él (ADR-0004)."""
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    client.get(reverse("patients:ficha", args=[paciente.pk]))

    assert anotaciones_sobre(paciente, Accion.LECTURA).get().usuario == usuario


def test_la_ficha_del_paciente_deja_constancia_de_los_tutores_que_nombra(client):
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)
    tutor = TutorFactory(clinic=usuario.clinic)
    tutor.se_hace_cargo_de(paciente)

    client.get(reverse("patients:ficha", args=[paciente.pk]))

    assert anotaciones_sobre(tutor, Accion.LECTURA).exists()


def test_la_ficha_del_tutor_deja_constancia_de_los_pacientes_que_nombra(client):
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic)
    paciente = PacienteFactory(clinic=usuario.clinic)
    tutor.se_hace_cargo_de(paciente)

    client.get(reverse("tutors:ficha", args=[tutor.pk]))

    assert anotaciones_sobre(paciente, Accion.LECTURA).exists()


def test_abrir_el_formulario_de_correccion_deja_constancia_de_la_lectura(client):
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    client.get(reverse("patients:editar", args=[paciente.pk]))

    assert anotaciones_sobre(paciente, Accion.LECTURA).exists()
    assert not anotaciones_sobre(paciente, Accion.MODIFICACION).exists()


def test_pedir_sumar_un_tutor_deja_constancia_de_haber_visto_el_fichero(client):
    """El desplegable enseña el nombre de todos los Tutores de la Clínica."""
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)

    client.get(reverse("patients:vincular", args=[paciente.pk]))

    assert RegistroDeAcceso.de_todas_las_clinicas.filter(
        tipo_de_objeto="tutors.Tutor", identificador=EL_CONJUNTO, accion=Accion.LECTURA
    ).exists()


def test_sumar_un_tutor_consta_como_modificacion_de_las_dos_fichas(client):
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic)
    tutor = TutorFactory(clinic=usuario.clinic)

    sumar_tutor(client, paciente, tutor)

    assert anotaciones_sobre(paciente, Accion.MODIFICACION).exists()
    assert anotaciones_sobre(tutor, Accion.MODIFICACION).exists()


def test_la_lista_de_razas_no_deja_constancia_de_nada(client):
    """Es catálogo, no datos de nadie. Anotarlo llenaría de ruido la tabla que
    tiene que valer como prueba."""
    recepcion(client)

    client.get(reverse("patients:razas"), {"especie": Especie.PERRO})

    assert not RegistroDeAcceso.de_todas_las_clinicas.exists()


# --- Separación de los datos personales y los clínicos --------------------


def test_el_paciente_no_guarda_ningun_dato_personal_de_su_tutor():
    """Anonimizar un Tutor sin tocar la Historia clínica (ADR-0004, ticket 20)
    solo es posible si ningún dato personal suyo bajó hasta el Paciente.

    Si el nombre o el teléfono del Tutor estuvieran copiados aquí, anonimizar o
    bien dejaría el dato personal en pie o bien se llevaría por delante la ficha
    clínica. Quién responde por el animal es el Vínculo, que es una tabla aparte.
    """
    # El `nombre` del Paciente es el del animal, no el de nadie: es el único
    # rótulo que las dos tablas comparten, y por eso se nombra aquí en vez de
    # dejar que la comparación lo dé por bueno en silencio.
    contacto_del_tutor = set(Tutor.DATOS_PERSONALES) - {"nombre"}
    del_paciente = Paciente._meta.local_fields + Paciente._meta.local_many_to_many
    campos = {campo.name for campo in del_paciente}

    assert campos & contacto_del_tutor == set()
    # Y el Tutor tampoco está como clave ajena: quién responde por el animal es
    # una tabla aparte, y por eso el Paciente sobrevive a que cambie.
    assert not [campo for campo in Paciente._meta.local_fields if campo.related_model is Tutor]


def test_vaciar_los_datos_personales_del_tutor_deja_al_paciente_entero(client):
    """Lo que hará el ticket 20, comprobado desde ahora: el derecho de supresión
    del Tutor no puede llevarse por delante la ficha del animal, de la que él no
    es titular. Lo que no desaparece es el Vínculo: quién trajo al Paciente es
    parte de su Historia."""
    usuario = recepcion(client)
    paciente = PacienteFactory(clinic=usuario.clinic, nombre="Rocco", raza=MESTIZO)
    tutor = TutorFactory(clinic=usuario.clinic)
    tutor.se_hace_cargo_de(paciente)

    for dato in Tutor.DATOS_PERSONALES:
        setattr(tutor, dato, "")
    tutor.save()

    paciente.refresh_from_db()
    assert paciente.nombre == "Rocco"
    assert paciente.raza == MESTIZO
    assert paciente.responsable == tutor

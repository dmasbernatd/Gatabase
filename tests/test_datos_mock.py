"""Los datos de demostración: que sean verosímiles, y que no se coman una base real.

Se corre el comando de verdad con un volumen pequeño —lo que tarda un test— y se
mira lo que quedó escrito. Lo que se comprueba no es que haya filas: es que el
dato pase por donde pasa el dato de verdad —un RUT cuyo dígito verificador cuadra,
un teléfono en E.164, una raza del catálogo— y que los casos límite que rompen
pantallas estén puestos y no dependan del azar.

`DEBUG` está apagado durante la batería de tests, y el comando se niega a poblar
así. Por eso casi todos los tests lo encienden: la negativa es lo que se prueba
aparte, y no algo que haya que rodear con una excepción para los tests.
"""

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.imports import mock
from apps.patients.catalogo import Especie, es_del_catalogo
from apps.patients.estados import EstadoDelPaciente
from apps.patients.models import Paciente
from apps.telefono import normalizado as telefono_normalizado
from apps.tenancy.models import Clinica, Rol, Usuario
from apps.tutors.models import Consentimiento, Tutor, Vinculo
from apps.tutors.rut import digito_verificador
from tests.factories import ClinicaFactory

pytestmark = pytest.mark.django_db

TUTORES = 25


@pytest.fixture
def poblada(settings):
    """Las dos Clínicas de demostración, pequeñas, ya escritas."""
    settings.DEBUG = True
    call_command("datos_mock", tutores=TUTORES, verbosity=0)
    return [Clinica.objects.get(nombre=nombre) for nombre in mock.NOMBRES_DE_LAS_CLINICAS]


def tutores_de(clinica):
    return Tutor.de_todas_las_clinicas.filter(clinic=clinica)


def pacientes_de(clinica):
    return Paciente.de_todas_las_clinicas.filter(clinic=clinica)


def test_pobla_dos_clinicas_con_su_sede(poblada):
    """Dos y no una: es lo que deja comprobar el aislamiento a mano."""
    grande, pequena = poblada

    assert [clinica.sedes.count() for clinica in poblada] == [1, 1]
    assert tutores_de(grande).count() == TUTORES
    assert tutores_de(pequena).count() < tutores_de(grande).count()


def test_cada_clinica_tiene_usuarios_de_los_tres_roles(poblada):
    for clinica in poblada:
        roles = set(Usuario.objects.filter(clinic=clinica).values_list("rol", flat=True))

        assert roles == {Rol.ADMIN, Rol.VETERINARIO, Rol.RECEPCION}


def test_los_usuarios_entran_con_la_contrasena_de_demostracion(poblada):
    """Impresa por el comando: el secreto no protege nada y perderla sí estorba."""
    grande, _pequena = poblada
    admin = Usuario.objects.filter(clinic=grande, rol=Rol.ADMIN).first()

    assert admin.check_password(mock.CONTRASENA)


def test_los_usuarios_pertenecen_a_la_sede_de_su_clinica(poblada):
    for clinica in poblada:
        for usuario in Usuario.objects.filter(clinic=clinica):
            assert list(usuario.sedes.all()) == list(clinica.sedes.all())


def test_ningun_dato_cruza_la_frontera_de_la_clinica(poblada):
    """Lo que la demostración enseña a mano, aquí de una vez (ADR-0003)."""
    grande, pequena = poblada

    assert not tutores_de(grande).filter(pk__in=tutores_de(pequena)).exists()
    for clinica in poblada:
        assert not Vinculo.de_todas_las_clinicas.filter(clinic=clinica).exclude(
            tutor__clinic=clinica, paciente__clinic=clinica
        ).exists()


def test_las_dos_clinicas_no_salen_calcadas(poblada):
    """La semilla lleva el nombre de la Clínica: dos copias no probarían nada."""
    grande, pequena = poblada
    cuantos = tutores_de(pequena).count()

    de_una = list(tutores_de(grande).values_list("nombre", "apellidos")[:cuantos])
    de_otra = list(tutores_de(pequena).values_list("nombre", "apellidos")[:cuantos])

    assert de_una != de_otra


def test_los_rut_cuadran_de_verdad(poblada):
    """El dígito verificador es una suma, no un formato: un RUT inventado no
    serviría para probar el mostrador, que es donde se teclean mal."""
    con_rut = Tutor.de_todas_las_clinicas.exclude(rut="")

    assert con_rut.exists()
    for rut in con_rut.values_list("rut", flat=True):
        assert rut[-1] == digito_verificador(rut[:-1])


def test_los_telefonos_se_guardan_como_se_guardan(poblada):
    """En E.164, que es lo que después sirve para llamar y para WhatsApp."""
    for telefono in Tutor.de_todas_las_clinicas.values_list("telefono", flat=True):
        assert telefono == telefono_normalizado(telefono)
        assert telefono.startswith("+")


def test_las_razas_salen_del_catalogo_o_estan_en_blanco(poblada):
    """Texto libre lo admite el campo, pero inventarlo aquí falsearía la
    estadística que el catálogo viene a salvar."""
    for especie, raza in pacientes_de(poblada[0]).values_list("especie", "raza"):
        assert raza == "" or es_del_catalogo(especie, raza)


def test_mandan_los_perros_y_los_gatos(poblada):
    """Es lo que entra por la puerta, y es lo que las pantallas tienen que
    aguantar: una mezcla a partes iguales no se parecería a ninguna clínica."""
    pacientes = pacientes_de(poblada[0])
    caninos_y_felinos = pacientes.filter(especie__in=(Especie.PERRO, Especie.GATO)).count()

    assert caninos_y_felinos > pacientes.count() * 0.7


def test_hay_algun_exotico(poblada):
    pacientes = pacientes_de(poblada[0])

    assert pacientes.exclude(especie__in=(Especie.PERRO, Especie.GATO)).exists()


def test_la_mayoria_de_los_perros_y_gatos_son_mestizos(poblada):
    caninos_y_felinos = pacientes_de(poblada[0]).filter(
        especie__in=(Especie.PERRO, Especie.GATO)
    )
    mestizos = caninos_y_felinos.filter(raza="Mestizo").count()

    assert mestizos > caninos_y_felinos.count() * 0.4


def test_los_microchips_no_se_repiten_dentro_de_la_clinica(poblada):
    """Único por Clínica (ADR-0001): un duplicado ni siquiera se guardaría, así
    que lo que esto vigila es que el generador no falle a mitad de una carga."""
    for clinica in poblada:
        chips = list(pacientes_de(clinica).exclude(microchip="").values_list("microchip", flat=True))

        assert chips
        assert len(chips) == len(set(chips))
        assert all(len(chip) == 15 and chip.isdigit() for chip in chips)


@pytest.mark.parametrize(
    "caso, consulta",
    [
        ("Paciente sin microchip", lambda c: pacientes_de(c).filter(microchip="")),
        (
            "Paciente fallecido",
            lambda c: pacientes_de(c).filter(estado=EstadoDelPaciente.FALLECIDO),
        ),
        ("Tutor sin RUT", lambda c: tutores_de(c).filter(rut="")),
        (
            "Tutor extranjero",
            lambda c: tutores_de(c).filter(rut="").exclude(telefono__startswith="+569"),
        ),
    ],
)
def test_los_casos_limite_estan_puestos(poblada, caso, consulta):
    """Con volumen alto el azar los produce solos; con `--tutores 40` no, y el
    comando tiene que dar lo mismo — es como se corre mientras se programa."""
    for clinica in poblada:
        assert consulta(clinica).exists(), caso


def test_hay_dos_tutores_con_el_mismo_telefono(poblada):
    """Una familia comparte número: es lo normal, y es lo que el aviso de
    coincidencia del mostrador tiene que saber enseñar."""
    for clinica in poblada:
        telefonos = list(tutores_de(clinica).values_list("telefono", flat=True))

        assert len(telefonos) != len(set(telefonos))


def test_hay_un_paciente_con_dos_tutores(poblada):
    for clinica in poblada:
        con_dos = [
            paciente
            for paciente in pacientes_de(clinica)
            if paciente.quienes_responden.count() > 1
        ]

        assert con_dos


def test_todo_paciente_activo_tiene_quien_responda_por_el(poblada):
    """Una ficha activa sin responsable no dice a quién llamar."""
    for clinica in poblada:
        activos = pacientes_de(clinica).filter(estado=EstadoDelPaciente.ACTIVO)

        assert activos.exists()
        assert not any(paciente.le_falta_responsable for paciente in activos)


def test_hay_pacientes_que_cambiaron_de_manos(poblada):
    """El Vínculo cerrado con su fecha, que es lo que el ticket 10 enseña."""
    for clinica in poblada:
        cerrados = Vinculo.de_todas_las_clinicas.filter(
            clinic=clinica, fecha_de_cierre__isnull=False
        )

        assert cerrados.exists()
        # Quien dejó de responder por el animal no puede seguir siendo a quien
        # se llama: la base de datos lo rechaza, y el generador no lo intenta.
        assert not cerrados.filter(responsable=True).exists()


def test_hay_consentimiento_declarado_y_hay_quien_se_desdijo(poblada):
    """No consta, otorgado y revocado: los tres estados existen en la clínica."""
    grande, _pequena = poblada
    declaraciones = Consentimiento.de_todas_las_clinicas.filter(clinic=grande)

    assert declaraciones.filter(otorgado=True).exists()
    assert declaraciones.filter(otorgado=False).exists()
    # Alguien de quien no consta nada de ningún canal: es el caso más frecuente
    # y el que la ficha enseña distinto de una negativa.
    assert tutores_de(grande).filter(consentimientos__isnull=True).exists()


def test_se_puede_correr_dos_veces_seguidas(settings, poblada):
    """Rehace lo suyo en vez de duplicarlo: es como se usa mientras se programa."""
    settings.DEBUG = True
    antes = [tutores_de(clinica).count() for clinica in poblada]
    usuarios_antes = Usuario.objects.count()

    call_command("datos_mock", tutores=TUTORES, verbosity=0)

    assert [tutores_de(clinica).count() for clinica in poblada] == antes
    assert Clinica.objects.count() == len(mock.CLINICAS)
    assert Usuario.objects.count() == usuarios_antes


def test_la_misma_semilla_da_la_misma_clinica(settings, poblada):
    """Un fallo que aparece con estos datos se vuelve a ver mañana."""
    settings.DEBUG = True
    grande = poblada[0]
    antes = list(tutores_de(grande).values_list("nombre", "apellidos", "rut"))

    call_command("datos_mock", tutores=TUTORES, verbosity=0)

    assert list(tutores_de(grande).values_list("nombre", "apellidos", "rut")) == antes


def test_otra_semilla_da_otra_clinica(settings, poblada):
    settings.DEBUG = True
    grande = poblada[0]
    antes = list(tutores_de(grande).values_list("nombre", "apellidos"))

    call_command("datos_mock", tutores=TUTORES, semilla=7, verbosity=0)

    assert list(tutores_de(grande).values_list("nombre", "apellidos")) != antes


def test_en_desarrollo_convive_con_las_clinicas_hechas_a_mano(settings):
    """Una base de desarrollo tiene siempre Clínicas de prueba, y no se tocan:
    negarse por ellas convertiría el aviso en un estorbo diario."""
    settings.DEBUG = True
    ajena = ClinicaFactory(nombre="Clínica de humo")

    call_command("datos_mock", tutores=TUTORES, verbosity=0)

    assert Clinica.objects.filter(pk=ajena.pk).exists()
    assert not tutores_de(ajena).exists()


def test_se_niega_contra_un_despliegue_con_clientes(settings):
    """El caso que no lo levanta ninguna opción: DEBUG apagado y Clínicas que
    no son suyas quiere decir que aquí hay datos de clientes."""
    settings.DEBUG = False
    ClinicaFactory(nombre="Clínica Veterinaria San Bernardo")

    with pytest.raises(CommandError, match="datos de clientes"):
        call_command("datos_mock", tutores=TUTORES, verbosity=0)

    assert not Tutor.de_todas_las_clinicas.exists()


def test_ni_pidiendolo_explicitamente(settings):
    """La opción levanta la sospecha de un despliegue, no la de unos clientes."""
    settings.DEBUG = False
    ClinicaFactory(nombre="Clínica Veterinaria San Bernardo")

    with pytest.raises(CommandError, match="datos de clientes"):
        call_command(
            "datos_mock", tutores=TUTORES, aunque_no_sea_desarrollo=True, verbosity=0
        )


def test_se_niega_con_debug_apagado(settings):
    """Que es como corre un despliegue, y como corre esta misma batería."""
    settings.DEBUG = False

    with pytest.raises(CommandError, match="DJANGO_DEBUG"):
        call_command("datos_mock", tutores=TUTORES, verbosity=0)

    assert not Clinica.objects.exists()


def test_con_debug_apagado_se_puede_pedir_explicitamente(settings):
    """La demostración a la clínica piloto corre en un despliegue de verdad."""
    settings.DEBUG = False

    call_command("datos_mock", tutores=TUTORES, aunque_no_sea_desarrollo=True, verbosity=0)

    assert Clinica.objects.count() == len(mock.CLINICAS)


def test_no_se_puebla_por_debajo_del_minimo(settings):
    """Con menos Tutores no caben los casos límite, y sin ellos no hay clínica."""
    settings.DEBUG = True

    with pytest.raises(CommandError, match="casos límite"):
        call_command("datos_mock", tutores=mock.MINIMO_DE_TUTORES - 1, verbosity=0)

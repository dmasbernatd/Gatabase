"""Fábricas compartidas de `factory_boy`.

Convención para los tickets siguientes: una fábrica por modelo de dominio,
con valores por defecto plausibles para una clínica chilena, y `Meta.django_get_or_create`
cuando el modelo tenga clave natural. Los tests las importan desde aquí; las
fábricas de un solo test viven junto a ese test.
"""

import datetime as dt

import factory
from django.contrib.auth import get_user_model

from apps.audit.models import Accion, RegistroDeAcceso
from apps.patients.catalogo import Especie
from apps.patients.models import Paciente, Sexo
from apps.tenancy.horarios import Dia
from apps.tenancy.models import (
    Clinica,
    ClinicaDeDerivacion,
    ExcepcionDeAtencion,
    FranjaDeAtencion,
    Rol,
    Sede,
)
from apps.tutors.models import Tutor, Vinculo
from apps.tutors.rut import digito_verificador

CONTRASENA_DE_PRUEBA = "gatabase-de-prueba-2026"


class ClinicaFactory(factory.django.DjangoModelFactory):
    """La organización que contrata el sistema; frontera de aislamiento."""

    class Meta:
        model = Clinica
        django_get_or_create = ("nombre",)

    nombre = factory.Sequence(lambda n: f"Clínica Veterinaria {n}")


class SedeFactory(factory.django.DjangoModelFactory):
    """Local físico de una Clínica."""

    class Meta:
        model = Sede

    clinic = factory.SubFactory(ClinicaFactory)
    nombre = factory.Sequence(lambda n: f"Sede {n}")
    direccion = "Av. Providencia 1234, Santiago"


class UsuarioFactory(factory.django.DjangoModelFactory):
    """Persona que accede a la aplicación: veterinario, recepción o administración."""

    class Meta:
        model = get_user_model()
        django_get_or_create = ("email",)
        skip_postgeneration_save = True

    clinic = factory.SubFactory(ClinicaFactory)
    email = factory.Sequence(lambda n: f"usuario{n}@clinica.example")
    nombre = "Camila"
    apellidos = "Rojas"
    rol = Rol.RECEPCION
    contrasena = CONTRASENA_DE_PRUEBA

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # La contraseña se guarda cifrada: crear el Usuario con `password=`
        # en claro dejaría cuentas imposibles de usar en los tests.
        contrasena = kwargs.pop("contrasena", None)
        return model_class.objects.create_user(contrasena=contrasena, **kwargs)

    @factory.post_generation
    def sedes(usuario, crear, extraidas, **kwargs):
        """Sin Sedes explícitas, el Usuario pertenece a una Sede nueva de su Clínica."""
        if not crear:
            return
        usuario.sedes.set(extraidas if extraidas is not None else [SedeFactory(clinic=usuario.clinic)])


class FabricaDeLaClinica(factory.django.DjangoModelFactory):
    """Base de las fábricas de modelos de dominio.

    Construye a través del manager sin filtro: una fábrica arma escenarios de
    varias Clínicas a la vez, y no tiene por qué haber ninguna Clínica activa.
    """

    class Meta:
        abstract = True

    clinic = factory.SubFactory(ClinicaFactory)

    @classmethod
    def _get_manager(cls, model_class):
        return model_class.de_todas_las_clinicas


def rut_de_prueba(numero):
    """Un RUT que cuadra de verdad, para que las fábricas no tengan que inventarse
    uno: el campo valida el dígito verificador pase por donde pase el dato."""
    cuerpo = str(10_000_000 + numero)
    return cuerpo + digito_verificador(cuerpo)


class TutorFactory(FabricaDeLaClinica):
    """Persona responsable de un Paciente ante la clínica y ante la ley."""

    class Meta:
        model = Tutor

    nombre = factory.Sequence(lambda n: f"Tutor de prueba {n}")
    rut = factory.Sequence(rut_de_prueba)
    apellidos = factory.Sequence(lambda n: f"Apellidos de prueba {n}")
    telefono = "+56912345678"
    email = factory.Sequence(lambda n: f"tutor{n}@correo.example")
    direccion = "Av. Providencia 1234, Santiago"


class PacienteFactory(FabricaDeLaClinica):
    """El animal atendido por la clínica."""

    class Meta:
        model = Paciente

    nombre = factory.Sequence(lambda n: f"Paciente de prueba {n}")
    especie = Especie.PERRO
    raza = "Mestizo"
    sexo = Sexo.MACHO
    color = "Negro"


class VinculoFactory(FabricaDeLaClinica):
    """Que un Tutor responde por un Paciente.

    La Clínica sale del Tutor: un Vínculo entre Clínicas no significaría nada, y
    dejar que la fábrica invente una tercera escondería justo los escenarios de
    aislamiento que los tests vienen a armar.
    """

    class Meta:
        model = Vinculo

    tutor = factory.SubFactory(TutorFactory)
    paciente = factory.SubFactory(PacienteFactory, clinic=factory.SelfAttribute("..tutor.clinic"))
    clinic = factory.SelfAttribute("tutor.clinic")


class RegistroDeAccesoFactory(FabricaDeLaClinica):
    """Anotación de un acceso a datos personales.

    Arma un Registro ya escrito, para probar lo que se consulta y lo que ya no
    se puede tocar. Lo que se anota al servir una página se prueba por HTTP: es
    la vista quien tiene que acordarse, no la fábrica.

    La Clínica sale del Usuario, como en el Registro de verdad: una anotación de
    un Usuario en una Clínica que no es la suya no significaría nada.
    """

    class Meta:
        model = RegistroDeAcceso

    usuario = factory.SubFactory(UsuarioFactory)
    clinic = factory.SelfAttribute("usuario.clinic")
    tipo_de_objeto = "tutors.Tutor"
    identificador = factory.Sequence(str)
    accion = Accion.LECTURA


class FabricaDeLaSede(FabricaDeLaClinica):
    """Base de lo que una Sede declara de sí misma.

    La Clínica sale de la Sede, como en los formularios: una Franja cuya Clínica
    no fuera la de su Sede no significaría nada, y dejar que la fábrica invente
    una tercera escondería justo los escenarios de aislamiento que se quieren
    armar.
    """

    class Meta:
        abstract = True

    sede = factory.SubFactory(SedeFactory)
    clinic = factory.SelfAttribute("sede.clinic")


class FranjaDeAtencionFactory(FabricaDeLaSede):
    """Un tramo de un día de la semana en que la Sede atiende."""

    class Meta:
        model = FranjaDeAtencion

    dia = Dia.LUNES
    desde = dt.time(9, 0)
    hasta = dt.time(13, 0)


class ExcepcionDeAtencionFactory(FabricaDeLaSede):
    """Lo que la Sede hace una fecha concreta, en vez de lo que diga su semana.

    Nace como un cierre —sin horas—, que es el caso corriente: un festivo o una
    semana de vacaciones. El día de horario raro se pide con `desde` y `hasta`.
    """

    class Meta:
        model = ExcepcionDeAtencion

    fecha = dt.date(2026, 9, 18)
    motivo = "Fiestas Patrias"


class ClinicaDeDerivacionFactory(FabricaDeLaClinica):
    """Clínica externa a la que se manda a un Tutor cuando la Sede no puede."""

    class Meta:
        model = ClinicaDeDerivacion

    nombre = factory.Sequence(lambda n: f"Clínica de urgencias {n}")
    telefono = "+56912345678"
    direccion = "Av. Las Condes 4321, Santiago"

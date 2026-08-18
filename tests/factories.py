"""Fábricas compartidas de `factory_boy`.

Convención para los tickets siguientes: una fábrica por modelo de dominio,
con valores por defecto plausibles para una clínica chilena, y `Meta.django_get_or_create`
cuando el modelo tenga clave natural. Los tests las importan desde aquí; las
fábricas de un solo test viven junto a ese test.
"""

import factory
from django.contrib.auth import get_user_model

from apps.audit.models import Accion, RegistroDeAcceso
from apps.tenancy.models import Clinica, Rol, Sede
from apps.tutors.models import Tutor

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


class TutorFactory(FabricaDeLaClinica):
    """Persona responsable de un Paciente ante la clínica y ante la ley."""

    class Meta:
        model = Tutor

    nombre = factory.Sequence(lambda n: f"Tutor de prueba {n}")
    apellidos = factory.Sequence(lambda n: f"Apellidos de prueba {n}")
    telefono = "+56912345678"
    email = factory.Sequence(lambda n: f"tutor{n}@correo.example")
    direccion = "Av. Providencia 1234, Santiago"


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

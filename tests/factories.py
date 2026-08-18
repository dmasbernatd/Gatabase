"""Fábricas compartidas de `factory_boy`.

Convención para los tickets siguientes: una fábrica por modelo de dominio,
con valores por defecto plausibles para una clínica chilena, y `Meta.django_get_or_create`
cuando el modelo tenga clave natural. Los tests las importan desde aquí; las
fábricas de un solo test viven junto a ese test.
"""

import factory
from django.contrib.auth import get_user_model

from apps.tenancy.models import Clinica, Rol, Sede

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

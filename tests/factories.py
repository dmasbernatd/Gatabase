"""Fábricas compartidas de `factory_boy`.

Convención para los tickets siguientes: una fábrica por modelo de dominio,
con valores por defecto plausibles para una clínica chilena, y `Meta.django_get_or_create`
cuando el modelo tenga clave natural. Los tests las importan desde aquí; las
fábricas de un solo test viven junto a ese test.
"""

import factory
from django.contrib.auth import get_user_model


class UsuarioFactory(factory.django.DjangoModelFactory):
    """Persona que accede a la aplicación: veterinario, recepción o administración."""

    class Meta:
        model = get_user_model()
        django_get_or_create = ("username",)
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"usuario{n}")
    email = factory.LazyAttribute(lambda u: f"{u.username}@clinica.example")
    first_name = "Camila"
    last_name = "Rojas"

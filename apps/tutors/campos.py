"""Los campos que normalizan lo que se escribe: el RUT y el teléfono.

Son campos de modelo y no validadores sueltos porque lo que hacen no es decir
«esto está mal»: es decidir **cómo se guarda**. Un validador se ejecuta después
de que el valor ya esté puesto en el objeto, así que dejaría entrar
«12.345.678-5» y «123456785» como dos cosas distintas y las dos válidas, y el
RUT único por Clínica no significaría nada.

Puestos en el modelo, la normalización ocurre pase lo que pase: en el
formulario, en el importador del ticket 17, en un comando o en un test. No hay
que acordarse de llamar a nadie, y el único sitio donde se decide cómo se lee un
RUT sigue siendo `rut.py`.

El campo de formulario que devuelven hace lo mismo al entrar —así el propio
formulario puede preguntar por duplicados con el valor ya normalizado, antes de
guardar— y al salir lo presenta como se lee.
"""

from django import forms
from django.db import models

from apps.tutors import rut, telefono


class _CampoQueNormaliza(models.CharField):
    """Base de los dos: un `CharField` que pasa por su normalizador al entrar.

    `to_python` es por donde entra el valor al validar el objeto, y
    `get_prep_value` por donde sale hacia la base de datos. Los dos, porque un
    `save()` sin `full_clean()` —lo normal en un comando o en una fábrica— solo
    pasa por el segundo, y ahí es donde se decide lo que queda escrito.
    """

    # Qué función lee lo escrito, y qué campo de formulario ofrece.
    normalizador = staticmethod(str)
    entrada = forms.CharField

    def to_python(self, valor):
        return self.normalizador(valor)

    def get_prep_value(self, valor):
        return self.to_python(super().get_prep_value(valor))

    def formfield(self, **kwargs):
        return super().formfield(**{"form_class": self.entrada, **kwargs})


class EntradaDeRut(forms.CharField):
    """La caja donde se teclea un RUT: entra como sea y se presenta a la chilena."""

    def to_python(self, valor):
        return rut.normalizado(super().to_python(valor))

    def prepare_value(self, valor):
        return rut.formateado(valor)


class EntradaDeTelefono(forms.CharField):
    """La caja donde se teclea un teléfono: entra como sea y se guarda en E.164."""

    def to_python(self, valor):
        return telefono.normalizado(super().to_python(valor))


class CampoDeRut(_CampoQueNormaliza):
    """El RUT de una persona, guardado sin puntos ni guion (`rut.py`)."""

    normalizador = staticmethod(rut.normalizado)
    entrada = EntradaDeRut


class CampoDeTelefono(_CampoQueNormaliza):
    """Un teléfono, guardado en E.164 (`telefono.py`)."""

    normalizador = staticmethod(telefono.normalizado)
    entrada = EntradaDeTelefono

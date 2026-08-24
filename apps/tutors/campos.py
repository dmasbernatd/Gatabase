"""Los campos del Tutor que normalizan lo que se escribe: el RUT y el teléfono.

Cómo se normaliza —y por qué en el campo y no en un validador— lo explica
`apps/campos.py`, de donde sale la base. Aquí solo se dice qué función lee cada
dato: el único sitio donde se decide cómo se lee un RUT sigue siendo `rut.py`.

El campo de formulario que devuelven hace lo mismo al entrar —así el propio
formulario puede preguntar por duplicados con el valor ya normalizado, antes de
guardar— y al salir lo presenta como se lee.
"""

from django import forms

from apps.campos import CampoQueNormaliza
from apps.tutors import rut, telefono


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


class CampoDeRut(CampoQueNormaliza):
    """El RUT de una persona, guardado sin puntos ni guion (`rut.py`)."""

    normalizador = staticmethod(rut.normalizado)
    entrada = EntradaDeRut


class CampoDeTelefono(CampoQueNormaliza):
    """Un teléfono, guardado en E.164 (`telefono.py`)."""

    normalizador = staticmethod(telefono.normalizado)
    entrada = EntradaDeTelefono

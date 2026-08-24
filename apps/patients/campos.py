"""El campo del Paciente que normaliza lo que se escribe: el microchip.

Cómo se normaliza —y por qué en el campo y no en un validador— lo explica
`apps/campos.py`, de donde sale la base. Aquí solo se dice qué función lee el
dato: el único sitio donde se decide cómo se lee un chip sigue siendo
`microchip.py`.

El campo de formulario hace lo mismo al entrar —así el propio formulario puede
preguntar por duplicados con el número ya normalizado, antes de guardar— y al
salir lo presenta en grupos, que es como se dicta.
"""

from django import forms

from apps.campos import CampoQueNormaliza
from apps.patients import microchip


class EntradaDeMicrochip(forms.CharField):
    """La caja donde se teclea un chip: entra como sea y se presenta en grupos."""

    def to_python(self, valor):
        return microchip.normalizado(super().to_python(valor))

    def prepare_value(self, valor):
        return microchip.formateado(valor)


class CampoDeMicrochip(CampoQueNormaliza):
    """El número de chip de un Paciente, guardado de corrido (`microchip.py`)."""

    normalizador = staticmethod(microchip.normalizado)
    entrada = EntradaDeMicrochip

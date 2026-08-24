"""Campos de modelo que normalizan lo que se escribe antes de guardarlo.

Aquí vive solo la base. Qué es un RUT lo decide `apps/tutors/rut.py`, y qué es un
microchip, `apps/patients/microchip.py`; este módulo no sabe de ninguno de los
dos.

Está fuera de las dos apps porque las dos lo necesitan y ninguna puede importar
de la otra: `tutors` conoce a `patients` y `patients` no conoce a nadie
(`CLAUDE.md`). Bajarlo aquí es lo que impide que el día de mañana el Paciente
importe algo de `tutors` para reaprovechar quince líneas.

Son campos de modelo y no validadores sueltos porque lo que hacen no es decir
«esto está mal»: es decidir **cómo se guarda**. Un validador corre después de que
el valor ya esté puesto en el objeto, así que dejaría entrar «900.123.456.789.012»
y «900123456789012» como dos cosas distintas y las dos válidas, y el microchip
único por Clínica no significaría nada.

Puestos en el modelo, la normalización ocurre pase lo que pase: en el
formulario, en el importador del ticket 18, en un comando o en un test. No hay
que acordarse de llamar a nadie.
"""

from django import forms
from django.db import models


class CampoQueNormaliza(models.CharField):
    """Un `CharField` que pasa por su normalizador al entrar.

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

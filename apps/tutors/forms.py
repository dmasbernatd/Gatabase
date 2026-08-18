"""Formulario de la ficha de Tutor.

Ofrece exactamente los datos personales del Tutor (`DATOS_PERSONALES`), y no la
Clínica: esa la pone `FormularioDeLaClinica` a partir de quien está rellenando la
ficha (ADR-0003).
"""

from apps.tenancy.aislamiento import FormularioDeLaClinica
from apps.tutors.models import Tutor


class TutorForm(FormularioDeLaClinica):
    """Alta y corrección de la ficha de un Tutor."""

    class Meta:
        model = Tutor
        fields = list(Tutor.DATOS_PERSONALES)

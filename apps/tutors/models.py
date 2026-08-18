"""Tutor: la persona responsable de un Paciente ante la clínica y ante la ley.

Aquí está en su forma mínima — nombre y teléfono — porque lo que este ticket
demuestra es el aislamiento por Clínica, no la ficha. El RUT, el correo y el
Consentimiento de contacto llegan en los tickets 05 y 06.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.tenancy.aislamiento import ModeloDeLaClinica


class Tutor(ModeloDeLaClinica):
    """Persona responsable de un Paciente. No es un Usuario del sistema."""

    nombre = models.CharField(_("nombre"), max_length=200)
    telefono = models.CharField(_("teléfono"), max_length=30, blank=True)

    class Meta:
        verbose_name = _("Tutor")
        verbose_name_plural = _("Tutores")
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

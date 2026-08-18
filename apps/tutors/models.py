"""Tutor: la persona responsable de un Paciente ante la clínica y ante la ley.

Aquí viven **solo** sus datos personales: cómo se llama y por dónde se le
contacta. Los datos clínicos son del Paciente y viven en `patients`, y esa
separación no es cosmética (ADR-0004): un Tutor puede exigir la supresión de sus
datos personales mientras la Historia clínica de sus Pacientes —de la que es
titular el animal, no él— tiene que conservarse. Anonimizar (ticket 20) será
vaciar `DATOS_PERSONALES` de esta tabla sin tocar ninguna otra.

El RUT y el Consentimiento de contacto llegan en los tickets 06 y 15, y el
vínculo con el Paciente en el 07.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.tenancy.aislamiento import ModeloDeLaClinica


class Tutor(ModeloDeLaClinica):
    """Persona responsable de un Paciente. No es un Usuario del sistema."""

    # Solo el nombre es obligatorio. En el mostrador a veces no hay más que un
    # nombre y un teléfono, y exigir el resto empujaría a rellenarlo con
    # cualquier cosa, que es peor que un hueco: un dato falso no se distingue.
    nombre = models.CharField(_("nombre"), max_length=200)
    apellidos = models.CharField(_("apellidos"), max_length=200, blank=True)
    telefono = models.CharField(_("teléfono"), max_length=30, blank=True)
    email = models.EmailField(_("correo"), blank=True)
    direccion = models.CharField(_("dirección"), max_length=250, blank=True)

    # Lo que desaparece al anonimizar al Tutor, y lo que el formulario ofrece
    # rellenar. `tests/test_fichas_de_tutor.py` comprueba que no hay en esta
    # tabla ningún otro campo: un dato clínico aquí sobreviviría al derecho de
    # supresión, y un dato personal fuera de aquí se le escaparía.
    DATOS_PERSONALES = ("nombre", "apellidos", "telefono", "email", "direccion")

    class Meta:
        verbose_name = _("Tutor")
        verbose_name_plural = _("Tutores")
        # Por apellidos, que es como se busca a alguien en un fichero.
        ordering = ["apellidos", "nombre"]
        indexes = [
            models.Index(fields=["clinic", "apellidos", "nombre"], name="tutor_por_apellidos")
        ]

    def __str__(self):
        return f"{self.nombre} {self.apellidos}".strip()

"""Tutor: la persona responsable de un Paciente ante la clínica y ante la ley.

Aquí viven **solo** sus datos personales: cómo se llama y por dónde se le
contacta. Los datos clínicos son del Paciente y viven en `patients`, y esa
separación no es cosmética (ADR-0004): un Tutor puede exigir la supresión de sus
datos personales mientras la Historia clínica de sus Pacientes —de la que es
titular el animal, no él— tiene que conservarse. Anonimizar (ticket 20) será
vaciar `DATOS_PERSONALES` de esta tabla sin tocar ninguna otra.

El Consentimiento de contacto llega en el ticket 15 y el vínculo con el Paciente
en el 07.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.tenancy.aislamiento import ModeloDeLaClinica
from apps.tutors.campos import CampoDeRut, CampoDeTelefono
from apps.tutors.rut import formateado


class Tutor(ModeloDeLaClinica):
    """Persona responsable de un Paciente. No es un Usuario del sistema."""

    # Solo el nombre es obligatorio. En el mostrador a veces no hay más que un
    # nombre y un teléfono, y exigir el resto empujaría a rellenarlo con
    # cualquier cosa, que es peor que un hueco: un dato falso no se distingue.
    nombre = models.CharField(_("nombre"), max_length=200)
    apellidos = models.CharField(_("apellidos"), max_length=200, blank=True)
    # El RUT también es opcional, y no por comodidad: un Tutor extranjero no
    # tiene, y quien no quiera darlo tiene derecho a que se le atienda igual.
    # Cuando está, es único dentro de la Clínica —nunca a nivel global, que ya
    # sería un fichero de personas por encima de las Clínicas (ADR-0003)—, y por
    # eso el hueco se guarda como cadena vacía y la restricción lo deja fuera:
    # dos Tutores sin RUT no son el mismo Tutor.
    rut = CampoDeRut(_("RUT"), max_length=9, blank=True)
    # No es único a propósito: una familia comparte número, y dos Tutores con el
    # mismo teléfono son lo normal. Que se repita se avisa al guardar, no se
    # impide.
    telefono = CampoDeTelefono(_("teléfono"), max_length=16, blank=True)
    email = models.EmailField(_("correo"), blank=True)
    direccion = models.CharField(_("dirección"), max_length=250, blank=True)

    # Lo que desaparece al anonimizar al Tutor, y lo que el formulario ofrece
    # rellenar. `tests/test_fichas_de_tutor.py` comprueba que no hay en esta
    # tabla ningún otro campo: un dato clínico aquí sobreviviría al derecho de
    # supresión, y un dato personal fuera de aquí se le escaparía.
    DATOS_PERSONALES = ("nombre", "apellidos", "rut", "telefono", "email", "direccion")

    class Meta:
        verbose_name = _("Tutor")
        verbose_name_plural = _("Tutores")
        # Por apellidos, que es como se busca a alguien en un fichero.
        ordering = ["apellidos", "nombre"]
        indexes = [
            models.Index(fields=["clinic", "apellidos", "nombre"], name="tutor_por_apellidos")
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["clinic", "rut"],
                condition=~models.Q(rut=""),
                name="rut_unico_dentro_de_la_clinica",
            )
        ]

    def __str__(self):
        return f"{self.nombre} {self.apellidos}".strip()

    @property
    def rut_a_la_chilena(self):
        """El RUT como se lee y se dicta: «12.345.678-5». Vacío si no tiene."""
        return formateado(self.rut)

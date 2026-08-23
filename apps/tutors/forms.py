"""Formulario de la ficha de Tutor.

Ofrece exactamente los datos personales del Tutor (`DATOS_PERSONALES`), y no la
Clínica: esa la pone `FormularioDeLaClinica` a partir de quien está rellenando la
ficha (ADR-0003).

El RUT y el teléfono llegan ya normalizados de sus campos (`campos.py`), así que
aquí se pueden comparar con lo que ya hay en la Clínica sin volver a interpretar
nada. Las dos comparaciones acaban distinto a propósito:

- **El RUT repetido no deja guardar.** Dos fichas con el mismo RUT son la misma
  persona duplicada, y un duplicado sale caro de deshacer más tarde. El aviso
  lleva a la ficha que ya existe, que es lo que recepción necesita: casi siempre
  venía a corregir esa.
- **El teléfono repetido sí deja guardar.** Una familia comparte número y eso no
  es un error. Se avisa después de guardar, y de eso se encarga la vista, porque
  un aviso que no impide nada solo tiene sentido si hubo guardado.

Nombrar al otro Tutor es enseñar sus datos personales, así que quien lo enseñe
—la vista— lo anota en el Registro de acceso (ADR-0004).
"""

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.tenancy.aislamiento import FormularioDeLaClinica
from apps.tutors.models import Tutor


class TutorForm(FormularioDeLaClinica):
    """Alta y corrección de la ficha de un Tutor."""

    class Meta:
        model = Tutor
        fields = list(Tutor.DATOS_PERSONALES)

    # El Tutor que ya tenía el RUT que se acaba de escribir, si lo hay. La vista
    # lo mira para dejar constancia de que recepción acaba de verle el nombre.
    tutor_con_el_mismo_rut = None

    def clean_rut(self):
        rut = self.cleaned_data["rut"]
        if not rut:
            return rut

        self.tutor_con_el_mismo_rut = self.los_demas().filter(rut=rut).first()
        if self.tutor_con_el_mismo_rut:
            raise ValidationError(
                format_html(
                    _("Este RUT ya es el de {ficha}, en esta misma Clínica."),
                    ficha=self.enlace_a(self.tutor_con_el_mismo_rut),
                ),
                code="rut_repetido",
            )
        return rut

    def quienes_comparten_el_telefono(self):
        """Los demás Tutores de la Clínica con el teléfono que se acaba de guardar.

        Se pregunta después de guardar y no al validar: no impide nada, y así el
        aviso habla de fichas que existen las dos.
        """
        telefono = self.cleaned_data.get("telefono")
        if not telefono:
            return []
        return list(self.los_demas().filter(telefono=telefono))

    @staticmethod
    def enlace_a(tutor):
        """El nombre del Tutor, enlazado a su ficha.

        Lo usa también la vista, para el aviso del teléfono compartido: los dos
        avisos señalan lo mismo —otra ficha de esta Clínica— y se escriben igual.
        """
        return format_html(
            '<a href="{}">{}</a>', reverse("tutors:ficha", args=[tutor.pk]), str(tutor)
        )

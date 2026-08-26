"""El formulario de subida: un archivo y nada más.

No pregunta la Clínica, y no es un olvido: lo importado es de la Clínica de quien
importa y no hay manera de decir otra cosa, porque un `<select>` de Clínicas sería
una frontera dibujada en el navegador (ADR-0003).

Tampoco pregunta el separador ni la codificación. Los adivina `planilla.py`, y
adivinar mal no rompe nada —se ve en la vista previa antes de guardar—, mientras
que preguntarlo obligaría al admin a saber con qué guardó su Excel, que es
exactamente lo que no sabe.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

# Lo que puede ocupar una planilla de Tutores, con mucho margen: una clínica con
# diez mil Tutores no llega a un megabyte. El límite no está por el disco, sino
# para que un archivo equivocado —el volcado de la base anterior, un ZIP— se
# rechace al subirlo y no después de intentar leerlo entero como texto.
TAMANO_MAXIMO = 5 * 1024 * 1024


class PlanillaForm(forms.Form):
    """El archivo que se va a examinar antes de importar nada."""

    archivo = forms.FileField(
        label=_("Planilla"),
        help_text=_("Un archivo CSV. Todavía no se guarda nada: primero se enseña qué entraría."),
    )

    def clean_archivo(self):
        subido = self.cleaned_data["archivo"]
        if subido.size > TAMANO_MAXIMO:
            raise forms.ValidationError(
                _("La planilla ocupa más de %(maximo)s MB. ¿Seguro que es la planilla?"),
                code="planilla_demasiado_grande",
                params={"maximo": TAMANO_MAXIMO // (1024 * 1024)},
            )
        return subido

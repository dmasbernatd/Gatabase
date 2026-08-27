"""Lo único que hay que rellenar aquí: el nombre de la Clínica que se va a cerrar.

Un botón con una pregunta de «¿seguro?» delante se pulsa dos veces igual de
rápido. Escribir el nombre no es una traba burocrática: es lo que obliga a mirar
qué Clínica se está cerrando, que es la equivocación que este formulario existe
para evitar — la de quien administra dos y tiene abiertas las dos pestañas.
"""

from django import forms
from django.utils.translation import gettext_lazy as _


class CierreForm(forms.Form):
    """Confirma el cierre de una Clínica escribiendo su nombre."""

    nombre = forms.CharField(
        label=_("Escriba el nombre de la Clínica para confirmar"),
        max_length=120,
    )

    def __init__(self, *args, clinica, **kwargs):
        super().__init__(*args, **kwargs)
        self.clinica = clinica

    def clean_nombre(self):
        """Tal como se llama, sin más indulgencia que la de los espacios sobrantes.

        No se comparan mayúsculas ni tildes a la ligera —como sí hace la búsqueda
        del mostrador— a propósito: aquí no se está buscando nada, se está
        confirmando que se ha leído lo que dice la pantalla.
        """
        escrito = self.cleaned_data["nombre"].strip()
        if escrito != self.clinica.nombre:
            raise forms.ValidationError(
                _("Eso no es el nombre de la Clínica. No se ha cerrado nada."),
                code="no_es_el_nombre",
            )
        return escrito

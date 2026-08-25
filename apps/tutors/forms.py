"""Formulario de la ficha de Tutor.

Ofrece exactamente los datos personales del Tutor (`DATOS_PERSONALES`), y no la
Clínica: esa la pone `FormularioDeLaClinica` a partir de quien está rellenando la
ficha (ADR-0003).

A quién se parece la ficha que se está escribiendo lo resuelve
`apps/coincidencias.py`; aquí solo se dice **por dónde** se puede confundir a un
Tutor con otro, que es un hecho de la ficha y no de ninguna pantalla. El RUT y el
teléfono llegan ya normalizados de sus campos (`campos.py`), así que se comparan
con lo que ya hay en la Clínica sin volver a interpretar nada, y las dos
comparaciones acaban distinto a propósito:

- **El RUT repetido no deja guardar.** Dos fichas con el mismo RUT son la misma
  persona duplicada, y además la base de datos no las admite (ADR-0003). El
  aviso lleva a la ficha que ya existe, que es lo que recepción necesita: casi
  siempre venía a corregir esa.
- **El teléfono repetido sí deja guardar.** Una familia comparte número y eso no
  es un error. Se avisa mientras se escribe y otra vez después de guardar, y de
  lo segundo se encarga la vista, porque un aviso que no impide nada solo tiene
  sentido si hubo guardado.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.coincidencias import FormularioQueSeParece, Parecido
from apps.tutors.consentimiento import LoQueDijo, como_esta
from apps.tutors.models import Tutor


class TutorForm(FormularioQueSeParece):
    """Alta y corrección de la ficha de un Tutor."""

    class Meta:
        model = Tutor
        fields = list(Tutor.DATOS_PERSONALES)

    # Por dónde se confunde a un Tutor con otro que ya está en la Clínica. El
    # nombre no entra: dos personas se llaman igual con toda normalidad, y
    # avisar de cada tocayo sería un aviso que nadie mira.
    PARECIDOS = (
        Parecido(
            "rut",
            _("Este RUT ya es el de {ficha}, en esta misma Clínica."),
            codigo="rut_repetido",
        ),
        Parecido("telefono", _("Este teléfono es también el de {ficha}.")),
    )

    DETECCION = "tutors:coincidencias"


class ConsentimientoDeContactoForm(forms.Form):
    """Lo que el Tutor dice de cada canal, tal como se le pregunta en el mostrador.

    No es un `ModelForm` porque lo que se rellena no es una fila: es una
    respuesta por canal, y cada una que cambie dejará su propia declaración con
    su fecha. Los campos se arman a partir del catálogo (`Canal`) y no a mano,
    para que añadir un canal no dependa de acordarse de tocar esta pantalla.

    **Ningún campo es obligatorio, y el hueco no es un «no».** Recepción pregunta
    por lo que puede preguntar —el Tutor llamó por otra cosa y solo dio el
    WhatsApp—, así que un canal en blanco es un canal del que no se habló y se
    queda como estaba. Tratarlo como una negativa convertiría cada visita a esta
    página en una revocación silenciosa de los otros dos.

    Lo que se puede contestar —y por qué «no consta» no está entre las opciones—
    lo dice `LoQueDijo`.
    """

    def __init__(self, *args, tutor, **kwargs):
        super().__init__(*args, **kwargs)
        self.tutor = tutor
        for estado in como_esta(tutor):
            self.fields[estado.canal] = forms.ChoiceField(
                label=estado.etiqueta,
                choices=LoQueDijo.choices,
                # Lo que ya constaba viene puesto: quien atiende no tiene que
                # acordarse de lo que este Tutor dijo hace ocho meses.
                initial=estado.lo_que_dijo,
                required=False,
                widget=forms.RadioSelect,
                help_text=estado.a_la_vista,
            )

    def guardar(self):
        """Deja dicho lo contestado y devuelve las declaraciones que hizo falta.

        Vacía cuando nada cambió, que es lo que mira la vista para decidir si
        hubo modificación que anotar: abrir la página y volver a guardarla igual
        no es un cambio en los datos de nadie.
        """
        return [
            declaracion
            for canal, contestado in self.cleaned_data.items()
            if contestado
            and (
                declaracion := self.tutor.deja_dicho_sobre_el_contacto(
                    canal, otorgado=contestado == LoQueDijo.SI
                )
            )
        ]

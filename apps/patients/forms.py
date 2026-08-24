"""Formularios de la ficha de Paciente y del Vínculo con un Tutor.

La ficha ofrece los datos del animal y ninguno de su Tutor: quién responde por él
es el Vínculo, y son dos cosas que se corrigen por separado porque cambian por
motivos distintos (ADR-0004). La Clínica no se elige aquí, como en toda ficha:
sale de quien la está rellenando (ADR-0003).

De la especie y la raza se encarga `catalogo.py`. Este formulario solo hace lo
que no puede hacerse sin saber las dos a la vez: la raza se lee contra el
catálogo **de la especie que se acaba de elegir**, así que se resuelve en el
`clean` conjunto y no en un `clean_raza`, que correría sin saber de qué animal se
habla.
"""

from django import forms
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.patients.catalogo import Especie, canonica, razas_de
from apps.patients.models import Paciente, Sexo
from apps.tenancy.aislamiento import FormularioDeLaClinica
from apps.tutors.models import Tutor

# El `id` de la lista de sugerencias de razas. Lo comparten el campo —que la
# nombra en su atributo `list`— y la plantilla que la pinta, y por eso no se
# escribe a mano en ninguno de los dos.
SUGERENCIAS_DE_RAZA = "razas"


class PacienteForm(FormularioDeLaClinica):
    """Alta y corrección de la ficha de un Paciente."""

    # La plantilla lo lee de aquí en vez de escribir "razas" a mano: el campo de
    # la raza y la lista de sugerencias tienen que nombrarse igual o el
    # autocompletado deja de funcionar en silencio.
    SUGERENCIAS_DE_RAZA = SUGERENCIAS_DE_RAZA

    class Meta:
        model = Paciente
        fields = [
            "nombre",
            "especie",
            "raza",
            "sexo",
            "fecha_de_nacimiento",
            "color",
            "observaciones",
        ]
        widgets = {
            # Cambiar de especie cambia las razas que se sugieren, sin recargar
            # la página. Sin JavaScript no se pierde nada: la lista que llegó
            # servida sigue siendo la de la especie que la ficha ya tenía, y lo
            # que se escriba a mano vale igual.
            "especie": forms.Select(
                attrs={
                    "hx-get": reverse_lazy("patients:razas"),
                    "hx-target": f"#{SUGERENCIAS_DE_RAZA}",
                    "hx-swap": "outerHTML",
                }
            ),
            # `list` y no un `<select>`: el catálogo de razas sugiere, no manda.
            # Lo que no está en la lista se escribe, que es la opción «otra».
            "raza": forms.TextInput(attrs={"list": SUGERENCIAS_DE_RAZA, "autocomplete": "off"}),
            "fecha_de_nacimiento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # El rótulo de la opción vacía lo pone Django, y en esta versión llega
        # sin traducir al es-CL: recepción vería «- Select an option -» en dos
        # desplegables. Puestos a escribirlo, que diga lo que hay que hacer y,
        # en el sexo, lo que significa dejarlo en blanco: no se sabe todavía,
        # que es una respuesta legítima en un animal recién recogido.
        self.fields["especie"].choices = [("", _("Elija una especie")), *Especie.choices]
        self.fields["sexo"].choices = [("", _("Todavía no se sabe")), *Sexo.choices]

    def clean_fecha_de_nacimiento(self):
        """Un Paciente no puede haber nacido mañana.

        Es el error de tecleo más fácil de cometer en una casilla de fecha —el
        año en curso por el anterior— y el más difícil de ver después, cuando lo
        único raro es una edad imposible en una ficha.
        """
        fecha = self.cleaned_data["fecha_de_nacimiento"]
        if fecha and fecha > timezone.localdate():
            raise forms.ValidationError(_("Esa fecha todavía no ha llegado."), code="fecha_futura")
        return fecha

    def clean(self):
        """Deja la raza con la ortografía del catálogo cuando se le parece.

        Sin esto, «bulldog frances» y «Bulldog Francés» serían dos razas para
        cualquier recuento, que es justo lo que el catálogo viene a evitar.
        """
        datos = super().clean()
        if datos.get("raza"):
            datos["raza"] = canonica(datos.get("especie"), datos["raza"])
        return datos

    @property
    def razas_sugeridas(self):
        """Las razas que se le ofrecen a la especie elegida ahora mismo.

        Sale del formulario y no de la vista porque es el formulario quien sabe
        qué especie tiene delante: la que se acaba de elegir, la de la ficha que
        se está corrigiendo, o ninguna en un alta recién abierta.
        """
        return razas_de(self["especie"].value())


class VinculoForm(forms.Form):
    """Sumar un Tutor a los que responden por un Paciente.

    El Paciente no es un campo: viene de la URL de su ficha. Y no es un
    `ModelForm` porque no compone un Vínculo campo a campo — de eso sabe el
    Tutor (`se_hace_cargo_de`), que es quien tiene que decidir además si el
    Paciente se queda sin responsable. Aquí solo se elige a quién.

    Los Tutores que se ofrecen son los de la Clínica que todavía no están
    vinculados: volver a elegir a uno que ya está no es un error del que haya que
    avisar, es una opción que no debería haberse ofrecido. Que la lista salga de
    la Clínica del formulario es lo que impide vincular a un Tutor de otra
    (ADR-0003).
    """

    tutor = forms.ModelChoiceField(
        queryset=Tutor.de_todas_las_clinicas.none(),
        label=_("Tutor"),
        empty_label=_("Elija un Tutor"),
    )
    responsable = forms.BooleanField(label=_("Es el responsable"), required=False)

    def __init__(self, *args, clinica, paciente, **kwargs):
        super().__init__(*args, **kwargs)
        self.paciente = paciente
        self.fields["tutor"].queryset = Tutor.de_todas_las_clinicas.filter(
            clinic=clinica
        ).exclude(pk__in=paciente.quienes_responden.values("tutor"))

    def guardar(self):
        """Deja constancia de que ese Tutor se hace cargo de este Paciente."""
        return self.cleaned_data["tutor"].se_hace_cargo_de(
            self.paciente, responsable=self.cleaned_data["responsable"]
        )

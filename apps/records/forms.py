"""El formulario con el que se escribe una Consulta mientras se atiende.

Lo que no se elige aquí: la Clínica, que sale de quien lo rellena (ADR-0003); el
Paciente, que sale de la ficha por la que se entró; y el veterinario y la Sede,
que salen de quién está trabajando y dónde. Ninguno de los cuatro es un campo
del formulario, y no es por comodidad: un `<select>` de veterinarios sería una
Consulta firmable con el nombre de otro, que es exactamente lo que un documento
con valor legal no puede permitir.

Nada es obligatorio, y eso es lo que hace que sirva: la Consulta se abre al
empezar a atender, cuando todavía no se sabe nada, y se guarda cuantas veces
haga falta mientras se va sabiendo. Un formulario que exigiera el diagnóstico
para dejar guardar obligaría a escribir un punto, y un punto no se distingue de
un dato que nadie tomó.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.records.models import Consulta
from apps.tenancy.aislamiento import FormularioDeLaClinica

# Las secciones del método SOAP, con lo que se le pregunta al veterinario en
# cada una. Están aquí y no en la plantilla porque el orden es clínico, no de
# maquetación: es como se piensa un caso, y la plantilla lo pinta.
AYUDAS = {
    "motivo": _("En palabras del Tutor: por qué vino."),
    "subjetivo": _("Lo que cuenta el Tutor: la anamnesis."),
    "objetivo": _("Lo que usted observa y mide en la exploración."),
    "evaluacion": _("Su interpretación de lo anterior."),
    "plan": _("Qué se va a hacer: pruebas, tratamiento, revisión."),
    "folio_de_la_receta_del_sag": _(
        "El folio de la receta que emitió en la plataforma del SAG, si emitió alguna. "
        "Este sistema no emite recetas."
    ),
}


class ConsultaForm(FormularioDeLaClinica):
    """Abre una Consulta y la escribe mientras está abierta.

    El mismo formulario para las dos cosas, como la ficha del Paciente: abrirla
    es guardarla por primera vez, y lo que cambia entre una vez y la siguiente
    no es lo que se pregunta.
    """

    class Meta:
        model = Consulta
        fields = [
            "motivo",
            "subjetivo",
            "objetivo",
            "evaluacion",
            "plan",
            "diagnostico",
            "tratamiento_indicado",
            "folio_de_la_receta_del_sag",
        ]
        widgets = {
            "motivo": forms.Textarea(attrs={"rows": 2}),
            "subjetivo": forms.Textarea(attrs={"rows": 4}),
            "objetivo": forms.Textarea(attrs={"rows": 4}),
            "evaluacion": forms.Textarea(attrs={"rows": 3}),
            "plan": forms.Textarea(attrs={"rows": 3}),
            "diagnostico": forms.Textarea(attrs={"rows": 2}),
            "tratamiento_indicado": forms.Textarea(attrs={"rows": 3}),
            # Sin autocompletado: el folio lo dicta la pantalla del SAG, y uno
            # sugerido de otra Consulta es una receta atribuida al animal que no
            # era.
            "folio_de_la_receta_del_sag": forms.TextInput(attrs={"autocomplete": "off"}),
        }

    def __init__(self, *args, paciente, veterinario, sede, **kwargs):
        """Recibe de la vista lo que no se elige: a quién, quién y dónde.

        Los tres se exigen por nombre y sin valor por omisión a propósito: una
        vista que se olvide de pasarlos falla al construir el formulario, no al
        guardar una Consulta a medio atribuir.
        """
        super().__init__(*args, **kwargs)
        self.paciente = paciente
        self.veterinario = veterinario
        self.sede = sede
        for campo, ayuda in AYUDAS.items():
            self.fields[campo].help_text = ayuda

    def save(self, commit=True):
        """Guarda la Consulta con su Paciente, su autor y su Sede.

        Los tres se ponen solo al abrirla —cuando no hay `pk`— y no se vuelven a
        tocar: quién atendió es un hecho de aquella tarde, y reescribirlo en cada
        guardado haría que la Consulta la firmara quien la abrió por última vez.
        En el ticket 01 esto no puede pasar todavía, porque solo su autor la
        escribe; dejarlo escrito aquí es lo que hace que siga sin poder pasar.
        """
        consulta = super().save(commit=False)
        if consulta.pk is None:
            consulta.paciente = self.paciente
            consulta.veterinario = self.veterinario
            consulta.sede = self.sede
        if commit:
            consulta.save()
        return consulta

"""Formularios de la ficha de Paciente, del Vínculo con un Tutor y de su estado.

La ficha ofrece los datos del animal y ninguno de su Tutor: quién responde por él
es el Vínculo, y son dos cosas que se corrigen por separado porque cambian por
motivos distintos (ADR-0004). La Clínica no se elige aquí, como en toda ficha:
sale de quien la está rellenando (ADR-0003).

De la especie y la raza se encarga `catalogo.py`. Este formulario solo hace lo
que no puede hacerse sin saber las dos a la vez: la raza se lee contra el
catálogo **de la especie que se acaba de elegir**, así que se resuelve en el
`clean` conjunto y no en un `clean_raza`, que correría sin saber de qué animal se
habla. Con el microchip y el estado de identificación pasa lo mismo, y por eso
comparten `clean`: la única combinación imposible se ve mirando los dos.

El microchip llega ya normalizado de su campo (`campos.py`), así que aquí se
puede comparar con lo que ya hay en la Clínica sin volver a interpretar nada. Se
compara como el RUT del Tutor y acaba igual: **repetido no deja guardar**, porque
dos fichas con el mismo chip son el mismo animal registrado dos veces y un
duplicado sale caro de deshacer. El aviso lleva a la ficha que ya existe, que es
a lo que recepción venía casi siempre.

Nombrar al otro Paciente es enseñar su ficha, así que quien lo enseñe —la vista—
lo anota en el Registro de acceso (ADR-0004): la ley protege la ficha del animal
igual que la de su Tutor, porque por ella se llega a él.

Que el animal muriera o dejara de venir no se corrige aquí: tiene formulario
propio (`EstadoDelPacienteForm`), porque no es un dato mal escrito sino un hecho
que cambió.
"""

from django import forms
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.patients.catalogo import Especie, canonica, razas_de
from apps.patients.estados import EstadoDelPaciente
from apps.patients.models import EstadoDeIdentificacion, Paciente, Sexo
from apps.tenancy.aislamiento import FormularioDeLaClinica
from apps.tutors.models import Tutor

# El `id` de la lista de sugerencias de razas. Lo comparten el campo —que la
# nombra en su atributo `list`— y la plantilla que la pinta, y por eso no se
# escribe a mano en ninguno de los dos.
SUGERENCIAS_DE_RAZA = "razas"


def sin_fechas_futuras(fecha):
    """Devuelve la fecha, o falla si todavía no ha llegado.

    Lo comparten el nacimiento y el fallecimiento porque es el mismo error de
    tecleo —el año en curso por el anterior— y el mismo remedio. Es además el
    más difícil de ver después: lo único raro que deja en la ficha es una edad
    imposible o un animal que murió el mes que viene.
    """
    if fecha and fecha > timezone.localdate():
        raise forms.ValidationError(_("Esa fecha todavía no ha llegado."), code="fecha_futura")
    return fecha


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
            "microchip",
            "estado_de_identificacion",
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
            # Sin autocompletado del navegador: lo que va aquí lo dicta un
            # certificado o lo escupe un lector, nunca la memoria del navegador,
            # y un chip sugerido de otra ficha es un animal confundido con otro.
            "microchip": forms.TextInput(attrs={"autocomplete": "off", "inputmode": "numeric"}),
        }

    # El Paciente que ya tenía el microchip que se acaba de escribir, si lo hay.
    # La vista lo mira para dejar constancia de que recepción acaba de ver su
    # ficha sin haberla abierto.
    paciente_con_el_mismo_microchip = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # El rótulo de la opción vacía lo pone Django, y en esta versión llega
        # sin traducir al es-CL: recepción vería «- Select an option -» en dos
        # desplegables. Puestos a escribirlo, que diga lo que hay que hacer y,
        # en el sexo, lo que significa dejarlo en blanco: no se sabe todavía,
        # que es una respuesta legítima en un animal recién recogido.
        self.fields["especie"].choices = [("", _("Elija una especie")), *Especie.choices]
        self.fields["sexo"].choices = [("", _("Todavía no se sabe")), *Sexo.choices]
        # El hueco del estado de identificación significa algo, y hay que poder
        # elegirlo: no es «sin chip», es que nadie lo ha preguntado. Ver
        # `EstadoDeIdentificacion`.
        self.fields["estado_de_identificacion"].choices = [
            ("", _("Todavía no se ha preguntado")),
            *EstadoDeIdentificacion.choices,
        ]

    def clean_fecha_de_nacimiento(self):
        """Un Paciente no puede haber nacido mañana."""
        return sin_fechas_futuras(self.cleaned_data["fecha_de_nacimiento"])

    def clean_microchip(self):
        """Rechaza un chip que ya es el de otro Paciente **de esta Clínica**.

        Solo de esta: el número identifica al animal en todo Chile, pero cada
        Clínica tiene su propio Paciente con su propia Historia clínica
        (ADR-0001). Que el mismo chip exista en otra Clínica es correcto y no se
        detecta — detectarlo sería cruzar datos entre tenants, que es lo que el
        ADR prohíbe—, y eso lo garantiza `los_demas()`, que nunca sale de la
        Clínica del formulario.
        """
        microchip = self.cleaned_data["microchip"]
        if not microchip:
            return microchip

        self.paciente_con_el_mismo_microchip = self.los_demas().filter(microchip=microchip).first()
        if self.paciente_con_el_mismo_microchip:
            raise forms.ValidationError(
                format_html(
                    _("Este microchip ya es el de {ficha}, en esta misma Clínica."),
                    ficha=self.enlace_a(self.paciente_con_el_mismo_microchip),
                ),
                code="microchip_repetido",
            )
        return microchip

    def clean(self):
        """Deja la raza con la ortografía del catálogo cuando se le parece, y no
        deja apuntar un chip en un Paciente que dice no tener ninguno.

        Lo de la raza, porque «bulldog frances» y «Bulldog Francés» serían dos
        razas para cualquier recuento, que es justo lo que el catálogo viene a
        evitar.

        Lo del chip, porque es la **única** combinación de las dos casillas que
        se contradice a sí misma, y sale de corregir una y olvidar la otra. Las
        demás son estados reales y no se tocan: un chip implantado en otra
        clínica cuyo número el Tutor no trae es lo más corriente del mostrador, y
        exigir el número ahí obligaría a inventárselo.
        """
        datos = super().clean()
        if datos.get("raza"):
            datos["raza"] = canonica(datos.get("especie"), datos["raza"])
        if datos.get("microchip") and datos.get("estado_de_identificacion") == (
            EstadoDeIdentificacion.SIN_CHIP
        ):
            self.add_error(
                "estado_de_identificacion",
                forms.ValidationError(
                    _("Tiene un microchip apuntado: no puede estar «sin chip»."),
                    code="chip_que_se_contradice",
                ),
            )
        return datos

    @staticmethod
    def enlace_a(paciente):
        """El nombre del Paciente, enlazado a su ficha."""
        return format_html(
            '<a href="{}">{}</a>', reverse("patients:ficha", args=[paciente.pk]), str(paciente)
        )

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


class EstadoDelPacienteForm(forms.Form):
    """Dejar constancia de que un Paciente murió o dejó de venir.

    Está fuera de la ficha, y esa es la decisión: la ficha son los datos del
    animal y se corrigen porque estaban mal escritos; el estado es un hecho que
    cambió en el mundo. Juntarlos pondría el fallecimiento a un descuido de
    distancia dentro del mismo formulario que se abre para arreglar una letra
    del nombre — y además la ficha de un fallecido ya no se corrige
    (`Paciente.se_puede_corregir`), así que ahí no cabría.

    No es un `ModelForm` por lo mismo que `VinculoForm` no lo es: no compone un
    Paciente campo a campo. De dejarlo coherente —limpiar la fecha cuando el
    animal no consta muerto— sabe el Paciente (`cambiar_de_estado`), que es
    quien tiene que saberlo aunque el cambio no venga de esta pantalla.
    """

    estado = forms.ChoiceField(choices=EstadoDelPaciente, label=_("Estado"))
    fecha_de_fallecimiento = forms.DateField(
        label=_("Fecha de fallecimiento"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        # Se pide, no se exige: el Tutor avisa a veces meses después y no
        # siempre recuerda el día. Un hueco aquí es «murió, no consta cuándo»,
        # que es verdad; una fecha inventada, no.
        help_text=_("Si no se sabe, déjela en blanco."),
    )

    def __init__(self, *args, paciente, **kwargs):
        super().__init__(*args, **kwargs)
        self.paciente = paciente
        self.fields["estado"].initial = paciente.estado
        self.fields["fecha_de_fallecimiento"].initial = paciente.fecha_de_fallecimiento

    def clean_fecha_de_fallecimiento(self):
        """Nadie muere mañana."""
        return sin_fechas_futuras(self.cleaned_data["fecha_de_fallecimiento"])

    def clean(self):
        """Un Paciente no puede haber muerto antes de nacer.

        Es la otra mitad del error de tecleo que `sin_fechas_futuras` no ve: el
        año equivocado hacia atrás. Solo se comprueba cuando la ficha trae fecha
        de nacimiento, que es opcional — de un animal recogido en la calle no se
        sabe.
        """
        datos = super().clean()
        fecha = datos.get("fecha_de_fallecimiento")
        nacimiento = self.paciente.fecha_de_nacimiento
        if fecha and nacimiento and fecha < nacimiento:
            self.add_error(
                "fecha_de_fallecimiento",
                forms.ValidationError(
                    _("Esa fecha es anterior a la de nacimiento."), code="antes_de_nacer"
                ),
            )
        return datos

    def guardar(self):
        """Deja al Paciente en el estado elegido y lo devuelve."""
        return self.paciente.cambiar_de_estado(
            self.cleaned_data["estado"], self.cleaned_data["fecha_de_fallecimiento"]
        )

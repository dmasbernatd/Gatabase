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

A quién se parece la ficha que se está escribiendo lo resuelve
`apps/coincidencias.py`; aquí solo se dice **por dónde** se puede confundir a un
Paciente con otro, que es el microchip y nada más. El nombre no entra a
propósito: dos animales de la misma familia se llaman parecido con toda
normalidad, y de los que su Tutor ya tiene se encarga la página del alta, que
los enseña enteros porque los tiene a mano sin buscar nada.

El chip llega ya normalizado de su campo (`campos.py`), así que se compara con lo
que ya hay en la Clínica sin volver a interpretar nada. Se compara como el RUT
del Tutor y acaba igual: **repetido no deja guardar**, porque dos fichas con el
mismo chip son el mismo animal registrado dos veces —y porque la base de datos no
las admite (ADR-0001)—. El aviso lleva a la ficha que ya existe, que es a lo que
recepción venía casi siempre.

Nombrar al otro Paciente es enseñar su ficha, así que quien lo enseñe —la vista—
lo anota en el Registro de acceso (ADR-0004): la ley protege la ficha del animal
igual que la de su Tutor, porque por ella se llega a él.

Que el animal muriera o dejara de venir no se corrige aquí: tiene formulario
propio (`EstadoDelPacienteForm`), porque no es un dato mal escrito sino un hecho
que cambió. Y que cambiara de manos, otro (`TraspasoForm`): tampoco es un dato
mal escrito, y además no toca la ficha del animal en absoluto — el Paciente
sigue siendo el mismo con la misma Historia clínica, y lo único que cambia es
quién responde por él.
"""

from django import forms
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.coincidencias import FormularioQueSeParece, Parecido
from apps.patients.catalogo import Especie, canonica, razas_de
from apps.patients.estados import EstadoDelPaciente
from apps.patients.models import EstadoDeIdentificacion, Paciente, Sexo
from apps.tutors.models import Tutor
from apps.tutors.traspaso import traspasar

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


class PacienteForm(FormularioQueSeParece):
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

    # Por dónde se confunde a un Paciente con otro que ya está en la Clínica.
    # Solo dentro de ella: el número identifica al animal en todo Chile, pero
    # cada Clínica tiene su propio Paciente con su propia Historia clínica
    # (ADR-0001). Que el mismo chip exista en otra Clínica es correcto y no se
    # detecta —detectarlo sería cruzar datos entre tenants—, y eso lo garantiza
    # `los_demas()`, que nunca sale de la Clínica del formulario.
    PARECIDOS = (
        Parecido(
            "microchip",
            _("Este microchip ya es el de {ficha}, en esta misma Clínica."),
            codigo="microchip_repetido",
        ),
    )

    DETECCION = "patients:coincidencias"

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
        # Volver a activo a un Paciente del que ya no responde nadie dejaría una
        # ficha de trabajo sin teléfono al que llamar: es la misma regla que
        # impide cerrar el Vínculo del responsable, por el otro lado. Se llega
        # aquí cuando el animal se traspasó estando inactivo y después vuelve, y
        # el remedio es vincularle antes a quien lo trae ahora.
        if (
            not self.paciente.esta_activo
            and datos.get("estado") == EstadoDelPaciente.ACTIVO
            and self.paciente.vinculo_responsable is None
        ):
            self.add_error(
                "estado",
                forms.ValidationError(
                    _("Nadie responde por él: súmele antes el Tutor que lo trae."),
                    code="sin_responsable",
                ),
            )
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


class FechaDelCambioForm(forms.Form):
    """Lo que comparten cerrar un Vínculo y traspasar al Paciente: cuándo fue.

    La fecha se exige, al revés que la de fallecimiento: el cambio de manos se
    dice en el mostrador el día que pasa, y viene puesta la de hoy. Sin ella, un
    Vínculo cerrado no serviría para lo que se cierra —saber quién tenía al
    animal en marzo—, y un «hasta que se cerró» no es una respuesta.
    """

    fecha = forms.DateField(
        label=_("Hasta"),
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        initial=timezone.localdate,
    )

    def clean_fecha(self):
        """Un animal no cambia de manos la semana que viene."""
        return sin_fechas_futuras(self.cleaned_data["fecha"])


class CierreDeVinculoForm(FechaDelCambioForm):
    """Que un Tutor dejó de responder por el Paciente.

    Cerrar y no borrar, que es de lo que va el ticket: quién lo trajo antes y
    hasta cuándo se conserva entero. De eso sabe el Vínculo (`cerrar`).

    El responsable de un Paciente activo no se cierra por aquí: dejaría una
    ficha que no dice a quién llamar. La regla la contesta el Vínculo, y el
    formulario solo la trae a la pantalla — así el motivo se escribe una vez y
    lo dicen igual la plantilla que esconde el enlace y el error de quien llegó
    con la URL en la mano.
    """

    def __init__(self, *args, vinculo, **kwargs):
        super().__init__(*args, **kwargs)
        self.vinculo = vinculo

    def clean(self):
        datos = super().clean()
        motivo = self.vinculo.por_que_no_se_puede_cerrar
        if motivo:
            raise forms.ValidationError(motivo, code="sin_responsable")
        return datos

    def guardar(self):
        """Cierra el Vínculo y lo devuelve."""
        return self.vinculo.cerrar(self.cleaned_data["fecha"])


class TraspasoForm(FechaDelCambioForm):
    """El Paciente cambia de manos: quién responde por él a partir de esa fecha.

    Es una sola pantalla y no dos porque es una sola operación (`traspaso.py`):
    cerrar el Vínculo del Tutor de antes sin decir quién lo releva dejaría, entre
    una cosa y la otra, un animal activo del que no responde nadie.

    Se ofrecen los Tutores de la Clínica menos el que ya responde por él, que es
    la única opción que no significaría nada. Los demás Tutores del Paciente sí
    se ofrecen: una pareja que se separa y uno de los dos se queda con el animal
    es exactamente esto, y ahí no se abre ningún Vínculo nuevo — se le pasa el
    cargo al que ya tenía.
    """

    tutor = forms.ModelChoiceField(
        queryset=Tutor.de_todas_las_clinicas.none(),
        label=_("Ahora responde"),
        empty_label=_("Elija un Tutor"),
    )

    # Primero a quién pasa el animal, que es la decisión; la fecha viene puesta.
    field_order = ["tutor", "fecha"]

    def __init__(self, *args, clinica, paciente, **kwargs):
        super().__init__(*args, **kwargs)
        self.paciente = paciente
        self.fields["tutor"].queryset = Tutor.de_todas_las_clinicas.filter(
            clinic=clinica
        ).exclude(pk__in=paciente.quienes_responden.filter(responsable=True).values("tutor"))

    def guardar(self):
        """Deja al Paciente en manos del Tutor elegido y devuelve su Vínculo."""
        return traspasar(self.paciente, self.cleaned_data["tutor"], self.cleaned_data["fecha"])

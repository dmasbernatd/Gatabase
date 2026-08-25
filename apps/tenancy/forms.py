"""Formularios de la administración: Usuarios, segundo factor y configuración de la Sede.

Todos reciben la Clínica de quien administra —de eso se encarga
`FormularioDeLaClinica`— y limitan a sus Sedes lo que se puede elegir: un
`<select>` es una sugerencia, no una frontera. Los de la configuración van un
paso más allá y ni siquiera ofrecen la Sede: llega por la URL de la página que
se está mirando (`FormularioDeLaSede`).
"""

from allauth.mfa.totp.forms import ActivateTOTPForm
from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.tenancy.aislamiento import FormularioDeLaClinica
from apps.tenancy.models import (
    ClinicaDeDerivacion,
    ExcepcionDeAtencion,
    FranjaDeAtencion,
    Sede,
    Usuario,
)


class UsuarioForm(FormularioDeLaClinica):
    """Alta y edición de un Usuario de la Clínica."""

    class Meta:
        model = Usuario
        fields = ["email", "nombre", "apellidos", "rol", "sedes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sedes"].queryset = self.clinica.sedes.all()
        self.fields["sedes"].required = True


class CrearUsuarioForm(UsuarioForm):
    """Alta con contraseña inicial.

    Todavía no hay correo saliente, así que el admin le entrega la contraseña
    al Usuario. Cuando lo haya, esto se sustituye por una invitación.
    """

    contrasena = forms.CharField(
        label=_("Contraseña inicial"), widget=forms.PasswordInput, strip=False
    )

    def clean(self):
        datos = super().clean()
        contrasena = datos.get("contrasena")
        if contrasena:
            # `self.instance` todavía está vacío aquí — Django lo rellena
            # después, en `_post_clean` —, así que la validación se hace contra
            # un Usuario armado a mano; si no, «contraseña igual al correo» pasa.
            futuro = Usuario(email=datos.get("email", ""), nombre=datos.get("nombre", ""))
            try:
                validate_password(contrasena, futuro)
            except ValidationError as invalida:
                self.add_error("contrasena", invalida)
        return datos

    def save(self, commit=True):
        self.instance.set_password(self.cleaned_data["contrasena"])
        return super().save(commit)


class AltaDeSegundoFactorForm(ActivateTOTPForm):
    """El código con el que el Usuario demuestra que su teléfono ya guarda el secreto.

    De `allauth` sale el secreto —lo guarda en la sesión mientras dura el
    alta— y la comprobación del código. Lo que se cambia aquí es el rótulo: el
    de origen habla de «autenticador», que en el mostrador no dice nada.
    """

    code = forms.CharField(
        label=_("Código de la aplicación"),
        widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "inputmode": "numeric"}),
    )


class FormularioDeLaSede(FormularioDeLaClinica):
    """Base de lo que se declara de una Sede concreta.

    La Sede llega por la URL y no como un campo: quien edita el horario está
    mirando la página de esa Sede, y un `<select>` de Sedes solo serviría para
    guardar la franja en la Sede equivocada. La Clínica sale de la Sede, que es
    de donde tiene que salir para que las dos no puedan discrepar.
    """

    def __init__(self, *args, sede, **kwargs):
        super().__init__(*args, clinica=sede.clinic, **kwargs)
        self.sede = sede

    def los_de_la_sede(self):
        """Lo que esta Sede ya tiene declarado de este modelo, menos lo editado."""
        return self.los_demas().filter(sede=self.sede)

    def save(self, commit=True):
        self.instance.sede = self.sede
        return super().save(commit)


class FranjaForm(FormularioDeLaSede):
    """Una franja del Horario de atención: «lunes de 09:00 a 13:00»."""

    class Meta:
        model = FranjaDeAtencion
        fields = ["dia", "desde", "hasta"]

    def clean(self):
        datos = super().clean()
        desde, hasta = datos.get("desde"), datos.get("hasta")
        if desde and hasta and desde >= hasta:
            # La base de datos también lo rechaza; aquí se dice con palabras y
            # sin página de error. Que una franja cruce la medianoche se declara
            # con dos franjas, una en cada día (`horarios.py`).
            self.add_error("hasta", _("La franja tiene que terminar después de empezar."))
        elif desde and hasta and self._se_pisa_con_otra(datos.get("dia"), desde, hasta):
            self.add_error(
                None,
                _("Ya hay una franja de ese día que se pisa con esta. Amplíe la que hay."),
            )
        return datos

    def _se_pisa_con_otra(self, dia, desde, hasta):
        """Si lo declarado se solapa con otra franja del mismo día.

        Dos franjas contiguas —hasta las 13:00 y desde las 13:00— no se pisan:
        la franja no incluye su hora de cierre, y por eso las 13:00 en punto
        caen en una sola (`horarios.py`).
        """
        return (
            self.los_de_la_sede()
            .filter(dia=dia, desde__lt=hasta, hasta__gt=desde)
            .exists()
        )


class ExcepcionForm(FormularioDeLaSede):
    """Lo que la Sede hace una fecha concreta: cerrar, o atender otras horas."""

    class Meta:
        model = ExcepcionDeAtencion
        fields = ["fecha", "motivo", "desde", "hasta"]

    def clean(self):
        datos = super().clean()
        desde, hasta = datos.get("desde"), datos.get("hasta")
        if bool(desde) != bool(hasta):
            # Media excepción no se sabría aplicar: «abre a las 09:00» sin decir
            # hasta cuándo no es ni cerrado ni un horario.
            self.add_error(
                "hasta" if desde else "desde",
                _("Escriba las dos horas, o ninguna para cerrar todo el día."),
            )
        elif desde and hasta and desde >= hasta:
            self.add_error("hasta", _("La franja tiene que terminar después de empezar."))
        return datos


class UrgenciasForm(forms.ModelForm):
    """Si la Sede atiende urgencias, y a qué número se llama entonces.

    Es un `ModelForm` de la Sede a secas y no un `FormularioDeLaClinica`: la
    Sede no es un modelo de dominio con Clínica que poner —ya la tiene—, y aquí
    no se crea nada, se edita lo que la Sede dice de sí misma.
    """

    class Meta:
        model = Sede
        fields = ["atiende_urgencias", "telefono_de_urgencias"]

    def clean(self):
        datos = super().clean()
        if datos.get("telefono_de_urgencias") and not datos.get("atiende_urgencias"):
            self.add_error(
                "telefono_de_urgencias",
                _("Esta Sede no atiende urgencias: borre el número o marque que sí."),
            )
        return datos


class ClinicaDeDerivacionForm(FormularioDeLaClinica):
    """Una clínica de la red a la que derivar cuando la Sede no puede atender."""

    class Meta:
        model = ClinicaDeDerivacion
        fields = ["nombre", "telefono", "direccion"]

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"]
        if self.los_demas().filter(nombre__iexact=nombre).exists():
            raise ValidationError(_("Esa clínica ya está en la lista."))
        return nombre

"""Formularios de la administración de Usuarios.

Ambos formularios reciben la Clínica de quien administra —de eso se encarga
`FormularioDeLaClinica`— y limitan a sus Sedes lo que se puede elegir: un
`<select>` es una sugerencia, no una frontera.
"""

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.tenancy.aislamiento import FormularioDeLaClinica
from apps.tenancy.models import Usuario


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

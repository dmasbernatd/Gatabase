"""Formularios de la administración de Usuarios.

Ambos formularios reciben la Clínica de quien administra y limitan a sus Sedes
lo que se puede elegir: un `<select>` es una sugerencia, no una frontera.
"""

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.tenancy.models import Usuario


class UsuarioForm(forms.ModelForm):
    """Alta y edición de un Usuario de la Clínica."""

    class Meta:
        model = Usuario
        fields = ["email", "nombre", "apellidos", "rol", "sedes"]

    def __init__(self, *args, clinica, **kwargs):
        super().__init__(*args, **kwargs)
        self.clinica = clinica
        self.fields["sedes"].queryset = clinica.sedes.all()
        self.fields["sedes"].required = True

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.clinic = self.clinica
        if commit:
            usuario.save()
            self.save_m2m()
        return usuario


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

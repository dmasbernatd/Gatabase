"""Clínica, Sede y Usuario.

La Clínica es la frontera de aislamiento de todos los datos (ADR-0003): por eso
es el único modelo de este archivo sin clave ajena `clinic`. La Sede es un local
físico suyo, y el Usuario pertenece a una Clínica y a una o varias de sus Sedes.
"""

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Clinica(models.Model):
    """La organización que contrata el sistema."""

    nombre = models.CharField(_("nombre"), max_length=120, unique=True)
    creada = models.DateTimeField(_("creada"), default=timezone.now)

    class Meta:
        verbose_name = _("Clínica")
        verbose_name_plural = _("Clínicas")
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Sede(models.Model):
    """Local físico de una Clínica.

    Las Sedes de una Clínica comparten Tutores y Pacientes, pero no agenda.
    """

    clinic = models.ForeignKey(
        Clinica, on_delete=models.CASCADE, related_name="sedes", verbose_name=_("Clínica")
    )
    nombre = models.CharField(_("nombre"), max_length=120)
    direccion = models.CharField(_("dirección"), max_length=250, blank=True)

    class Meta:
        verbose_name = _("Sede")
        verbose_name_plural = _("Sedes")
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(fields=["clinic", "nombre"], name="sede_unica_en_la_clinica")
        ]

    def __str__(self):
        return self.nombre


class Rol(models.TextChoices):
    """Lo que un Usuario puede hacer dentro de su Clínica."""

    VETERINARIO = "veterinario", _("veterinario")
    RECEPCION = "recepcion", _("recepción")
    ADMIN = "admin", _("admin")


class GestorDeUsuarios(BaseUserManager):
    """Crea Usuarios con la contraseña ya cifrada.

    No hay `create_superuser`: no existe `django.contrib.admin` y el alta de una
    Clínica con su primer admin la hace el comando `crear_clinica`.
    """

    def create_user(self, email, clinic, contrasena=None, **campos):
        if not email:
            raise ValueError(_("Un Usuario necesita un correo para entrar."))
        usuario = self.model(email=self.normalize_email(email), clinic=clinic, **campos)
        usuario.set_password(contrasena)
        usuario.save(using=self._db)
        return usuario


class Usuario(AbstractBaseUser):
    """Persona que accede a la aplicación en el contexto de una Clínica.

    Sin `PermissionsMixin`: los permisos de Gatabase son el `rol` y las Sedes,
    no los grupos de Django, y no hay sitio de administración que los use.
    """

    clinic = models.ForeignKey(
        Clinica, on_delete=models.CASCADE, related_name="usuarios", verbose_name=_("Clínica")
    )
    # El correo identifica al Usuario en todo el sistema, no solo en su Clínica:
    # es con lo que entra. Quien trabaje en dos Clínicas necesita dos correos.
    email = models.EmailField(_("correo"), unique=True)
    nombre = models.CharField(_("nombre"), max_length=120)
    apellidos = models.CharField(_("apellidos"), max_length=120, blank=True)
    rol = models.CharField(_("rol"), max_length=20, choices=Rol.choices, default=Rol.RECEPCION)
    sedes = models.ManyToManyField(
        Sede, related_name="usuarios", verbose_name=_("Sedes"), blank=True
    )
    is_active = models.BooleanField(_("activo"), default=True)
    date_joined = models.DateTimeField(_("alta"), default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = GestorDeUsuarios()

    class Meta:
        verbose_name = _("Usuario")
        verbose_name_plural = _("Usuarios")
        ordering = ["apellidos", "nombre"]

    def __str__(self):
        return f"{self.nombre} {self.apellidos}".strip()

    @property
    def es_admin(self):
        return self.rol == Rol.ADMIN

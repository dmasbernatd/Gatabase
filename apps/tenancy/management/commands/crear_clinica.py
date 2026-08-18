"""Alta de una Clínica con su primera Sede y su primer admin.

Es el único camino para que una Clínica empiece a existir: no hay registro
abierto ni sitio de administración. A partir de aquí, los demás Usuarios los
crea el admin desde el panel.
"""

from getpass import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.tenancy.models import Clinica, Rol, Sede, Usuario


class Command(BaseCommand):
    help = _("Da de alta una Clínica con su primera Sede y su primer admin.")

    def add_arguments(self, parser):
        parser.add_argument("--clinica", required=True, help=_("Nombre de la Clínica"))
        parser.add_argument("--sede", required=True, help=_("Nombre de la primera Sede"))
        parser.add_argument("--direccion", default="", help=_("Dirección de la Sede"))
        parser.add_argument("--email", required=True, help=_("Correo del primer admin"))
        parser.add_argument("--nombre", required=True, help=_("Nombre del primer admin"))
        parser.add_argument("--apellidos", default="", help=_("Apellidos del primer admin"))
        parser.add_argument(
            "--contrasena",
            help=_("Contraseña del primer admin; si falta, se pide por teclado"),
        )

    @transaction.atomic
    def handle(self, *args, **opciones):
        nombre_de_clinica = opciones["clinica"]
        email = opciones["email"]

        if Clinica.objects.filter(nombre=nombre_de_clinica).exists():
            raise CommandError(_("La Clínica «%s» ya está dada de alta.") % nombre_de_clinica)
        if Usuario.objects.filter(email=email).exists():
            raise CommandError(_("Ya hay un Usuario con el correo %s.") % email)

        contrasena = opciones["contrasena"] or getpass(_("Contraseña del admin: "))
        try:
            validate_password(contrasena, Usuario(email=email, nombre=opciones["nombre"]))
        except ValidationError as invalida:
            raise CommandError("\n".join(invalida.messages)) from invalida

        clinica = Clinica.objects.create(nombre=nombre_de_clinica)
        sede = Sede.objects.create(
            clinic=clinica, nombre=opciones["sede"], direccion=opciones["direccion"]
        )
        admin = Usuario.objects.create_user(
            email=email,
            clinic=clinica,
            contrasena=contrasena,
            nombre=opciones["nombre"],
            apellidos=opciones["apellidos"],
            rol=Rol.ADMIN,
        )
        admin.sedes.add(sede)

        self.stdout.write(
            self.style.SUCCESS(
                _("Clínica «%(clinica)s» dada de alta con la Sede «%(sede)s» y el admin %(email)s.")
                % {"clinica": clinica.nombre, "sede": sede.nombre, "email": admin.email}
            )
        )

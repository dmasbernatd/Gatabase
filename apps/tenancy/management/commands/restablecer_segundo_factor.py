"""Retira el segundo factor de un Usuario que perdió el teléfono.

El admin no puede entrar sin segundo factor, y el suyo vive en un teléfono que
se puede perder, romper o formatear. Sin códigos de recuperación —habría que
entregarlos por correo, y todavía no hay correo saliente— el rescate es este
comando, que se ejecuta en el servidor: quien tiene acceso al servidor ya podría
hacer cualquier cosa, así que no abre ninguna puerta nueva.

Solo lo retira. Darlo de alta otra vez lo hace el propio Usuario la próxima vez
que entre, con su contraseña y su teléfono nuevo.
"""

from allauth.mfa.models import Authenticator
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _

from apps.tenancy.models import Usuario


class Command(BaseCommand):
    help = _("Retira el segundo factor de un Usuario para que lo vuelva a dar de alta al entrar.")

    def add_arguments(self, parser):
        parser.add_argument("email", help=_("Correo del Usuario"))

    def handle(self, *args, **opciones):
        email = opciones["email"]
        usuario = Usuario.objects.filter(email__iexact=email).first()
        if usuario is None:
            raise CommandError(_("No hay ningún Usuario con el correo «%s».") % email)

        retirados, _detalle = Authenticator.objects.filter(user=usuario).delete()
        if not retirados:
            self.stdout.write(_("«%s» no tenía segundo factor configurado.") % email)
            return
        self.stdout.write(
            _("Segundo factor retirado. «%s» lo dará de alta la próxima vez que entre.") % email
        )

"""Reabre una Clínica que se cerró, para quien la cerró por error.

Cerrar desde la aplicación deja fuera a todos los Usuarios de la Clínica, el
admin que lo pidió incluido, así que no queda nadie que pueda deshacerlo desde
dentro: la puerta que queda es la consola, como con `restablecer_segundo_factor`.

Reabrir es solo vaciar la fecha. Cerrar no desactivó a nadie, así que vuelve a
entrar exactamente quien entraba antes, y quien el admin había desactivado sigue
fuera. El comando enumera a quién le devuelve el acceso, para que quien lo
ejecuta lo vea antes de que esa gente se entere por su cuenta.

No queda en el Registro de acceso: el Registro anota lo que hace un Usuario, y
aquí no hay ninguno. La fecha del cierre se vacía, pero la anotación del cierre
sigue diciendo quién cerró y cuándo.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _

from apps.tenancy.models import Clinica


class Command(BaseCommand):
    help = _("Reabre una Clínica cerrada: vuelve a entrar quien entraba antes de cerrarla.")

    def add_arguments(self, parser):
        parser.add_argument("clinica", help=_("Nombre de la Clínica"))

    def handle(self, *args, **opciones):
        nombre = opciones["clinica"]
        clinica = Clinica.objects.filter(nombre=nombre).first()
        if clinica is None:
            raise CommandError(_("No hay ninguna Clínica que se llame «%s».") % nombre)
        # Si no estaba cerrada, lo más probable es que se quisiera reabrir otra y
        # se escribiera mal el nombre: decirlo antes que no hacer nada en silencio.
        if not clinica.esta_cerrada:
            raise CommandError(_("La Clínica «%s» no está cerrada.") % nombre)

        clinica.cerrada = None
        clinica.save(update_fields=["cerrada"])

        self.stdout.write(self.style.SUCCESS(_("Clínica «%s» reabierta.") % nombre))
        vuelven = clinica.usuarios.filter(is_active=True).order_by("email")
        if not vuelven:
            self.stdout.write(_("No tiene ningún Usuario activo: nadie puede entrar todavía."))
            return
        self.stdout.write(_("Vuelven a poder entrar:"))
        for usuario in vuelven:
            self.stdout.write(f"  {usuario.email} ({usuario.get_rol_display()})")

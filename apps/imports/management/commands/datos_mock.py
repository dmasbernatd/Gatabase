"""Llena la base de datos de demostración con dos Clínicas chilenas enteras.

El comando es la puerta; quién inventa los datos y por qué son como son lo
cuenta `apps/imports/mock.py`. Aquí solo viven las tres cosas que son de la línea
de órdenes: a quién se le niega, cuánto se pide y qué se le enseña al terminar.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import gettext as _

from apps.imports import mock


class Command(BaseCommand):
    help = _("Llena la base con dos Clínicas de demostración y datos verosímiles.")

    def add_arguments(self, parser):
        parser.add_argument(
            "--tutores",
            type=int,
            default=mock.TUTORES_POR_DEFECTO,
            help=_("Cuántos Tutores tiene la Clínica grande (por defecto %(cuantos)s)")
            % {"cuantos": mock.TUTORES_POR_DEFECTO},
        )
        parser.add_argument(
            "--semilla",
            type=int,
            default=mock.SEMILLA,
            help=_("Semilla del azar; la misma semilla da la misma clínica"),
        )
        parser.add_argument(
            "--aunque-no-sea-desarrollo",
            action="store_true",
            help=_("Puebla con DJANGO_DEBUG apagado: el despliegue de la demostración"),
        )

    @transaction.atomic
    def handle(self, *args, **opciones):
        # Antes que nada y dentro de la transacción: lo que se comprueba es que
        # esta base no tenga clientes, y a partir de aquí se borra y se escribe.
        motivo = mock.por_que_no_se_puede_poblar(opciones["aunque_no_sea_desarrollo"])
        if motivo:
            raise CommandError(motivo)

        if opciones["tutores"] < mock.MINIMO_DE_TUTORES:
            raise CommandError(
                _("Con menos de %(minimo)s Tutores no caben los casos límite.")
                % {"minimo": mock.MINIMO_DE_TUTORES}
            )

        for plantilla in mock.CLINICAS:
            resumen = mock.poblar(plantilla, opciones["tutores"], opciones["semilla"])
            if opciones["verbosity"]:
                self._contar(resumen)

        if not opciones["verbosity"]:
            return
        self.stdout.write(
            self.style.SUCCESS(
                _("Listo. Todos los Usuarios entran con la contraseña «%(clave)s».")
                % {"clave": mock.CONTRASENA}
            )
        )

    def _contar(self, resumen):
        """Qué quedó escrito y dónde mirar lo que rompe pantallas."""
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(str(resumen.clinica)))
        self.stdout.write(
            _("  Sede %(sede)s · %(tutores)s Tutores · %(pacientes)s Pacientes · "
              "%(vinculos)s Vínculos · %(consentimientos)s Consentimientos")
            % {
                "sede": resumen.sede.nombre,
                "tutores": resumen.tutores,
                "pacientes": resumen.pacientes,
                "vinculos": resumen.vinculos,
                "consentimientos": resumen.consentimientos,
            }
        )
        for usuario in resumen.usuarios:
            self.stdout.write(f"  {usuario.get_rol_display():<12} {usuario.email}")
        self.stdout.write(_("  Casos límite:"))
        for que, quien in resumen.casos_limite:
            self.stdout.write(f"    {que}: {quien}")

"""Borra las planillas subidas que ya no puede confirmar nadie.

Es el mismo barrido que corre al subir una planilla (`apps/imports/almacen.py`),
puesto donde un cron lo alcance: sin él, la última planilla que suba una clínica
se queda en el disco para siempre, con los datos de cientos de Tutores y fuera
del alcance del derecho de supresión.

No toca la planilla que alguien está mirando: se mide por inactividad, con el
mismo plazo que la sesión de la que cuelga.
"""

from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from apps.imports.almacen import barrer_lo_que_ya_no_alcanza_nadie


class Command(BaseCommand):
    help = _("Borra las planillas subidas cuya sesión ya caducó.")

    def handle(self, *args, **opciones):
        barridas = barrer_lo_que_ya_no_alcanza_nadie()
        self.stdout.write(
            ngettext(
                "Se borró %(n)d planilla que ya no podía confirmar nadie.",
                "Se borraron %(n)d planillas que ya no podía confirmar nadie.",
                barridas,
            )
            % {"n": barridas}
        )

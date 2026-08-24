"""El Paciente cambia de manos: quién responde por él a partir de hoy.

Es una sola operación y no dos, y esa es toda la decisión de este módulo. Cerrar
el Vínculo del Tutor de antes y abrir el del de ahora por separado deja, entre
una cosa y otra, un animal activo del que no responde nadie: una ficha que no
dice a quién llamar. Aquí las dos mitades van juntas y en la misma transacción,
así que o cambia de manos o no cambia nada.

La información del animal **no** se toca: sigue siendo el mismo Paciente con la
misma Historia clínica y el mismo microchip (ADR-0001). Lo único que cambia es
quién responde por él, que es un hecho del Tutor y vive en el Vínculo.

Vive en `tutors` y no en `patients` porque escribe Vínculos, y porque la
dependencia entre las dos apps va en este sentido (`CLAUDE.md`). Es un módulo
propio y no un método del Tutor porque la operación no es de ninguno de los dos
Tutores: es del Paciente que pasa de uno a otro.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def traspasar(paciente, a, fecha=None):
    """Deja al Paciente en manos de ese Tutor y cierra el del anterior.

    Devuelve el Vínculo abierto del Tutor nuevo. La fecha es la del cambio de
    manos —hasta cuándo respondió el anterior—; sin ella, la de hoy.

    Si el Tutor nuevo ya estaba vinculado —una pareja que se separa y uno de los
    dos se queda con el animal— no se abre otro Vínculo: se le pasa el cargo al
    que ya tenía, que es lo que pasó de verdad. Lo único que se rechaza es
    traspasarle el animal a quien ya responde por él, que no es un cambio de
    manos sino una pantalla enviada dos veces.
    """
    anterior = paciente.vinculo_responsable
    if anterior and anterior.tutor_id == a.pk:
        raise ValidationError(
            _("%(tutor)s ya responde por %(paciente)s.")
            % {"tutor": a, "paciente": paciente.nombre},
            code="ya_responde",
        )
    fecha = fecha or timezone.localdate()
    with transaction.atomic():
        # Primero el nuevo, que suelta al anterior del cargo al marcarse
        # (`hacer_responsable`): así no hay ningún instante sin responsable, y
        # el cierre encuentra al anterior ya sin el cargo.
        vinculo = a.se_hace_cargo_de(paciente, responsable=True)
        if anterior:
            anterior.refresh_from_db()
            anterior.cerrar(fecha)
    return vinculo

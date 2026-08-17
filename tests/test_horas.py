"""Las horas se guardan en UTC y se presentan en America/Santiago.

El ida y vuelta pasa por Postgres de verdad: lo que se comprueba es que el
instante sobrevive al almacenamiento y que la presentación lo traduce a la
zona horaria de la clínica, no que Django sepa sumar horas.
"""

import datetime as dt
import zoneinfo

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.utils import timezone

from tests.factories import UsuarioFactory

SANTIAGO = zoneinfo.ZoneInfo("America/Santiago")

# 15:30 UTC del 20 de junio: invierno en Chile, offset -04:00 → 11:30 local.
INSTANTE_INVIERNO = dt.datetime(2026, 6, 20, 15, 30, tzinfo=dt.timezone.utc)
# 15:30 UTC del 20 de enero: verano en Chile, offset -03:00 → 12:30 local.
INSTANTE_VERANO = dt.datetime(2026, 1, 20, 15, 30, tzinfo=dt.timezone.utc)


def test_la_configuracion_usa_utc_y_presenta_en_santiago():
    assert settings.USE_TZ is True
    assert settings.TIME_ZONE == "America/Santiago"


@pytest.mark.django_db
@pytest.mark.parametrize("instante", [INSTANTE_INVIERNO, INSTANTE_VERANO])
def test_una_fecha_guardada_y_recuperada_conserva_el_instante(instante):
    usuario = UsuarioFactory(date_joined=instante)

    recuperado = get_user_model().objects.get(pk=usuario.pk)

    assert recuperado.date_joined == instante
    assert timezone.is_aware(recuperado.date_joined)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("instante", "hora_local"),
    [(INSTANTE_INVIERNO, "11:30"), (INSTANTE_VERANO, "12:30")],
)
def test_una_fecha_recuperada_se_presenta_en_hora_de_santiago(instante, hora_local):
    usuario = UsuarioFactory(date_joined=instante)
    recuperado = get_user_model().objects.get(pk=usuario.pk)

    presentada = Template("{{ momento|date:'H:i' }}").render(
        Context({"momento": recuperado.date_joined})
    )

    assert presentada == hora_local
    assert recuperado.date_joined.astimezone(SANTIAGO).strftime("%H:%M") == hora_local

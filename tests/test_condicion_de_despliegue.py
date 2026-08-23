"""La condición de despliegue de ADR-0004 la comprueba alguien (`audit.E001`).

La inalterabilidad del Registro de acceso descansa en algo que la migración no
puede imponerse a sí misma: el rol con el que la aplicación se conecta. Aquí se
comprueba que ese descuido lo delata un `check` de Django, y que el `check` no
molesta donde no toca — con `DEBUG` encendido y dentro de la propia batería, donde
el rol es superusuario a propósito y la base se tira al terminar.

El rol de desarrollo *es* superusuario, así que la conexión de estos tests sirve
de espécimen: preguntándole directamente a `fallos_de_la_condicion_de_despliegue`
se ve el error que saldría en un despliegue mal montado.
"""

import pytest
from django.core.management import call_command
from django.db import DatabaseError, connection

from apps.audit.comprobaciones import (
    CODIGO_ROL_SUPERUSUARIO,
    CODIGO_SIN_COMPROBAR,
    en_la_bateria_de_tests,
    fallos_de_la_condicion_de_despliegue,
    hay_que_comprobar,
)

pytestmark = pytest.mark.django_db


def test_un_rol_superusuario_delata_la_condicion_de_despliegue():
    """El rol de desarrollo se salta los permisos de la tabla, y eso se dice."""
    fallos = fallos_de_la_condicion_de_despliegue(connection)

    assert [fallo.id for fallo in fallos] == [CODIGO_ROL_SUPERUSUARIO]


def test_el_fallo_explica_como_se_arregla():
    (fallo,) = fallos_de_la_condicion_de_despliegue(connection)

    assert "superusuario" in fallo.msg
    assert "REVOKE" in fallo.hint


def test_no_se_comprueba_dentro_de_la_bateria_de_tests(settings):
    """Aunque `DEBUG` esté apagado, que es como corren los tests."""
    settings.DEBUG = False

    assert en_la_bateria_de_tests()
    assert not hay_que_comprobar(connection)


def test_no_se_comprueba_en_desarrollo(settings):
    settings.DEBUG = True

    assert not hay_que_comprobar(connection)


def test_la_bateria_de_checks_de_django_sigue_pasando(settings):
    """La comprobación no puede romper `manage.py check` en desarrollo ni en la
    propia batería de tests: si lo hiciera, se acabaría desactivando."""
    settings.DEBUG = False

    call_command("check")


def test_una_base_sin_migrar_no_tiene_nada_que_reprochar():
    """La tabla aún no existe: el `REVOKE` lo hará la migración al pasar. El
    `drop` vive dentro de la transacción del test y se deshace con ella."""
    with connection.cursor() as cursor:
        cursor.execute("drop table audit_registrodeacceso cascade")

    assert fallos_de_la_condicion_de_despliegue(connection) == []


def test_si_la_base_no_responde_se_avisa_pero_no_revienta():
    """Un `check` que revienta deja sin arrancar por algo que no es el fallo."""

    class ConexionCaida:
        vendor = "postgresql"

        def cursor(self):
            raise DatabaseError("no such host")

    fallos = fallos_de_la_condicion_de_despliegue(ConexionCaida())

    assert [fallo.id for fallo in fallos] == [CODIGO_SIN_COMPROBAR]

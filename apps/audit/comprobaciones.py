"""Comprobación de despliegue: el Registro de acceso es inalterable de verdad.

La migración `audit/0002` pone dos cierres — los permisos de la tabla y un
disparador —, pero el primero descansa en una condición que la migración no
puede imponerse a sí misma: que la aplicación se conecte con un rol que **no**
sea superusuario de Postgres, y que, si el despliegue migra con un rol distinto
del de la aplicación, a ese otro rol se le hayan retirado los mismos `UPDATE`,
`DELETE` y `TRUNCATE` — un `REVOKE` concede por nombre y solo alcanza al rol
que ejecuta la migración.

Hasta aquí, esa condición solo estaba escrita en el README y en la migración.
En una máquina de desarrollo el disparador tapa el agujero; en un despliegue
donde el rol es superusuario, la garantía que se le enseña a la autoridad es de
papel. Esto la convierte en algo que se comprueba solo: un `check` de Django que
le pregunta a la base de datos, con la conexión de la aplicación, si ese rol
podría modificar la tabla. La pregunta se hace con `has_table_privilege`, que
responde por lo que el rol puede de verdad — a un superusuario le dice que sí a
todo, que es justamente el caso que hay que descubrir.

No se comprueba con `DEBUG` encendido ni dentro de la batería de tests: ahí el
rol es el de la imagen de Postgres, superusuario, y la base se tira al terminar.
Lo que se protege es el despliegue.
"""

from django.conf import settings
from django.core import mail
from django.core.checks import Error, Warning, register
from django.db import DatabaseError, connections

from apps.audit.models import RegistroDeAcceso

CODIGO_ROL_SUPERUSUARIO = "audit.E001"
CODIGO_PERMISOS_NO_RETIRADOS = "audit.E002"
CODIGO_SIN_COMPROBAR = "audit.W001"

# Los tres que la migración retira: los que dejarían de ser cierta la promesa de
# que una anotación nace y no cambia nunca más.
PERMISOS_QUE_SOBRAN = ("UPDATE", "DELETE", "TRUNCATE")

TABLA = RegistroDeAcceso._meta.db_table

CONDICION_DE_DESPLIEGUE = (
    "Conecta la aplicación con un rol que no sea superusuario de Postgres y, si "
    "las migraciones se aplican con otro rol, retírale a ese otro los mismos "
    f"permisos: REVOKE {', '.join(PERMISOS_QUE_SOBRAN)} ON {TABLA} FROM <rol>."
)


def en_la_bateria_de_tests():
    """Estamos dentro de `pytest`, no de un despliegue.

    Hace falta preguntarlo porque durante los tests `DEBUG` está apagado y la
    base la sirve la imagen de Postgres, cuyo rol es superusuario: sin esto, la
    comprobación saltaría en cada `manage.py check` de la batería y acabaría
    desactivada, que es como no tenerla.

    Se pregunta por el buzón de correo de test — `setup_test_environment()` lo
    pone y fuera de los tests no existe — y no por el nombre de la base: Django
    reescribe ese nombre al crearla, así que ya no se distingue del configurado.
    Si algún día dejara de valer, la comprobación fallaría en la batería, a la
    vista; nunca al revés.
    """
    return hasattr(mail, "outbox")


def hay_que_comprobar(conexion):
    if settings.DEBUG or conexion.vendor != "postgresql":
        return False
    return not en_la_bateria_de_tests()


def _puede_modificar_el_registro(conexion):
    """Qué le deja hacer Postgres al rol de esta conexión sobre la tabla.

    Devuelve `(es_superusuario, permisos_que_tiene)`, o `None` si la tabla aún
    no existe: una base sin migrar no tiene nada que proteger todavía, y la
    propia migración hará el `REVOKE` al pasar.
    """
    with conexion.cursor() as cursor:
        cursor.execute(
            "select to_regclass(%s) is not null, "
            "(select rolsuper from pg_roles where rolname = current_user)",
            [TABLA],
        )
        existe_la_tabla, es_superusuario = cursor.fetchone()
        if not existe_la_tabla:
            return None

        # Una consulta aparte: `has_table_privilege` revienta si la tabla no
        # existe, y en Postgres las dos ramas de un `and` se evalúan igual.
        cursor.execute(
            "select " + ", ".join(f"has_table_privilege(%s, '{p}')" for p in PERMISOS_QUE_SOBRAN),
            [TABLA] * len(PERMISOS_QUE_SOBRAN),
        )
        tiene = [p for p, concedido in zip(PERMISOS_QUE_SOBRAN, cursor.fetchone()) if concedido]

    return bool(es_superusuario), tiene


def fallos_de_la_condicion_de_despliegue(conexion):
    """Los `Error` de ADR-0004 que la base de datos delata en esta conexión."""
    try:
        sondeo = _puede_modificar_el_registro(conexion)
    except DatabaseError as error:
        return [
            Warning(
                "No se pudo comprobar si el Registro de acceso es inalterable: "
                f"{error}",
                hint=CONDICION_DE_DESPLIEGUE,
                id=CODIGO_SIN_COMPROBAR,
            )
        ]

    if sondeo is None:
        return []

    es_superusuario, permisos = sondeo
    if es_superusuario:
        return [
            Error(
                "La aplicación se conecta a Postgres con un rol superusuario, que "
                "se salta los permisos de la tabla del Registro de acceso: la "
                "inalterabilidad que exige ADR-0004 queda en manos del disparador.",
                hint=CONDICION_DE_DESPLIEGUE,
                id=CODIGO_ROL_SUPERUSUARIO,
            )
        ]
    if permisos:
        return [
            Error(
                f"El rol de la aplicación conserva {', '.join(permisos)} sobre "
                f"{TABLA}. Suele pasar cuando las migraciones se aplicaron con un "
                "rol distinto: el REVOKE de `audit/0002` solo alcanzó a aquel.",
                hint=CONDICION_DE_DESPLIEGUE,
                id=CODIGO_PERMISOS_NO_RETIRADOS,
            )
        ]
    return []


@register()
def el_registro_de_acceso_no_lo_puede_modificar_la_aplicacion(app_configs, **kwargs):
    conexion = connections[RegistroDeAcceso.objects.db]
    if not hay_que_comprobar(conexion):
        return []
    return fallos_de_la_condicion_de_despliegue(conexion)

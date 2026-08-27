"""Qué significa cerrar una Clínica, y por qué no significa borrarla.

Una Clínica que se va **se exporta y se cierra**. Borrarla no es una opción que
esté escondida ni pendiente: el Registro de acceso no admite `DELETE`
(ADR-0004, migración `audit/0002`), así que el borrado en cascada tropieza con el
disparador y se lleva por delante la transacción entera. Eso es lo que tiene que
pasar — la evidencia de quién vio los datos de quién sobrevive a que la clínica
deje de ser cliente, que es justamente para lo que sirve —, pero hasta ahora la
única manera de enterarse era pulsar algo y recibir un `IntegrityError`. Este
módulo existe para que el sistema ofrezca lo que sí se puede hacer.

**Cerrar es dejarla sin acceso.** Se anota cuándo se cerró y se desactivan todos
sus Usuarios, incluido el admin que lo pide. A partir de ahí nadie de esa Clínica
entra: `allauth` deja fuera al Usuario inactivo en el login, y a quien tuviera
sesión abierta lo desconecta en su siguiente petición, porque el backend de
autenticación no devuelve Usuarios inactivos. Los datos se quedan donde están,
intactos y sin nadie que los mire.

**Es un gesto terminal, y se pide como tal.** No hay pantalla que reabra una
Clínica: para volver a entrar hay que reactivar a un Usuario en la base de datos,
que es trabajo de consola y con alguien delante. Por eso la vista pide escribir
el nombre de la Clínica antes de hacerlo, y por eso la página ofrece antes la
exportación: cerrar sin haberse llevado los datos es la única manera de que esto
duela.

**Queda en el Registro de acceso**, como una modificación sobre la Clínica: es el
último gesto de esa Clínica y el que explica por qué después no hay ninguno más.
"""

from django.db import transaction
from django.utils import timezone

from apps.audit.models import Accion
from apps.audit.registro import anotar
from apps.tenancy.models import Usuario


def cerrar(clinica, usuario):
    """Cierra la Clínica: consta desde cuándo, y su gente deja de entrar.

    Todo en la misma transacción: una Clínica marcada como cerrada cuya gente
    siguiera entrando, o una Clínica sin acceso que no constara cerrada, serían
    dos maneras distintas de mentir sobre lo mismo.

    Se puede llamar sobre una Clínica ya cerrada y no pasa nada — vuelve a
    desactivar lo que ya estaba desactivado —, pero no se pisa la fecha: cuándo
    se cerró se dice una vez.
    """
    with transaction.atomic():
        if not clinica.esta_cerrada:
            clinica.cerrada = timezone.now()
            clinica.save(update_fields=["cerrada"])
        # `update` y no un bucle con `save`: son todos los Usuarios de la Clínica
        # de un golpe, y ninguno de ellos tiene nada que hacer al guardarse.
        Usuario.objects.filter(clinic=clinica, is_active=True).update(is_active=False)
        anotar(usuario, Accion.MODIFICACION, clinica)

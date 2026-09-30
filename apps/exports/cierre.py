"""Qué significa cerrar una Clínica, y por qué no significa borrarla.

Una Clínica que se va **se exporta y se cierra**. Borrarla no es una opción que
esté escondida ni pendiente: el Registro de acceso no admite `DELETE`
(ADR-0004, migración `audit/0002`), así que el borrado en cascada tropieza con el
disparador y se lleva por delante la transacción entera. Eso es lo que tiene que
pasar — la evidencia de quién vio los datos de quién sobrevive a que la clínica
deje de ser cliente, que es justamente para lo que sirve —, pero hasta ahora la
única manera de enterarse era pulsar algo y recibir un `IntegrityError`. Este
módulo existe para que el sistema ofrezca lo que sí se puede hacer.

**Cerrar es dejarla sin acceso.** Se anota cuándo se cerró, y esa fecha es la
puerta: el backend de autenticación (`apps/tenancy/autenticacion.py`) no deja
entrar a ningún Usuario de una Clínica cerrada, ni en el login ni a quien
tuviera sesión abierta, que sale en su siguiente petición. Los Usuarios no se
tocan: quien estaba activo sigue activo y quien se había desactivado sigue
desactivado, y eso es lo que permite reabrir sin adivinar. Los datos se quedan
donde están, intactos y sin nadie que los mire.

**Es un gesto terminal desde la aplicación, y se pide como tal.** No hay
pantalla que reabra una Clínica —quien la cerró ya no puede entrar a pedirlo—:
se reabre con `manage.py reabrir_clinica`, en el servidor y con alguien delante.
Por eso la vista pide escribir el nombre de la Clínica antes de hacerlo, y por
eso la página ofrece antes la exportación: cerrar sin haberse llevado los datos
es la única manera de que esto duela.

**Queda en el Registro de acceso**, como una modificación sobre la Clínica: es el
último gesto de esa Clínica y el que explica por qué después no hay ninguno más.
"""

from django.db import transaction
from django.utils import timezone

from apps.audit.models import Accion
from apps.audit.registro import anotar


def cerrar(clinica, usuario):
    """Cierra la Clínica: consta desde cuándo, y con eso su gente deja de entrar.

    Se puede llamar sobre una Clínica ya cerrada y no pasa nada, pero no se pisa
    la fecha: cuándo se cerró se dice una vez.
    """
    with transaction.atomic():
        if not clinica.esta_cerrada:
            clinica.cerrada = timezone.now()
            clinica.save(update_fields=["cerrada"])
        anotar(usuario, Accion.MODIFICACION, clinica)

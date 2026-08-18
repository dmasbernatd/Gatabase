"""Sede actual del Usuario durante su sesión.

Un Usuario puede pertenecer a varias Sedes de su Clínica, pero trabaja en una
sola cada vez: la agenda y las bandejas son de la Sede, no de la Clínica. Cuál
es esa Sede vive en la sesión, no en el Usuario, para que la misma cuenta pueda
estar abierta en el mostrador de una Sede y en el box de otra.
"""

CLAVE_DE_SESION = "sede_actual"


def sede_actual(request):
    """La Sede en la que trabaja ahora el Usuario, o `None` si no tiene ninguna.

    Si la Sede guardada en la sesión ya no le corresponde — se la quitó el
    admin —, devuelve la primera que le quede en lugar de dejarlo sin Sede.
    """
    elegida = request.session.get(CLAVE_DE_SESION)
    sedes = list(request.user.sedes.all())
    for sede in sedes:
        if sede.pk == elegida:
            return sede
    return sedes[0] if sedes else None


def fijar_sede(request, sede):
    request.session[CLAVE_DE_SESION] = sede.pk

"""Contexto de plantilla: en qué Clínica y en qué Sede está trabajando el Usuario.

Toda página interna lo muestra, así que no se pasa vista a vista.
"""

from apps.tenancy.sedes import sede_actual


def sesion_de_clinica(request):
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.is_authenticated:
        return {}
    return {
        "clinica": usuario.clinic,
        "sede_actual": sede_actual(request),
        "sedes_del_usuario": usuario.sedes.all(),
    }

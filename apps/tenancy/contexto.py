"""Contexto de plantilla: quién está trabajando, en qué Clínica, en qué Sede y
por cuánto tiempo más.

Toda página interna lo muestra, así que no se pasa vista a vista. Quién está
activo es una de las razones de ser de este ticket: una Consulta firmada con el
nombre del veterinario equivocado tiene valor legal.
"""

from apps.tenancy.sedes import sede_actual
from apps.tenancy.sesion import segundos_de_aviso, segundos_de_sesion


def sesion_de_clinica(request):
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.is_authenticated:
        return {}
    return {
        "clinica": usuario.clinic,
        "sede_actual": sede_actual(request),
        "sedes_del_usuario": usuario.sedes.all(),
        "segundos_de_sesion": segundos_de_sesion(),
        "segundos_de_aviso": segundos_de_aviso(),
    }

"""Quién puede entrar en una vista.

Los permisos de Gatabase son el `rol` del Usuario y sus Sedes, no los grupos de
Django. Viven aquí, y no en `views.py`, porque también los usan otras apps.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def solo_admin(vista):
    """Reserva una vista al rol admin. Sin sesión se va al login, no al 403."""

    @wraps(vista)
    def comprobar_el_rol(request, *args, **kwargs):
        if not request.user.es_admin:
            raise PermissionDenied
        return vista(request, *args, **kwargs)

    return login_required(comprobar_el_rol)


def solo_veterinario(vista):
    """Reserva una vista al rol veterinario. Sin sesión se va al login, no al 403.

    La Historia clínica la escribe quien atiende, y solo él: una Consulta es un
    documento clínico firmado por un veterinario (ADR-0002), y recepción no
    puede figurar como su autor ni corrigiendo una coma. Leerla es otra cosa, y
    no pasa por aquí — recepción le imprime al Tutor el resumen de lo que se le
    hizo al animal.
    """

    @wraps(vista)
    def comprobar_el_rol(request, *args, **kwargs):
        if not request.user.es_veterinario:
            raise PermissionDenied
        return vista(request, *args, **kwargs)

    return login_required(comprobar_el_rol)

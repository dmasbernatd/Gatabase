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

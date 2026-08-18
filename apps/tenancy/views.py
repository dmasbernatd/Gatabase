"""Panel de la Clínica y administración de Usuarios.

Todo lo que se lee y se escribe aquí se filtra por la Clínica del Usuario que
pide la página. Pedir algo de otra Clínica es un 404, nunca un 403 con
contenido: la existencia del objeto ya es información (ADR-0003).
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.tenancy.forms import CrearUsuarioForm, UsuarioForm
from apps.tenancy.models import Sede, Usuario
from apps.tenancy.permisos import solo_admin
from apps.tenancy.sedes import fijar_sede


def _usuarios_de_la_clinica(request):
    return Usuario.objects.filter(clinic=request.user.clinic)


@login_required
def inicio(request):
    """Lo primero que ve el Usuario: dónde está trabajando."""
    return render(request, "tenancy/inicio.html")


@login_required
@require_POST
def cambiar_sede(request):
    sede = get_object_or_404(Sede, pk=request.POST.get("sede"), usuarios=request.user)
    fijar_sede(request, sede)
    return redirect("tenancy:inicio")


@solo_admin
def usuarios(request):
    return render(request, "tenancy/usuarios.html", {"usuarios": _usuarios_de_la_clinica(request)})


@solo_admin
def crear_usuario(request):
    formulario = CrearUsuarioForm(request.POST or None, clinica=request.user.clinic)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        return redirect("tenancy:usuarios")
    return render(
        request,
        "tenancy/formulario_de_usuario.html",
        {"formulario": formulario, "titulo": _("Crear Usuario")},
    )


@solo_admin
def editar_usuario(request, pk):
    usuario = get_object_or_404(_usuarios_de_la_clinica(request), pk=pk)
    formulario = UsuarioForm(request.POST or None, instance=usuario, clinica=request.user.clinic)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        return redirect("tenancy:usuarios")
    return render(
        request,
        "tenancy/formulario_de_usuario.html",
        {"formulario": formulario, "titulo": _("Editar Usuario")},
    )


@solo_admin
@require_POST
def desactivar_usuario(request, pk):
    # Un admin que se desactiva a sí mismo deja a la Clínica sin quien
    # administre: solo el alta por comando podría rescatarla.
    usuario = get_object_or_404(_usuarios_de_la_clinica(request).exclude(pk=request.user.pk), pk=pk)
    usuario.is_active = False
    usuario.save(update_fields=["is_active"])
    return redirect("tenancy:usuarios")

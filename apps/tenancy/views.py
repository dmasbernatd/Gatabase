"""Panel de la Clínica y administración de Usuarios.

Todo lo que se lee y se escribe aquí se filtra por la Clínica del Usuario que
pide la página. Pedir algo de otra Clínica es un 404, nunca un 403 con
contenido: la existencia del objeto ya es información (ADR-0003).
"""

import base64

from allauth.account.internal.decorators import login_stage_required
from allauth.mfa.adapter import get_adapter as adaptador_del_segundo_factor
from allauth.mfa.totp.internal.auth import TOTP, clear_totp_secret
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.tenancy.forms import AltaDeSegundoFactorForm, CrearUsuarioForm, UsuarioForm
from apps.tenancy.models import Sede, Usuario
from apps.tenancy.permisos import solo_admin
from apps.tenancy.sedes import fijar_sede, sede_actual
from apps.tenancy.segundo_factor import CLAVE_DE_LA_ETAPA


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


@login_required
@require_POST
def seguir_conectado(request):
    """Renueva el plazo de la sesión sin recargar la página.

    Lo llama el aviso de caducidad cuando el Usuario dice que sigue ahí. No
    devuelve página: quien lo pide está a media ficha y no quiere perderla.
    """
    # `SESSION_SAVE_EVERY_REQUEST` ya renueva el plazo en cada petición; esto lo
    # deja dicho aquí, para que la vista siga cumpliendo su promesa aunque esa
    # opción cambie.
    request.session.modified = True
    return HttpResponse(status=204)


@login_required
@require_POST
def cambiar_de_usuario(request):
    """Cierra la sesión y deja el login listo para quien viene detrás.

    La tablet no se mueve del box, así que la Sede se conserva: quien entra
    detrás no tiene que volver a elegir dónde está trabajando. Lo demás se va
    con la sesión — cambiar de Usuario es cambiar de Usuario, no compartirla.
    """
    sede = sede_actual(request)
    logout(request)
    if sede is not None:
        fijar_sede(request, sede)
    messages.info(request, _("Entre con su propio correo."))
    return redirect("account_login")


@login_stage_required(stage=CLAVE_DE_LA_ETAPA, redirect_urlname="account_login")
def alta_de_segundo_factor(request):
    """El admin da de alta su segundo factor para terminar de entrar.

    Se llega aquí con el login a medias: hay contraseña correcta, pero todavía
    no hay sesión. Hasta que el código no cuadre, no la hay.
    """
    etapa = request._login_stage
    usuario = etapa.login.user
    formulario = AltaDeSegundoFactorForm(request.POST or None, user=usuario)
    if request.method == "POST" and formulario.is_valid():
        TOTP.activate(usuario, formulario.secret)
        clear_totp_secret(request)
        return etapa.exit()
    return render(
        request,
        "tenancy/alta_de_segundo_factor.html",
        {
            "formulario": formulario,
            "secreto": formulario.secret,
            "codigo_qr": _codigo_qr(usuario, formulario.secret),
        },
    )


def _codigo_qr(usuario, secreto):
    """El secreto dibujado para escanearlo con la cámara.

    Va como `data:` dentro de la página y no como una imagen aparte: es un
    secreto, y una URL propia sería una URL que se puede pedir dos veces.
    """
    adaptador = adaptador_del_segundo_factor()
    svg = adaptador.build_totp_svg(adaptador.build_totp_url(usuario, secreto))
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")

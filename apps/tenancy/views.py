"""Panel de la Clínica, administración de Usuarios y configuración de la Sede.

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

from apps.tenancy.forms import (
    AltaDeSegundoFactorForm,
    ClinicaDeDerivacionForm,
    CrearUsuarioForm,
    ExcepcionForm,
    FranjaForm,
    UrgenciasForm,
    UsuarioForm,
)
from apps.tenancy.horarios import Dia
from apps.tenancy.models import (
    ClinicaDeDerivacion,
    ExcepcionDeAtencion,
    FranjaDeAtencion,
    Sede,
    Usuario,
)
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


# ---------------------------------------------------------------------------
# Configuración de la Sede: Horario de atención y Clínicas de derivación.
#
# En H1 esto no cambia nada de lo que ve el mostrador: es lo que la agenda (H3)
# y la Autorespuesta (H4) van a preguntar. Por eso vive detrás de un enlace del
# admin y no en la página de inicio de nadie.
# ---------------------------------------------------------------------------


def _sedes_de_la_clinica(request):
    return request.user.clinic.sedes.all()


def _derivaciones_de_la_clinica(request):
    return ClinicaDeDerivacion.objects.all()


def _sede_de_la_clinica(request, pk):
    """La Sede pedida, siempre que sea de la Clínica de quien la pide."""
    return get_object_or_404(_sedes_de_la_clinica(request), pk=pk)


def _semana(sede):
    """El Horario de atención como se lee en la puerta: los siete días, en orden.

    Los días sin Franjas salen igual, vacíos. Un horario se revisa mirando qué
    falta —«el sábado no está»—, y para eso el día tiene que aparecer.
    """
    franjas = list(sede.franjas.all())
    return [
        {"dia": dia.label, "franjas": [f for f in franjas if f.dia == dia]} for dia in Dia
    ]


def _pagina_del_horario(request, sede, urgencias=None, franja=None, excepcion=None):
    """La página de la Sede, con los formularios que traiga quien la pinte.

    Los tres formularios conviven en la misma página, así que cada vista que
    guarda uno vuelve aquí con el suyo —con sus errores, si los tiene— y deja
    que los otros dos nazcan vacíos.
    """
    return render(
        request,
        "tenancy/horario_de_la_sede.html",
        {
            "sede": sede,
            "semana": _semana(sede),
            "excepciones": sede.excepciones.all(),
            "formulario_de_urgencias": urgencias or UrgenciasForm(instance=sede),
            "formulario_de_franja": franja or FranjaForm(sede=sede),
            "formulario_de_excepcion": excepcion or ExcepcionForm(sede=sede),
        },
    )


@solo_admin
def configuracion(request):
    """Por dónde se entra a lo que la Clínica declara de sí misma."""
    return render(
        request,
        "tenancy/configuracion.html",
        {"sedes": _sedes_de_la_clinica(request)},
    )


@solo_admin
def horario_de_la_sede(request, pk):
    return _pagina_del_horario(request, _sede_de_la_clinica(request, pk))


@solo_admin
@require_POST
def guardar_urgencias(request, pk):
    sede = _sede_de_la_clinica(request, pk)
    formulario = UrgenciasForm(request.POST, instance=sede)
    if formulario.is_valid():
        formulario.save()
        return redirect("tenancy:horario_de_la_sede", pk=sede.pk)
    return _pagina_del_horario(request, sede, urgencias=formulario)


@solo_admin
@require_POST
def crear_franja(request, pk):
    sede = _sede_de_la_clinica(request, pk)
    formulario = FranjaForm(request.POST, sede=sede)
    if formulario.is_valid():
        formulario.save()
        return redirect("tenancy:horario_de_la_sede", pk=sede.pk)
    return _pagina_del_horario(request, sede, franja=formulario)


@solo_admin
@require_POST
def quitar_franja(request, pk, franja):
    """Una Franja sí se borra: es lo que la Sede dice que hace hoy, no un hecho
    del pasado. Cuando el horario cambia, el horario de antes no le importa a
    nadie — lo que pasó de verdad son las Consultas, y esas no se tocan."""
    sede = _sede_de_la_clinica(request, pk)
    get_object_or_404(FranjaDeAtencion.objects.filter(sede=sede), pk=franja).delete()
    return redirect("tenancy:horario_de_la_sede", pk=sede.pk)


@solo_admin
@require_POST
def crear_excepcion(request, pk):
    sede = _sede_de_la_clinica(request, pk)
    formulario = ExcepcionForm(request.POST, sede=sede)
    if formulario.is_valid():
        formulario.save()
        return redirect("tenancy:horario_de_la_sede", pk=sede.pk)
    return _pagina_del_horario(request, sede, excepcion=formulario)


@solo_admin
@require_POST
def quitar_excepcion(request, pk, excepcion):
    sede = _sede_de_la_clinica(request, pk)
    get_object_or_404(ExcepcionDeAtencion.objects.filter(sede=sede), pk=excepcion).delete()
    return redirect("tenancy:horario_de_la_sede", pk=sede.pk)


@solo_admin
def derivaciones(request):
    return render(
        request,
        "tenancy/derivaciones.html",
        {"derivaciones": _derivaciones_de_la_clinica(request)},
    )


@solo_admin
def crear_derivacion(request):
    formulario = ClinicaDeDerivacionForm(request.POST or None, clinica=request.user.clinic)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        return redirect("tenancy:derivaciones")
    return render(
        request,
        "tenancy/formulario_de_derivacion.html",
        {"formulario": formulario, "titulo": _("Añadir Clínica de derivación")},
    )


@solo_admin
def editar_derivacion(request, pk):
    derivacion = get_object_or_404(_derivaciones_de_la_clinica(request), pk=pk)
    formulario = ClinicaDeDerivacionForm(
        request.POST or None, instance=derivacion, clinica=request.user.clinic
    )
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        return redirect("tenancy:derivaciones")
    return render(
        request,
        "tenancy/formulario_de_derivacion.html",
        {"formulario": formulario, "titulo": _("Editar Clínica de derivación")},
    )


@solo_admin
@require_POST
def quitar_derivacion(request, pk):
    """La red de clínicas socias cambia: la que dejó de serlo se quita. No es un
    dato del que dependa ninguna Historia clínica — es una lista de teléfonos."""
    get_object_or_404(_derivaciones_de_la_clinica(request), pk=pk).delete()
    return redirect("tenancy:derivaciones")

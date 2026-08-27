"""La Clínica se lleva sus datos, y la Clínica que se va se cierra.

Las dos cosas están en la misma página porque son el mismo gesto contado entero:
una clínica que deja el sistema se exporta **y** se cierra, en ese orden. Poner
el cierre en otro sitio dejaría a alguien cerrando antes de haberse llevado nada.

**Todo esto es del admin.** Es el acceso masivo a los datos personales de toda la
Clínica, y es por lo que el rol admin tiene el segundo factor obligatorio
(ticket 13). Recepción y veterinario no pasan de aquí.

**La descarga no es una página, es un envío.** No hay URL que sirva el archivo:
se compone mientras sale, contra el POST de quien pulsó el botón, y no queda
copia en el disco ni en la base (`paquete.py`). Pedir esa URL con un GET no
devuelve un archivo viejo, devuelve un 405.

**Se anota antes de que salga el primer byte**, y no después como manda la regla
general del Registro (`apps/audit/registro.py`). Aquí la respuesta se compone
sola durante minutos: para cuando saliera el último byte, la anotación dependería
de que el navegador no cancelara la descarga a mitad. Y quien la cancela a mitad
ha leído los datos igual — la base ya los sirvió. Lo que se anota es una lectura
del conjunto por cada modelo con datos de Tutor o de Paciente que va dentro
(ADR-0004), que es lo que hay que poder demostrar: este Usuario se llevó todos
los Tutores de esta Clínica a esta hora.
"""

from django.contrib import messages
from django.contrib.auth import logout
from django.http import StreamingHttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.audit.models import Accion
from apps.audit.registro import anotando
from apps.exports import cierre
from apps.exports.forms import CierreForm
from apps.exports.hojas import HOJAS, de_quienes_son_los_datos
from apps.exports.paquete import como_un_zip, se_llama
from apps.tenancy.permisos import solo_admin

# Lo que se le pone a la descarga para que el navegador la guarde en vez de
# intentar enseñarla.
DESCARGA = "application/zip"


def _pagina(request, formulario):
    return render(
        request,
        "exports/exportacion.html",
        # La Clínica ya la pone el contexto de toda página interna
        # (`apps.tenancy.contexto`): la plantilla la nombra en el botón de cerrar.
        {"hojas": HOJAS, "formulario": formulario},
    )


@solo_admin
def exportacion(request):
    """Qué se lleva la Clínica si se lo lleva, y qué pasa si además se cierra."""
    return _pagina(request, CierreForm(clinica=request.user.clinic))


@solo_admin
@require_POST
def descarga(request):
    """Manda el zip con todo lo de la Clínica, componiéndolo mientras sale."""
    clinica = request.user.clinic
    momento = timezone.now()
    respuesta = StreamingHttpResponse(
        como_un_zip(HOJAS, clinica, momento), content_type=DESCARGA
    )
    respuesta["Content-Disposition"] = f'attachment; filename="{se_llama(clinica, momento)}"'
    # La otra mitad de «no queda accesible por una dirección permanente»: sin
    # esto, el navegador o un proxy por medio pueden guardarse una copia del zip
    # y volver a servirla. Aquí no se compone nada que se pueda volver a pedir.
    respuesta["Cache-Control"] = "private, no-store"
    return anotando(respuesta, request.user, Accion.LECTURA, *de_quienes_son_los_datos())


@solo_admin
@require_POST
def cerrar(request):
    """Cierra la Clínica: la deja sin acceso, y a quien lo pide fuera con ella."""
    formulario = CierreForm(request.POST, clinica=request.user.clinic)
    if not formulario.is_valid():
        return _pagina(request, formulario)

    nombre = request.user.clinic.nombre
    cierre.cerrar(request.user.clinic, request.user)
    # El aviso se deja **después** de cerrar la sesión: cerrarla vacía la sesión,
    # y con ella se iría el aviso que explica por qué ya no se puede entrar.
    logout(request)
    messages.info(
        request,
        _(
            "La Clínica %(clinica)s queda cerrada. Sus datos siguen guardados, pero "
            "ya no entra nadie: para reabrirla hay que pedírselo a quien administra "
            "el servidor."
        ) % {"clinica": nombre},
    )
    return redirect("account_login")

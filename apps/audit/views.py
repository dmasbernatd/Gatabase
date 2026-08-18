"""Consulta del Registro de acceso.

Con esta página el admin de la Clínica responde a la pregunta que hará la
autoridad: quién vio la ficha de este Tutor, y cuándo. Es de solo lectura,
porque el Registro no admite otra cosa.
"""

from django.core.paginator import Paginator
from django.shortcuts import render

from apps.audit.forms import FiltroDelRegistro
from apps.audit.models import RegistroDeAcceso
from apps.tenancy.permisos import solo_admin

ANOTACIONES_POR_PAGINA = 50
PARAMETRO_DE_PAGINA = "pagina"


def _filtro_en_la_url(request):
    """El filtro actual, listo para pegarle el número de página detrás.

    Sale con `&` al final, o vacío: así el enlace del paginador es
    `?usuario=3&pagina=2` o `?pagina=2`, y nunca `?&pagina=2`.
    """
    parametros = request.GET.copy()
    parametros.pop(PARAMETRO_DE_PAGINA, None)
    consulta = parametros.urlencode()
    return f"{consulta}&" if consulta else ""


@solo_admin
def registro(request):
    # Esta vista no se anota a sí misma: el Registro no contiene datos
    # personales de Tutor ni de Paciente, y anotarla lo llenaría de ruido.
    filtro = FiltroDelRegistro(request.GET or None, clinica=request.user.clinic)
    anotaciones = filtro.filtrar(RegistroDeAcceso.objects.select_related("usuario"))
    pagina = Paginator(anotaciones, ANOTACIONES_POR_PAGINA).get_page(
        request.GET.get(PARAMETRO_DE_PAGINA)
    )
    return render(
        request,
        "audit/registro.html",
        {"filtro": filtro, "pagina": pagina, "filtro_en_la_url": _filtro_en_la_url(request)},
    )

"""La importación de una planilla, en dos pasos: primero se enseña, luego se guarda.

Los dos pasos son el ticket entero. Una clínica sube el archivador de sus
Tutores una vez, con las manos del admin y sin nadie que sepa deshacerlo, así
que la pregunta no es «¿se importó?» sino «¿qué va a entrar y qué no?». La vista
previa la responde sin escribir nada, y es literalmente el mismo `examinar` que
después confirma: una vista previa que no fuera el ensayo exacto de la
importación sería peor que no tenerla.

Entre las dos páginas la planilla espera en el disco, colgada de la sesión de
quien la subió (`almacen.py`). Ninguna URL de aquí lleva identificador de nada,
y por eso no hay forma de pedir la planilla de otro.

**Todo esto es del admin**, no del mostrador: escribe cientos de fichas de un
golpe, y quien atiende no tiene por qué poder hacerlo sin querer.

**Del informe de errores no se guarda copia**, y no hace falta: la importación es
idempotente, así que volver a subir la misma planilla —corregida o no— vuelve a
decir exactamente qué falta y por qué, sin duplicar lo que ya entró. Un informe
guardado sería una segunda copia de datos personales envejeciendo en el disco
para responder a algo que se puede volver a preguntar.
"""

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.audit.models import Accion
from apps.audit.registro import anotando
from apps.imports import almacen
from apps.imports.forms import PlanillaForm
from apps.imports.models import Importacion
from apps.imports.planilla import PlanillaIlegible
from apps.imports.tutores import COLUMNAS_DE_LA_PLANILLA, EJEMPLO, examinar, importar
from apps.imports.tutores import ejemplo as planilla_de_ejemplo
from apps.tenancy.permisos import solo_admin
from apps.tutors.models import Tutor

# Cómo se llama el informe cuando se descarga. Lleva la palabra «errores» porque
# es lo que el admin va a buscar en su carpeta de descargas dentro de un rato.
INFORME = "errores-de-la-planilla.csv"

# Cuántas importaciones anteriores se enseñan. Las suficientes para reconocer
# por dónde iba una migración por tandas, no un historial: el historial entero
# está en el Registro de acceso, que es donde tiene que estar.
ULTIMAS = 10

# Lo que se le pone a una descarga para que el navegador la guarde en vez de
# enseñarla. `charset=utf-8` va aunque el archivo empiece por la marca de orden:
# la marca es para Excel, la cabecera para el navegador.
DESCARGA = "text/csv; charset=utf-8"


def _descarga(texto, nombre):
    respuesta = HttpResponse(texto, content_type=DESCARGA)
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return respuesta


def _lo_que_espera(request):
    """La planilla que espera confirmación ya examinada, o `None` si no hay ninguna.

    Devolver `None` es lo mismo para los tres sitios que lo llaman: se avisa y se
    vuelve al principio. Pasa cuando la sesión caducó, cuando alguien pidió la
    vista previa sin haber subido nada, y cuando lo subido no se deja leer — y
    entonces se descarta, porque volver a intentarlo daría el mismo error.
    """
    esperando = almacen.recuperar(request)
    if not esperando:
        messages.error(request, _("No hay ninguna planilla esperando. Vuelve a subirla."))
        return None

    nombre, contenido = esperando
    try:
        return nombre, examinar(contenido, request.user.clinic)
    except PlanillaIlegible as ilegible:
        almacen.olvidar(request)
        messages.error(request, str(ilegible))
        return None


def _anotando_a_quienes_nombra(respuesta, request, informe):
    """Deja constancia de las fichas que la página enseña, si enseña alguna.

    La vista previa nombra a los Tutores que ya están en la Clínica —«ya está en
    la Clínica: Camila Rojas»—, y eso es servir un dato personal suyo aunque
    nadie haya abierto su ficha (ADR-0004). Se anota el conjunto, como la caja
    del mostrador: una planilla puede nombrar a cientos.

    Cuando no se repite ninguna, la página no enseña a nadie que ya estuviera, y
    lo que no se llegó a servir no se anota.
    """
    if not informe.repetidas:
        return respuesta
    return anotando(respuesta, request.user, Accion.LECTURA, Tutor)


@solo_admin
def tutores(request):
    """Sube la planilla de Tutores. No guarda ninguna ficha: lleva a la vista previa."""
    formulario = PlanillaForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and formulario.is_valid():
        almacen.guardar(request, formulario.cleaned_data["archivo"])
        return redirect("imports:vista_previa")
    return render(
        request,
        "imports/tutores.html",
        {
            "formulario": formulario,
            "columnas": COLUMNAS_DE_LA_PLANILLA,
            # Lo que se importó antes, que es donde «cuántas filas» se puede
            # leer: el Registro de acceso anota **que** hubo una importación y
            # apunta a ella, pero no sabe guardar «ciento veinte filas». Y es lo
            # que hace falta para importar por tandas sin llevar la cuenta a
            # mano de por dónde iba la migración.
            "importaciones": Importacion.objects.select_related("usuario")[:ULTIMAS],
        },
    )


@solo_admin
def ejemplo_de_tutores(request):
    """La planilla de ejemplo, con el formato que se documenta al lado.

    Se genera de la misma definición que documenta la página y que lee el
    importador (`tutores.COLUMNAS_DE_LA_PLANILLA`), así que no puede quedarse
    atrás. No trae datos de nadie: son tres personas inventadas.
    """
    return _descarga(planilla_de_ejemplo(), EJEMPLO)


@solo_admin
def vista_previa(request):
    """Qué entraría y qué no, antes de que se guarde nada."""
    esperando = _lo_que_espera(request)
    if not esperando:
        return redirect("imports:tutores")

    planilla, informe = esperando
    respuesta = render(
        request, "imports/vista_previa.html", {"informe": informe, "planilla": planilla}
    )
    return _anotando_a_quienes_nombra(respuesta, request, informe)


@solo_admin
def informe(request):
    """El informe fila a fila, como planilla, para corregir el archivo y volver a subirlo."""
    esperando = _lo_que_espera(request)
    if not esperando:
        return redirect("imports:tutores")

    _, examinado = esperando
    return _anotando_a_quienes_nombra(_descarga(examinado.como_csv(), INFORME), request, examinado)


@solo_admin
@require_POST
def confirmar(request):
    """Guarda lo que la vista previa dio por creable, y solo eso."""
    esperando = _lo_que_espera(request)
    if not esperando:
        return redirect("imports:tutores")

    planilla, examinado = esperando
    importacion = importar(examinado, request.user.clinic, request.user, planilla)
    almacen.olvidar(request)

    messages.success(
        request,
        _("Importados %(creados)s Tutores de %(leidas)s filas.") % {
            "creados": importacion.filas_creadas,
            "leidas": importacion.filas_leidas,
        },
    )
    if importacion.filas_con_error:
        messages.warning(
            request,
            _(
                "%(cuantas)s filas quedaron sin importar por algún error. Corrígelas en la "
                "planilla y vuelve a subirla: lo que ya entró no se duplica."
            ) % {"cuantas": importacion.filas_con_error},
        )
    return redirect("tutors:lista")


@solo_admin
@require_POST
def descartar(request):
    """Tira la planilla que esperaba, sin importar nada."""
    almacen.olvidar(request)
    return redirect("imports:tutores")

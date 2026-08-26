"""La importación de una planilla, en dos pasos: primero se enseña, luego se guarda.

Los dos pasos son el ticket entero. Una clínica sube el archivador de sus
Tutores y el de sus animales una vez, con las manos del admin y sin nadie que
sepa deshacerlo, así que la pregunta no es «¿se importó?» sino «¿qué va a entrar
y qué no?». La vista previa la responde sin escribir nada, y es literalmente el
mismo `examinar` que después confirma: una vista previa que no fuera el ensayo
exacto de la importación sería peor que no tenerla.

**Aquí no se sabe qué es un Tutor ni qué es un Paciente.** Estas vistas son las
mismas para las dos planillas —y para la que venga—: lo que cambia de una a otra
lo declara su módulo, y quién es quién lo dice `importadores.py`. Es lo que hace
que la página de subida de Pacientes no sea una copia de la de Tutores con las
palabras cambiadas.

Entre las dos páginas la planilla espera en el disco, colgada de la sesión de
quien la subió (`almacen.py`), y con ella qué decía traer: confirmar es una sola
página para las dos. Ninguna URL de aquí lleva identificador de nada, y por eso
no hay forma de pedir la planilla de otro.

**Todo esto es del admin**, no del mostrador: escribe cientos de fichas de un
golpe, y quien atiende no tiene por qué poder hacerlo sin querer.

**Del informe de errores no se guarda copia**, y no hace falta: la importación es
idempotente, así que volver a subir la misma planilla —corregida o no— vuelve a
decir exactamente qué falta y por qué, sin duplicar lo que ya entró. Un informe
guardado sería una segunda copia de datos personales envejeciendo en el disco
para responder a algo que se puede volver a preguntar.
"""

from dataclasses import dataclass

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.audit.models import Accion
from apps.audit.registro import anotando
from apps.imports import almacen
from apps.imports.forms import PlanillaForm
from apps.imports.importadores import IMPORTADORES, el_de
from apps.imports.models import Importacion
from apps.imports.planilla import PlanillaIlegible
from apps.tenancy.permisos import solo_admin

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


@dataclass(frozen=True)
class LoQueEspera:
    """La planilla que espera, ya examinada: quién sabe leerla, cómo llegó y qué
    pasaría con ella. Los tres viajan juntos a las tres páginas que la usan."""

    importador: object
    planilla: str
    informe: object


def _como_se_llama_lo_que_entra(importador):
    """El nombre en singular y en plural de lo que esa planilla crea.

    Sale del modelo, que es quien sabe cómo se llama en el dominio, y se
    pregunta aquí una vez para que no haya tres sitios andando por dentro de su
    `_meta`.
    """
    modelo = importador.MODELO._meta
    return modelo.verbose_name, modelo.verbose_name_plural


def _descarga(texto, nombre):
    respuesta = HttpResponse(texto, content_type=DESCARGA)
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return respuesta


def _lo_que_espera(request):
    """La planilla que espera confirmación ya examinada, o `None` si no hay ninguna.

    Quién sabe leerla sale de lo que ella misma decía traer, no de por qué
    página se entró.

    Devolver `None` es lo mismo para los tres sitios que lo llaman: se avisa y se
    vuelve al principio. Pasa cuando la sesión caducó, cuando alguien pidió la
    vista previa sin haber subido nada, y cuando lo subido no se deja leer — y
    entonces se descarta, porque volver a intentarlo daría el mismo error.
    """
    esperando = almacen.recuperar(request)
    if not esperando or esperando.que not in IMPORTADORES:
        messages.error(request, _("No hay ninguna planilla esperando. Vuelve a subirla."))
        return None

    importador = el_de(esperando.que)
    try:
        return LoQueEspera(
            importador,
            esperando.nombre,
            importador.examinar(esperando.contenido, request.user.clinic),
        )
    except PlanillaIlegible as ilegible:
        almacen.olvidar(request)
        messages.error(request, str(ilegible))
        return None


def _anotando_a_quienes_nombra(respuesta, request, informe):
    """Deja constancia de las fichas que la página enseña, si enseña alguna.

    La vista previa nombra a quien ya está en la Clínica —«ya está en la Clínica:
    Camila Rojas», «hay dos Tutores que podrían ser»—, y eso es servir un dato
    personal suyo aunque nadie haya abierto su ficha (ADR-0004). Se anota el
    conjunto, como la caja del mostrador: una planilla puede nombrar a cientos.

    Qué se nombró lo dice el informe y no esta vista (`Informe.lo_que_nombra`):
    aquí no se sabe de qué era la planilla, y una fila que solo se compara con
    otra fila del mismo archivo no ha servido el dato de nadie.
    """
    nombrados = informe.lo_que_nombra
    if not nombrados:
        return respuesta
    return anotando(respuesta, request.user, Accion.LECTURA, *nombrados)


@solo_admin
def subida(request, que):
    """Sube una planilla. No guarda ninguna ficha: lleva a la vista previa."""
    importador = el_de(que)
    que_entra, que_entran = _como_se_llama_lo_que_entra(importador)
    formulario = PlanillaForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and formulario.is_valid():
        almacen.guardar(request, formulario.cleaned_data["archivo"], que)
        return redirect("imports:vista_previa")
    return render(
        request,
        importador.PLANTILLA,
        {
            "formulario": formulario,
            "columnas": importador.COLUMNAS_DE_LA_PLANILLA,
            "que_entra": que_entra,
            "que_entran": que_entran,
            "url_del_ejemplo": importador.URL_DEL_EJEMPLO,
            # Lo que se importó antes **de esto mismo**, que es donde «cuántas
            # filas» se puede leer: el Registro de acceso anota **que** hubo una
            # importación y apunta a ella, pero no sabe guardar «ciento veinte
            # filas». Y es lo que hace falta para importar por tandas sin llevar
            # la cuenta a mano de por dónde iba la migración.
            "importaciones": Importacion.objects.filter(que_se_importo=que).select_related(
                "usuario"
            )[:ULTIMAS],
        },
    )


@solo_admin
def ejemplo(request, que):
    """La planilla de ejemplo, con el formato que se documenta al lado.

    Se genera de la misma definición que documenta la página y que lee el
    importador (`COLUMNAS_DE_LA_PLANILLA`), así que no puede quedarse atrás. No
    trae datos de nadie: son tres personas y tres animales inventados.
    """
    importador = el_de(que)
    return _descarga(importador.ejemplo(), importador.EJEMPLO)


@solo_admin
def vista_previa(request):
    """Qué entraría y qué no, antes de que se guarde nada."""
    esperando = _lo_que_espera(request)
    if not esperando:
        return redirect("imports:tutores")

    que_entra, que_entran = _como_se_llama_lo_que_entra(esperando.importador)
    respuesta = render(
        request,
        "imports/vista_previa.html",
        {
            "informe": esperando.informe,
            "planilla": esperando.planilla,
            "que_entra": que_entra,
            "que_entran": que_entran,
        },
    )
    return _anotando_a_quienes_nombra(respuesta, request, esperando.informe)


@solo_admin
def informe(request):
    """El informe fila a fila, como planilla, para corregir el archivo y volver a subirlo."""
    esperando = _lo_que_espera(request)
    if not esperando:
        return redirect("imports:tutores")

    examinado = esperando.informe
    return _anotando_a_quienes_nombra(_descarga(examinado.como_csv(), INFORME), request, examinado)


@solo_admin
@require_POST
def confirmar(request):
    """Guarda lo que la vista previa dio por creable, y solo eso."""
    esperando = _lo_que_espera(request)
    if not esperando:
        return redirect("imports:tutores")

    importador = esperando.importador
    importacion = importador.importar(
        esperando.informe, request.user.clinic, request.user, esperando.planilla
    )
    almacen.olvidar(request)

    en_plural = _como_se_llama_lo_que_entra(importador)[1]
    messages.success(
        request,
        _("Importados %(creados)s %(que)s de %(leidas)s filas.") % {
            "creados": importacion.filas_creadas,
            "que": en_plural,
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
    return redirect(importador.VUELVE_A)


@solo_admin
@require_POST
def descartar(request):
    """Tira la planilla que esperaba, sin importar nada.

    Se vuelve a la página de la planilla que se acaba de tirar, que es donde se
    sube la siguiente. Cuando no había ninguna —o ya no se sabe qué era— se
    vuelve a la de Tutores, que es por donde empieza toda migración.
    """
    que = almacen.que_espera(request)
    almacen.olvidar(request)
    if que in IMPORTADORES:
        return redirect(el_de(que).URL_DE_LA_SUBIDA)
    return redirect("imports:tutores")

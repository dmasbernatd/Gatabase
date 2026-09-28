"""El fichero de Tutores: listarlo, buscarlo, abrir una ficha, crearla y corregirla.

Ninguna de estas vistas filtra por Clínica: no hace falta. `Tutor.objects` ya
solo ve la Clínica activa, que el middleware resolvió a partir del Usuario. Un
Tutor de otra Clínica sencillamente no existe para esta consulta, y por eso
pedirlo por su identificador da 404 y no 403: la existencia ya es información.

Los datos de un Tutor son datos personales, así que servirlos o tocarlos deja
constancia en el Registro de acceso (ADR-0004). Cuando basta con la URL para
saber qué se sirvió —la ficha, el listado— lo anota el decorador
`deja_constancia`, después de responder y solo si respondió.

Las dos vistas que escriben llaman a `anotar` a mano, y no es por capricho: en
ellas la misma URL hace dos cosas distintas según cómo termine —el formulario de
corrección es una lectura, y guardarlo una modificación—, y eso el decorador no
lo puede saber desde fuera. Anotan igualmente después de tener la respuesta
compuesta, que es la regla que sostiene al Registro: lo que no se llegó a servir
no se anota.

La ficha que se está escribiendo puede ser una que ya existe: el Tutor que ya
tenía ese RUT, o los que comparten ese teléfono. Se dice dos veces y en dos
momentos distintos — mientras se teclea, en el hueco que repinta `coincidencias`,
y al guardar, al lado del campo o como aviso —, y las dos veces se dice el mismo
texto porque lo compone el mismo sitio (`apps/coincidencias.py`). Nombrar al otro
Tutor es enseñar un dato personal suyo, así que las dos dejan constancia igual
que si se hubiera abierto su ficha (ADR-0004).

El listado también responde a HTMX: la búsqueda, el orden y el paginado
devuelven solo la tabla de resultados. Se dispara al enviar la búsqueda y al
pulsar una cabecera o una página, nunca a cada tecla: cada una de esas
peticiones sirve datos personales y se anota, y una búsqueda por tecla llenaría
de ruido justo la tabla que tiene que valer como prueba.

La caja del mostrador (`mostrador`) sí busca mientras se escribe, y por eso lo
que anota es distinto: ver su docstring.

Por dónde acepta el Tutor que se le contacte se enseña en su ficha y se cambia en
página aparte (`consentimiento`), porque no es un dato que se teclea: es algo que
él dijo, y lo que se guarda es la declaración con su fecha.

Los derechos del titular —darle lo que consta de él, suprimirlo— son del admin y
viven en su propia página (`derechos`), a un clic de la ficha: son dos gestos que
no se hacen atendiendo en el mostrador, y uno de ellos no tiene vuelta atrás. Un
Tutor anonimizado sigue teniendo ficha, pero ya no se corrige ni se le toma el
consentimiento: rellenar cualquiera de las dos cosas sería volver a identificarlo.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.audit.models import Accion
from apps.audit.registro import anotando, anotar, deja_constancia
from apps.coincidencias import (
    avisar_de_lo_que_no_impidio_guardar,
    constancia_de_lo_que_impidio_guardar,
    responde_a_quien_se_parece,
)
from apps.patients.estados import FiltroPorEstado
from apps.patients.models import Paciente
from apps.tenancy.permisos import solo_admin
from apps.tutors import derechos as derechos_del_titular
from apps.tutors.consentimiento import como_esta
from apps.tutors.forms import AnonimizacionForm, ConsentimientoDeContactoForm, TutorForm
from apps.tutors.listado import ListadoDeTutores
from apps.tutors.models import Tutor
from apps.tutors.mostrador import BusquedaDelMostrador

# Lo que htmx pone en toda petición suya; Django lo entrega como cabecera.
PETICION_DE_HTMX = "HX-Request"


@login_required
def coincidencias(request, pk=None):
    """A qué Tutor se parece la ficha que se está escribiendo, mientras se escribe.

    El `pk` es el de la ficha que se está corrigiendo, si se está corrigiendo
    alguna: sin él, un Tutor coincidiría consigo mismo en cuanto se le tocara
    una letra al apellido.

    De lo demás —qué se responde, qué se anota y por qué— sabe
    `apps/coincidencias.py`, que es quien lo cuenta igual para las dos apps.
    """
    ficha = get_object_or_404(Tutor, pk=pk) if pk else None
    return responde_a_quien_se_parece(
        request, TutorForm(request.GET, instance=ficha, clinica=request.user.clinic)
    )


@login_required
def mostrador(request):
    """La caja única: encuentra al Paciente por lo que se escriba.

    Está en `tutors` porque atraviesa el Vínculo (ver `mostrador.py`), pero no
    es el fichero de Tutores: su ruta cuelga del panel y no de ninguna de las
    dos apps, porque lo que encuentra son Pacientes y quien responde por ellos.

    Anota **el conjunto** y no cada resultado, que es lo que separa esta caja
    del listado con paginación. La lista se repinta a cada pocas teclas, y
    anotar los veinte nombres que se ven de paso llenaría de ruido justo la
    tabla que tiene que valer como prueba: quedaría un Registro donde no se
    distingue a quién se consultó de verdad de quién pasó por delante mientras
    alguien escribía. La lectura de una persona concreta se anota al abrir su
    ficha, que es cuando alguien la consultó de verdad (ADR-0004).

    La página con la caja todavía vacía no sirve dato de nadie, y por eso no
    anota nada: es la misma regla de siempre —lo que no se llegó a servir no se
    anota—, aplicada a una página que se abre antes de preguntar nada.
    """
    busqueda = BusquedaDelMostrador(request.GET)
    solo_los_resultados = PETICION_DE_HTMX in request.headers
    respuesta = render(
        request,
        "mostrador/_resultados.html" if solo_los_resultados else "mostrador/buscador.html",
        {"busqueda": busqueda},
    )
    if busqueda.vacia:
        return respuesta
    # Los dos conjuntos, porque la tabla enseña datos de los dos: el animal y
    # quien responde por él, con su teléfono.
    return anotando(respuesta, request.user, Accion.LECTURA, Paciente, Tutor)


@login_required
@deja_constancia(Accion.LECTURA, sobre=Tutor, identificado_por=None)
def lista(request):
    listado = ListadoDeTutores(Tutor.objects.all(), request.GET)
    solo_el_listado = PETICION_DE_HTMX in request.headers
    return render(
        request,
        "tutors/listado.html" if solo_el_listado else "tutors/lista.html",
        {"listado": listado},
    )


@login_required
@deja_constancia(Accion.LECTURA, sobre=Tutor)
def ficha(request, pk):
    tutor = get_object_or_404(Tutor, pk=pk)
    # De qué animales se hace cargo **hoy**: los que dejaron de venir y los que
    # murieron se piden. Quien abre esta ficha suele tener al Tutor al teléfono,
    # y lo que necesita saber es a quién atiende; enseñar de entrada a los que
    # ya no están es invitar a citar a un animal muerto.
    filtro = FiltroPorEstado(request.GET)
    pacientes = list(filtro.aplicado_a(tutor.de_quienes_se_hace_cargo))
    # Y de cuáles se hizo cargo antes, con la fecha hasta la que respondió por
    # ellos: el animal cambió de manos y sigue constando que fue suyo, que es lo
    # que se mira cuando llama preguntando por lo que se le hizo mientras lo
    # tuvo. Sin filtro de estado, porque es historia y no una lista de trabajo.
    cerrados = list(tutor.de_quienes_se_hizo_cargo)
    respuesta = render(
        request,
        "tutors/ficha.html",
        {
            "tutor": tutor,
            "pacientes": pacientes,
            "filtro": filtro,
            "cerrados": cerrados,
            # Por dónde acepta que se le escriba, con su fecha. Va en la ficha y
            # no a un clic porque la pregunta se hace justo aquí: quien mira esta
            # página es quien está a punto de contactarlo.
            "consentimiento": como_esta(tutor),
        },
    )
    # El Tutor lo anota el decorador; sus Pacientes, no: la ficha los nombra uno
    # a uno, y la ley protege la ficha del animal igual que la de su Tutor,
    # porque por ella se llega a él (ADR-0004). Los que fueron suyos también
    # salen nombrados, y un nombre servido es una lectura.
    return anotando(
        respuesta,
        request.user,
        Accion.LECTURA,
        *pacientes,
        *(vinculo.paciente for vinculo in cerrados),
    )


@login_required
def crear(request):
    formulario = TutorForm(request.POST or None, clinica=request.user.clinic)
    if request.method == "POST" and formulario.is_valid():
        tutor = formulario.save()
        anotar(request.user, Accion.CREACION, tutor)
        avisar_de_lo_que_no_impidio_guardar(request, formulario)
        return redirect("tutors:ficha", pk=tutor.pk)
    respuesta = render(
        request,
        "tutors/formulario.html",
        {"formulario": formulario, "titulo": _("Registrar Tutor")},
    )
    # Un formulario vacío no enseña datos de nadie, y uno rechazado tampoco
    # salvo cuando el RUT ya era de otro: entonces la página trae su nombre.
    constancia_de_lo_que_impidio_guardar(request, formulario)
    return respuesta


@login_required
def editar(request, pk):
    tutor = get_object_or_404(Tutor.objects.filter(Tutor.IDENTIFICABLES), pk=pk)
    formulario = TutorForm(request.POST or None, instance=tutor, clinica=request.user.clinic)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        anotar(request.user, Accion.MODIFICACION, tutor)
        avisar_de_lo_que_no_impidio_guardar(request, formulario)
        return redirect("tutors:ficha", pk=tutor.pk)
    respuesta = render(
        request,
        "tutors/formulario.html",
        {"formulario": formulario, "titulo": _("Corregir la ficha"), "tutor": tutor},
    )
    # Se llega aquí al abrir el formulario y al volver de una corrección que no
    # se pudo guardar. En los dos casos la página enseña los datos del Tutor, y
    # eso es una lectura: quien la vio la vio, aunque no cambiara nada. Se anota
    # con la respuesta ya compuesta, no antes: una página que no se llegó a
    # componer no la vio nadie.
    anotar(request.user, Accion.LECTURA, tutor)
    constancia_de_lo_que_impidio_guardar(request, formulario)
    return respuesta


@login_required
def consentimiento(request, pk):
    """Registra o revoca por qué canales acepta el Tutor que se le contacte.

    En página aparte de la ficha por lo mismo que el estado del Paciente: no es
    una corrección de la ficha, es dejar constancia de algo que el Tutor dijo, y
    con su fecha. La ficha enseña lo que consta; aquí se cambia.

    Lo que se guarda **no pisa** lo anterior: cada respuesta que cambia deja su
    propia declaración, y la anterior sigue ahí. Eso es lo que hace que el
    consentimiento sea exigible ante la Ley 21.719 — no vale decir qué acepta
    hoy, hay que poder decir desde cuándo lo aceptaba el día que se le escribió.

    Se anota como modificación **solo si algo cambió** (ADR-0004): guardar el
    formulario tal como llegó no toca ningún dato de nadie, y anotarlo dejaría en
    el Registro de acceso una modificación que no ocurrió. La lectura sí consta
    siempre, que es lo que de verdad pasó al abrir la página.
    """
    tutor = get_object_or_404(Tutor.objects.filter(Tutor.IDENTIFICABLES), pk=pk)
    formulario = ConsentimientoDeContactoForm(request.POST or None, tutor=tutor)
    if request.method == "POST" and formulario.is_valid():
        if formulario.guardar():
            anotar(request.user, Accion.MODIFICACION, tutor)
        return redirect("tutors:ficha", pk=tutor.pk)
    respuesta = render(
        request,
        "tutors/consentimiento.html",
        # Con todo lo que ha dicho hasta hoy: «queda registro» solo significa
        # algo si alguien lo puede mirar sin abrir la base de datos.
        {
            "formulario": formulario,
            "tutor": tutor,
            "historia": tutor.lo_que_ha_dicho_del_contacto,
        },
    )
    # La página dice de quién se habla, con su nombre y por dónde se le contacta:
    # eso es servir datos personales, y consta aunque no se cambie nada.
    return anotando(respuesta, request.user, Accion.LECTURA, tutor)


def _pagina_de_derechos(request, tutor, formulario):
    respuesta = render(
        request, "tutors/derechos.html", {"tutor": tutor, "formulario": formulario}
    )
    # La página dice de quién se habla, y pide escribir su nombre: es una
    # lectura de sus datos aunque no se descargue ni se suprima nada.
    return anotando(respuesta, request.user, Accion.LECTURA, tutor)


@solo_admin
def derechos(request, pk):
    """Lo que el Tutor puede pedir de sus datos: que se le den, o que se supriman."""
    tutor = get_object_or_404(Tutor, pk=pk)
    return _pagina_de_derechos(request, tutor, AnonimizacionForm(tutor=tutor))


@solo_admin
@require_POST
def datos_del_titular(request, pk):
    """Entrega lo que consta del Tutor en un documento que se lee sin programas.

    Un HTML autocontenido y no un zip de planillas como el de la Clínica: esto
    lo lee una persona que pidió saber qué se guarda de ella, no el Excel de
    otro sistema, y un navegador lo abre, lo imprime y lo guarda como PDF.

    Va por POST y no por un enlace, por lo mismo que la exportación de la
    Clínica: se compone contra la petición de quien lo pide y no queda en
    ninguna parte, así que no hay dirección que alguien pueda volver a abrir.

    Se puede pedir también de un Tutor ya anonimizado: sus datos ya no están,
    pero el Registro de quién los vio mientras estuvieron sí, y es lo que habrá
    que enseñar si alguien pregunta después qué se hizo con ellos.
    """
    tutor = get_object_or_404(Tutor, pk=pk)
    momento = timezone.now()
    consta = derechos_del_titular.lo_que_consta_de(tutor)
    respuesta = HttpResponse(
        render_to_string(
            "tutors/datos_del_titular.html",
            {
                "consta": consta,
                "momento": momento,
                "clinica": tutor.clinic,
                "sin_lo_del_conjunto": derechos_del_titular.SIN_LO_DEL_CONJUNTO,
            },
            request=request,
        ),
        content_type="text/html; charset=utf-8",
    )
    respuesta["Content-Disposition"] = (
        f'attachment; filename="{derechos_del_titular.se_llama(tutor, momento)}"'
    )
    respuesta["Cache-Control"] = "private, no-store"
    # El Tutor y los Pacientes que nombra, igual que su ficha: el documento es
    # la ficha entera y algo más.
    return anotando(respuesta, request.user, Accion.LECTURA, tutor, *consta.pacientes)


@solo_admin
@require_POST
def anonimizar(request, pk):
    """Suprime los datos personales del Tutor, sin tocar a sus Pacientes.

    Qué se borra y qué se queda lo cuenta `derechos.py`. Aquí solo se pide la
    confirmación —escribir su nombre—, porque es lo único de esta aplicación que
    no se deshace.
    """
    tutor = get_object_or_404(Tutor.objects.filter(Tutor.IDENTIFICABLES), pk=pk)
    formulario = AnonimizacionForm(request.POST, tutor=tutor)
    if not formulario.is_valid():
        return _pagina_de_derechos(request, tutor, formulario)

    derechos_del_titular.anonimizar(tutor, request.user)
    # El aviso no dice cómo se llamaba, y no por despiste: los avisos esperan en
    # la sesión, y la sesión se guarda en la base de datos. Nombrarlo aquí sería
    # dejar una copia del nombre que se acaba de suprimir.
    messages.success(
        request,
        _(
            "Los datos personales del Tutor se han suprimido. Sus Pacientes "
            "siguen como estaban, a cargo de un Tutor anonimizado."
        ),
    )
    return redirect("tutors:ficha", pk=tutor.pk)

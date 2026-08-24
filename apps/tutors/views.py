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

Al guardar, el formulario puede haber tropezado con otro Tutor: el que ya tenía
ese RUT, o los que comparten ese teléfono. Los dos avisos dicen de quién se
trata, y decirlo es enseñar un dato personal, así que los dos dejan constancia
igual que si se hubiera abierto su ficha (ADR-0004).

El listado también responde a HTMX: la búsqueda, el orden y el paginado
devuelven solo la tabla de resultados. Se dispara al enviar la búsqueda y al
pulsar una cabecera o una página, nunca a cada tecla: cada una de esas
peticiones sirve datos personales y se anota, y una búsqueda por tecla llenaría
de ruido justo la tabla que tiene que valer como prueba.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.audit.models import Accion
from apps.audit.registro import anotando, anotar, deja_constancia
from apps.patients.estados import FiltroPorEstado
from apps.tutors.forms import TutorForm
from apps.tutors.listado import ListadoDeTutores
from apps.tutors.models import Tutor

# Lo que htmx pone en toda petición suya; Django lo entrega como cabecera.
PETICION_DE_HTMX = "HX-Request"


def constancia_del_rut_repetido(request, formulario):
    """Anota la lectura del Tutor cuyo nombre trae el aviso de RUT repetido.

    El formulario rechazado no guardó nada, pero la página que vuelve dice a
    quién pertenece ya ese RUT y enlaza a su ficha: recepción ha visto un dato
    personal suyo sin haber abierto nada.
    """
    otro = formulario.tutor_con_el_mismo_rut
    if otro:
        anotar(request.user, Accion.LECTURA, otro)


def avisar_del_telefono_compartido(request, formulario):
    """Avisa de los Tutores que ya tenían el teléfono que se acaba de guardar.

    No impide nada: una familia comparte número, y bloquearlo obligaría a
    recepción a inventarse un teléfono falso para el segundo Tutor. Solo lo pone
    delante, por si eran la misma persona registrada dos veces. Cada aviso dice
    un nombre, así que cada aviso es una lectura y consta como tal.
    """
    for otro in formulario.quienes_comparten_el_telefono():
        messages.warning(
            request,
            format_html(
                _("Este teléfono es también el de {ficha}."),
                ficha=formulario.enlace_a(otro),
            ),
        )
        anotar(request.user, Accion.LECTURA, otro)


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
    respuesta = render(
        request,
        "tutors/ficha.html",
        {"tutor": tutor, "pacientes": pacientes, "filtro": filtro},
    )
    # El Tutor lo anota el decorador; sus Pacientes, no: la ficha los nombra uno
    # a uno, y la ley protege la ficha del animal igual que la de su Tutor,
    # porque por ella se llega a él (ADR-0004).
    return anotando(respuesta, request.user, Accion.LECTURA, *pacientes)


@login_required
def crear(request):
    formulario = TutorForm(request.POST or None, clinica=request.user.clinic)
    if request.method == "POST" and formulario.is_valid():
        tutor = formulario.save()
        anotar(request.user, Accion.CREACION, tutor)
        avisar_del_telefono_compartido(request, formulario)
        return redirect("tutors:ficha", pk=tutor.pk)
    respuesta = render(
        request,
        "tutors/formulario.html",
        {"formulario": formulario, "titulo": _("Registrar Tutor")},
    )
    # Un formulario vacío no enseña datos de nadie, y uno rechazado tampoco
    # salvo cuando el RUT ya era de otro: entonces la página trae su nombre.
    constancia_del_rut_repetido(request, formulario)
    return respuesta


@login_required
def editar(request, pk):
    tutor = get_object_or_404(Tutor, pk=pk)
    formulario = TutorForm(request.POST or None, instance=tutor, clinica=request.user.clinic)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        anotar(request.user, Accion.MODIFICACION, tutor)
        avisar_del_telefono_compartido(request, formulario)
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
    constancia_del_rut_repetido(request, formulario)
    return respuesta

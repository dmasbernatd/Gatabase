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

El listado también responde a HTMX: la búsqueda, el orden y el paginado
devuelven solo la tabla de resultados. Se dispara al enviar la búsqueda y al
pulsar una cabecera o una página, nunca a cada tecla: cada una de esas
peticiones sirve datos personales y se anota, y una búsqueda por tecla llenaría
de ruido justo la tabla que tiene que valer como prueba.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from apps.audit.models import Accion
from apps.audit.registro import anotar, deja_constancia
from apps.tutors.forms import TutorForm
from apps.tutors.listado import ListadoDeTutores
from apps.tutors.models import Tutor

# Lo que htmx pone en toda petición suya; Django lo entrega como cabecera.
PETICION_DE_HTMX = "HX-Request"


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
    return render(request, "tutors/ficha.html", {"tutor": get_object_or_404(Tutor, pk=pk)})


@login_required
def crear(request):
    formulario = TutorForm(request.POST or None, clinica=request.user.clinic)
    if request.method == "POST" and formulario.is_valid():
        tutor = formulario.save()
        anotar(request.user, Accion.CREACION, tutor)
        return redirect("tutors:ficha", pk=tutor.pk)
    # Un formulario vacío no enseña datos de nadie: no hay nada que anotar.
    return render(
        request,
        "tutors/formulario.html",
        {"formulario": formulario, "titulo": _("Registrar Tutor")},
    )


@login_required
def editar(request, pk):
    tutor = get_object_or_404(Tutor, pk=pk)
    formulario = TutorForm(request.POST or None, instance=tutor, clinica=request.user.clinic)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        anotar(request.user, Accion.MODIFICACION, tutor)
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
    return respuesta

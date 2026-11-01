"""La Consulta: abrirla desde la ficha del Paciente, leerla y escribirla.

Ninguna de estas vistas filtra por Clínica, y no hace falta: `Consulta.objects` y
`Paciente.objects` solo ven la Clínica activa, que el middleware resolvió a
partir del Usuario (ADR-0003). La Consulta de otra Clínica no existe para esta
consulta, y pedirla por su identificador da 404 y no 403 — la existencia ya es
información, y aquí lo que existiría es que ese animal fue atendido.

Quién entra: escribir una Consulta es del veterinario y de nadie más
(`solo_veterinario`), porque es él quien la firma. Leerla no, y a propósito:
recepción le imprime al Tutor lo que se le hizo al animal (ticket 09), y el admin
responde ante la autoridad por lo que consta. Lo que recepción no puede es
figurar como autor de un documento clínico ni corrigiendo una coma.

Y entre veterinarios: una Consulta abierta la escribe **su** autor. Otro la lee
entera y, si tiene algo que añadir, lo añadirá como Enmienda suya (ticket 03).
La regla la sabe el modelo (`Consulta.la_escribe`) y esta vista la ejercita; no
está en la plantilla que esconde el botón, porque quien llegue con la URL en la
mano también tiene que tropezar con ella.

Toda lectura de esta app queda en el Registro de acceso (ADR-0004) y no es una
lectura cualquiera: es un dato de salud, el más protegido que guarda el sistema.
Abrir la página de una Consulta se anota como lectura, guardarla como
modificación, y abrirla por primera vez como creación. Se anotan además el
Paciente del que se habla, porque la página dice de qué animal se trata: cada
ficha servida es una lectura, igual que en `patients`.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from apps.audit.models import Accion
from apps.audit.registro import anotando, anotar, deja_constancia
from apps.patients.models import Paciente
from apps.records.forms import ConsultaForm
from apps.records.models import Consulta
from apps.tenancy.permisos import solo_veterinario
from apps.tenancy.sedes import sede_actual

# Lo que se le dice a quien intenta escribir en una Consulta que no es suya. No
# nombra al autor: quien no la escribe tampoco necesita saber de quién es para
# entender que no le toca, y el nombre ya está en la página que sí puede leer.
NO_ES_SUYA = _("Esta Consulta la escribe el veterinario que la abrió. Puede leerla entera.")

# Lo que se le dice a quien llega sin Sede. No es un error del Usuario: es un
# admin que no le asignó ninguna, y la Consulta no puede no decir dónde se
# atendió, así que se para aquí y se dice qué hay que arreglar.
SIN_SEDE = _("No consta en qué Sede trabaja: pídale al admin de la Clínica que le asigne una.")


@login_required
@deja_constancia(Accion.LECTURA, sobre=Consulta)
def consulta(request, pk):
    """Lee una Consulta entera.

    La lee cualquier Usuario de la Clínica, no solo su autor ni solo
    veterinarios: es la hoja que antes estaba en el archivador, y recepción la
    necesita para decirle al Tutor lo que se le hizo al animal.
    """
    consulta = get_object_or_404(Consulta, pk=pk)
    respuesta = render(
        request,
        "records/consulta.html",
        {"consulta": consulta, "la_escribe": consulta.la_escribe(request.user)},
    )
    # La Consulta la anota el decorador; su Paciente, no: la página dice de qué
    # animal se trata y enlaza a su ficha, y eso es una lectura de esa ficha.
    return anotando(respuesta, request.user, Accion.LECTURA, consulta.paciente)


@solo_veterinario
def abrir(request, paciente):
    """Abre una Consulta para el Paciente y la deja abierta para seguir escribiendo.

    Se entra desde la ficha del animal y no desde un listado de Consultas: se
    abre con el Paciente delante, que es el único momento en que se abre una.

    No necesita Cita ninguna, y es lo que hace que sirva en el mostrador: la
    mitad de lo que entra por la puerta no tenía hora, y `records` no sabe
    siquiera que existan las Citas (`CLAUDE.md`).
    """
    paciente = get_object_or_404(Paciente, pk=paciente)
    # Un Paciente fallecido no admite Consultas nuevas: su Historia clínica
    # queda en solo lectura (`CONTEXT.md`). Se impone aquí y no escondiendo el
    # botón, como la corrección de su ficha en `patients`. No es un 403 ni un
    # 404 —el animal existe y su Historia se puede leer— sino un desvío a verla.
    if not paciente.admite_consultas:
        messages.info(request, paciente.por_que_no_admite_consultas)
        return redirect("patients:ficha", pk=paciente.pk)
    sede = sede_actual(request)
    if sede is None:
        messages.error(request, SIN_SEDE)
        return redirect("patients:ficha", pk=paciente.pk)
    formulario = ConsultaForm(
        request.POST or None,
        clinica=request.user.clinic,
        paciente=paciente,
        veterinario=request.user,
        sede=sede,
    )
    if request.method == "POST" and formulario.is_valid():
        abierta = formulario.save()
        anotar(request.user, Accion.CREACION, abierta)
        # La Historia clínica del Paciente cambió: tiene una Consulta más.
        anotar(request.user, Accion.MODIFICACION, paciente)
        return redirect("records:consulta", pk=abierta.pk)
    respuesta = render(
        request,
        "records/formulario.html",
        {"formulario": formulario, "paciente": paciente, "titulo": _("Abrir Consulta")},
    )
    # La página dice de qué animal se va a hablar, con su nombre.
    return anotando(respuesta, request.user, Accion.LECTURA, paciente)


@solo_veterinario
def escribir(request, pk):
    """Sigue escribiendo una Consulta abierta. Guardar la deja abierta y vuelve a ella.

    Guardar cuantas veces se quiera es el caso corriente y no una concesión: una
    Consulta no se escribe de una vez, se escribe entre que entra el animal y
    que sale. Cerrarla es otro acto y llega en el ticket 02.
    """
    consulta = get_object_or_404(Consulta, pk=pk)
    if not consulta.la_escribe(request.user):
        messages.info(request, NO_ES_SUYA)
        return redirect("records:consulta", pk=consulta.pk)
    formulario = ConsultaForm(
        request.POST or None,
        instance=consulta,
        clinica=request.user.clinic,
        paciente=consulta.paciente,
        veterinario=consulta.veterinario,
        sede=consulta.sede,
    )
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        anotar(request.user, Accion.MODIFICACION, consulta)
        return redirect("records:consulta", pk=consulta.pk)
    respuesta = render(
        request,
        "records/formulario.html",
        {
            "formulario": formulario,
            "consulta": consulta,
            "paciente": consulta.paciente,
            "titulo": _("Escribir la Consulta"),
        },
    )
    # Se llega aquí al abrir el formulario y al volver de un guardado que no se
    # pudo hacer. En los dos casos la página enseña lo escrito, y eso es una
    # lectura de la Consulta y de la ficha del animal.
    return anotando(respuesta, request.user, Accion.LECTURA, consulta, consulta.paciente)

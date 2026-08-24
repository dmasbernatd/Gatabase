"""La ficha de un Paciente: registrarlo, abrirla, corregirla y decir quién responde.

Ninguna de estas vistas filtra por Clínica, y no hace falta: `Paciente.objects` y
`Tutor.objects` ya solo ven la Clínica activa, que el middleware resolvió a
partir del Usuario (ADR-0003). Un Paciente de otra Clínica no existe para esta
consulta, y pedirlo por su identificador da 404 y no 403, porque la existencia ya
es información.

Los datos de un Paciente también se registran al servirlos (ADR-0004): la ley
protege la ficha del animal igual que la de su Tutor, porque por ella se llega a
él. Lo que la URL basta para identificar lo anota el decorador
`deja_constancia`; lo demás va con `anotando`, que anota lo que la página enseña
después de tenerla compuesta. Y estas páginas enseñan más de una cosa: la ficha
del Paciente dice cómo se llaman sus Tutores, y el alta dice de quién es el
animal que se está registrando. Cada nombre servido es una lectura.

Al guardar, el formulario puede haber tropezado con otro Paciente: el que ya
tenía ese microchip. El aviso dice de quién se trata y enlaza a su ficha, y
decirlo es enseñar esa ficha, así que deja constancia igual que si se hubiera
abierto (ADR-0004).

Un Paciente nunca nace suelto: se registra desde la ficha del Tutor que lo trae,
y ese Tutor queda como responsable. Es como llega un animal al mostrador — con
alguien— y ahorra el estado intermedio de un Paciente del que nadie responde.

Que el animal muriera o dejara de venir tiene vista propia (`estado`), y la de
corregir la ficha se aparta cuando consta fallecido: entonces la ficha se
conserva entera y en solo lectura, que es lo contrario de borrarla.

Que cambiara de manos tiene otras dos (`traspasar` y `cerrar_vinculo`), y las dos
escriben en Vínculos y no en la ficha del animal: el Paciente sigue siendo el
mismo, con la misma Historia clínica (ADR-0001). Las dos tocan además datos de
dos personas —quien lo tenía y quien lo tiene—, así que las dos dejan constancia
sobre cada una de ellas.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.audit.models import Accion
from apps.audit.registro import anotando, anotar, deja_constancia
from apps.patients.catalogo import razas_de
from apps.patients.forms import (
    CierreDeVinculoForm,
    EstadoDelPacienteForm,
    PacienteForm,
    TraspasoForm,
    VinculoForm,
)
from apps.patients.models import Paciente
from apps.tutors.models import Tutor, Vinculo


def constancia_del_microchip_repetido(request, formulario):
    """Anota la lectura del Paciente cuyo nombre trae el aviso de chip repetido.

    El formulario rechazado no guardó nada, pero la página que vuelve dice de
    qué animal es ya ese chip y enlaza a su ficha: recepción la ha visto sin
    haber abierto nada.
    """
    otro = formulario.paciente_con_el_mismo_microchip
    if otro:
        anotar(request.user, Accion.LECTURA, otro)


@login_required
@deja_constancia(Accion.LECTURA, sobre=Paciente)
def ficha(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    vinculos = list(paciente.quienes_responden)
    # Los de antes se enseñan también, con la fecha hasta la que respondieron:
    # es lo que hace del cierre algo distinto de un borrado.
    cerrados = list(paciente.quienes_respondieron)
    respuesta = render(
        request,
        "patients/ficha.html",
        {"paciente": paciente, "vinculos": vinculos, "cerrados": cerrados},
    )
    # El Paciente lo anota el decorador; sus Tutores, no: la página los nombra
    # uno a uno, y nombrar a alguien es enseñar un dato personal suyo. Los de
    # antes también salen nombrados, y un nombre servido es una lectura aunque
    # el Vínculo esté cerrado.
    return anotando(
        respuesta,
        request.user,
        Accion.LECTURA,
        *(vinculo.tutor for vinculo in vinculos + cerrados),
    )


@login_required
def crear(request, tutor):
    tutor = get_object_or_404(Tutor, pk=tutor)
    formulario = PacienteForm(request.POST or None, clinica=request.user.clinic)
    if request.method == "POST" and formulario.is_valid():
        paciente = formulario.save()
        tutor.se_hace_cargo_de(paciente, responsable=True)
        anotar(request.user, Accion.CREACION, paciente)
        # La ficha del Tutor cambió también: ahora tiene un Paciente más.
        anotar(request.user, Accion.MODIFICACION, tutor)
        return redirect("patients:ficha", pk=paciente.pk)
    constancia_del_microchip_repetido(request, formulario)
    respuesta = render(
        request,
        "patients/formulario.html",
        {
            "formulario": formulario,
            "tutor": tutor,
            "titulo": _("Registrar Paciente"),
        },
    )
    # La página dice de quién va a ser el Paciente, con su nombre.
    return anotando(respuesta, request.user, Accion.LECTURA, tutor)


@login_required
def editar(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    # La ficha de un Paciente fallecido se conserva entera y en solo lectura, y
    # eso se impone aquí y no escondiendo el enlace: quien llegue con la URL en
    # la mano o con una pestaña abierta de antes tampoco la corrige. No es un
    # 403 ni un 404 —la ficha existe y se puede ver— sino un desvío a verla.
    if not paciente.se_puede_corregir:
        messages.info(
            request,
            _("La ficha de un Paciente fallecido no se corrige: queda tal como estaba."),
        )
        return redirect("patients:ficha", pk=paciente.pk)
    formulario = PacienteForm(request.POST or None, instance=paciente, clinica=request.user.clinic)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        anotar(request.user, Accion.MODIFICACION, paciente)
        return redirect("patients:ficha", pk=paciente.pk)
    constancia_del_microchip_repetido(request, formulario)
    respuesta = render(
        request,
        "patients/formulario.html",
        {"formulario": formulario, "paciente": paciente, "titulo": _("Corregir la ficha")},
    )
    # Se llega aquí al abrir el formulario y al volver de una corrección que no
    # se pudo guardar. En los dos casos la página enseña la ficha, y eso es una
    # lectura aunque no se cambiara nada.
    return anotando(respuesta, request.user, Accion.LECTURA, paciente)


@login_required
def vincular(request, pk):
    """Suma otro Tutor a los que responden por el Paciente.

    En página aparte y no en la ficha porque el desplegable enseña el fichero de
    Tutores entero, y eso es una lectura del conjunto que no tiene por qué
    quedar anotada cada vez que alguien abre una ficha.
    """
    paciente = get_object_or_404(Paciente, pk=pk)
    formulario = VinculoForm(request.POST or None, clinica=request.user.clinic, paciente=paciente)
    if request.method == "POST" and formulario.is_valid():
        vinculo = formulario.guardar()
        anotar(request.user, Accion.MODIFICACION, paciente)
        anotar(request.user, Accion.MODIFICACION, vinculo.tutor)
        return redirect("patients:ficha", pk=paciente.pk)
    respuesta = render(
        request,
        "patients/vincular.html",
        {"formulario": formulario, "paciente": paciente},
    )
    # La página enseña la ficha del Paciente y, en el desplegable, el nombre de
    # todos los Tutores de la Clínica: el conjunto.
    return anotando(respuesta, request.user, Accion.LECTURA, paciente, Tutor)


@login_required
@require_POST
def responsable(request, pk, vinculo):
    """Pasa el cargo de responsable a otro de los Tutores del Paciente.

    Solo por POST: cambia a quién se llama y a quién se cobra, y eso no puede
    pasar por seguir un enlace.
    """
    paciente = get_object_or_404(Paciente, pk=pk)
    vinculo = get_object_or_404(Vinculo, pk=vinculo, paciente=paciente)
    vinculo.hacer_responsable()
    anotar(request.user, Accion.MODIFICACION, paciente)
    anotar(request.user, Accion.MODIFICACION, vinculo.tutor)
    return redirect("patients:ficha", pk=paciente.pk)


@login_required
def traspasar(request, pk):
    """El Paciente cambia de manos: otro Tutor responde por él a partir de hoy.

    En página aparte de «Sumar un Tutor» porque no es sumar: alguien deja de
    responder por el animal el mismo día en que otro empieza, y las dos mitades
    van juntas. Y aparte de corregir la ficha porque la ficha no cambia — el
    animal es el mismo, con su Historia clínica entera.

    Consta como modificación de los dos Tutores y del Paciente: a quién se le
    dejó de cobrar y a quién se le empezó a cobrar es justo lo que habrá que
    poder demostrar si alguien reclama (ADR-0004).
    """
    paciente = get_object_or_404(Paciente, pk=pk)
    anterior = paciente.responsable
    formulario = TraspasoForm(request.POST or None, clinica=request.user.clinic, paciente=paciente)
    if request.method == "POST" and formulario.is_valid():
        vinculo = formulario.guardar()
        anotar(request.user, Accion.MODIFICACION, paciente)
        anotar(request.user, Accion.MODIFICACION, vinculo.tutor)
        if anterior:
            anotar(request.user, Accion.MODIFICACION, anterior)
        return redirect("patients:ficha", pk=paciente.pk)
    respuesta = render(
        request,
        "patients/traspaso.html",
        {"formulario": formulario, "paciente": paciente, "anterior": anterior},
    )
    # La página enseña la ficha del Paciente, el nombre de quien responde ahora
    # por él y, en el desplegable, el de todos los Tutores de la Clínica.
    objetos = [paciente, *([anterior] if anterior else []), Tutor]
    return anotando(respuesta, request.user, Accion.LECTURA, *objetos)


@login_required
def cerrar_vinculo(request, pk, vinculo):
    """Que un Tutor dejó de responder por el Paciente, con la fecha.

    Cerrar y no borrar: quién lo trajo antes y hasta cuándo se conserva entero,
    porque la Historia clínica es del animal pero quién lo traía cada vez es
    parte de ella (ADR-0001).

    El del responsable de un Paciente activo no se cierra aquí —dejaría una ficha
    que no dice a quién llamar—, y el formulario lo dice en la cara: esconder el
    enlace no basta para quien llega con la URL en la mano.
    """
    paciente = get_object_or_404(Paciente, pk=pk)
    vinculo = get_object_or_404(Vinculo, pk=vinculo, paciente=paciente, fecha_de_cierre=None)
    formulario = CierreDeVinculoForm(request.POST or None, vinculo=vinculo)
    if request.method == "POST" and formulario.is_valid():
        formulario.guardar()
        anotar(request.user, Accion.MODIFICACION, paciente)
        anotar(request.user, Accion.MODIFICACION, vinculo.tutor)
        return redirect("patients:ficha", pk=paciente.pk)
    respuesta = render(
        request,
        "patients/cerrar_vinculo.html",
        {"formulario": formulario, "paciente": paciente, "vinculo": vinculo},
    )
    # La página dice de qué animal y de qué persona se habla, con sus nombres.
    return anotando(respuesta, request.user, Accion.LECTURA, paciente, vinculo.tutor)


@login_required
def estado(request, pk):
    """Deja constancia de que el Paciente murió o dejó de venir.

    En página aparte de la ficha porque no es una corrección: el nombre estaba
    mal escrito y se arregla, pero el animal murió y eso se registra. Y porque
    la ficha de un fallecido ya no se corrige, así que este es el único cambio
    que le queda — incluido el de deshacerlo. Marcar por error al animal que no
    era es lo bastante fácil, y lo bastante grave, como para que volver atrás no
    dependa de tocar la base de datos a mano.

    El cambio es una modificación de la ficha y consta como tal (ADR-0004): a
    quién se dio por muerto, quién lo hizo y cuándo es justamente lo que habrá
    que poder demostrar si alguien reclama.
    """
    paciente = get_object_or_404(Paciente, pk=pk)
    formulario = EstadoDelPacienteForm(request.POST or None, paciente=paciente)
    if request.method == "POST" and formulario.is_valid():
        formulario.guardar()
        anotar(request.user, Accion.MODIFICACION, paciente)
        return redirect("patients:ficha", pk=paciente.pk)
    respuesta = render(
        request, "patients/estado.html", {"formulario": formulario, "paciente": paciente}
    )
    # La página dice de qué animal se habla, con su nombre y su estado de ahora.
    return anotando(respuesta, request.user, Accion.LECTURA, paciente)


@login_required
def razas(request):
    """Las razas que se le sugieren a una especie, para la lista del formulario.

    Es catálogo, no datos de nadie: no se anota. Existe para que elegir la
    especie cambie las sugerencias sin recargar la página; sin JavaScript la
    lista sigue llegando servida con el formulario, solo que la de la especie
    que ya tenía.
    """
    return render(request, "patients/_razas.html", {"razas": razas_de(request.GET.get("especie"))})

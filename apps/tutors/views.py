"""Listado, búsqueda y ficha de Tutor.

Ninguna de estas vistas filtra por Clínica: no hace falta. `Tutor.objects` ya
solo ve la Clínica activa, que el middleware resolvió a partir del Usuario. Un
Tutor de otra Clínica sencillamente no existe para esta consulta, y por eso
pedirlo por su identificador da 404 y no 403: la existencia ya es información.

Los datos de un Tutor son datos personales, así que servirlos deja constancia
en el Registro de acceso (ADR-0004). De eso se encarga `deja_constancia`, que
anota lo que la vista sirvió y solo si lo sirvió.

La ficha completa del Tutor es del ticket 05; esto es lo mínimo con lo que se
puede demostrar el aislamiento por HTTP.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from apps.audit.models import Accion
from apps.audit.registro import deja_constancia
from apps.tutors.models import Tutor


@login_required
@deja_constancia(Accion.LECTURA, sobre=Tutor, identificado_por=None)
def lista(request):
    buscado = request.GET.get("q", "").strip()
    tutores = Tutor.objects.all()
    if buscado:
        tutores = tutores.filter(nombre__icontains=buscado)
    return render(request, "tutors/lista.html", {"tutores": tutores, "buscado": buscado})


@login_required
@deja_constancia(Accion.LECTURA, sobre=Tutor)
def ficha(request, pk):
    return render(request, "tutors/ficha.html", {"tutor": get_object_or_404(Tutor, pk=pk)})

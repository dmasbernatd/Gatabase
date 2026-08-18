"""Listado, búsqueda y ficha de Tutor.

Ninguna de estas vistas filtra por Clínica: no hace falta. `Tutor.objects` ya
solo ve la Clínica activa, que el middleware resolvió a partir del Usuario. Un
Tutor de otra Clínica sencillamente no existe para esta consulta, y por eso
pedirlo por su identificador da 404 y no 403: la existencia ya es información.

La ficha completa del Tutor es del ticket 05; esto es lo mínimo con lo que se
puede demostrar el aislamiento por HTTP.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from apps.tutors.models import Tutor


@login_required
def lista(request):
    buscado = request.GET.get("q", "").strip()
    tutores = Tutor.objects.all()
    if buscado:
        tutores = tutores.filter(nombre__icontains=buscado)
    return render(request, "tutors/lista.html", {"tutores": tutores, "buscado": buscado})


@login_required
def ficha(request, pk):
    return render(request, "tutors/ficha.html", {"tutor": get_object_or_404(Tutor, pk=pk)})

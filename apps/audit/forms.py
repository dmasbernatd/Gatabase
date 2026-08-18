"""Filtro con el que el admin consulta el Registro de acceso.

Las tres preguntas que se le hacen a un registro de auditoría son quién, qué y
cuándo, y el filtro no ofrece nada más. Vive aparte de la vista porque el "qué"
y el "cuándo" tienen su propia lógica — el rango son días de la clínica, no
instantes en UTC — y esa lógica se prueba sola.
"""

import datetime as dt

from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.audit.models import RegistroDeAcceso, nombre_del_tipo


def comienzo_del_dia(fecha):
    """El instante en que empieza ese día en la clínica, en el que se compara.

    La base de datos guarda UTC, pero quien pide "el 20 de junio" pide el 20 de
    junio en Chile: convertir es lo que hace que un acceso de las 23:30 no se
    cuente como del día siguiente.
    """
    return timezone.make_aware(dt.datetime.combine(fecha, dt.time.min))


class FiltroDelRegistro(forms.Form):
    """Quién, qué y cuándo. Todo opcional: sin nada marcado se ve todo."""

    usuario = forms.ModelChoiceField(
        queryset=get_user_model().objects.none(),
        required=False,
        label=_("Usuario"),
        empty_label=_("Cualquier Usuario"),
    )
    tipo_de_objeto = forms.ChoiceField(required=False, label=_("Tipo de objeto"), choices=[])
    identificador = forms.CharField(required=False, label=_("Identificador"), max_length=64)
    desde = forms.DateField(
        required=False, label=_("Desde"), widget=forms.DateInput(attrs={"type": "date"})
    )
    hasta = forms.DateField(
        required=False, label=_("Hasta"), widget=forms.DateInput(attrs={"type": "date"})
    )

    def __init__(self, *args, clinica, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["usuario"].queryset = get_user_model().objects.filter(clinic=clinica)
        self.fields["tipo_de_objeto"].choices = self._tipos_registrados()

    def _tipos_registrados(self):
        """Solo los tipos de los que hay algo anotado: ofrecer más es prometer
        una búsqueda que no puede devolver nada."""
        tipos = (
            RegistroDeAcceso.objects.order_by()
            .values_list("tipo_de_objeto", flat=True)
            .distinct()
        )
        return [("", _("Cualquier objeto"))] + [(tipo, nombre_del_tipo(tipo)) for tipo in tipos]

    def filtrar(self, anotaciones):
        """Las anotaciones que cumplen lo que se haya rellenado del filtro.

        Un filtro que no se entiende — una fecha imposible, un tipo de objeto
        que no existe — no devuelve nada. Devolver el Registro entero sería lo
        cómodo, y también la forma de que alguien se lleve una lista completa de
        accesos creyendo que pidió una en concreto.
        """
        if not self.is_bound:
            return anotaciones
        if not self.is_valid():
            return anotaciones.none()
        elegido = self.cleaned_data
        if elegido["usuario"]:
            anotaciones = anotaciones.filter(usuario=elegido["usuario"])
        if elegido["tipo_de_objeto"]:
            anotaciones = anotaciones.filter(tipo_de_objeto=elegido["tipo_de_objeto"])
        if elegido["identificador"]:
            anotaciones = anotaciones.filter(identificador=elegido["identificador"])
        if elegido["desde"]:
            anotaciones = anotaciones.filter(momento__gte=comienzo_del_dia(elegido["desde"]))
        if elegido["hasta"]:
            # El día `hasta` entra entero: se compara con el comienzo del
            # siguiente, no con su medianoche.
            siguiente = elegido["hasta"] + dt.timedelta(days=1)
            anotaciones = anotaciones.filter(momento__lt=comienzo_del_dia(siguiente))
        return anotaciones

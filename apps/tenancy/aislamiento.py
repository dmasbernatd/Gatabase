"""Aislamiento por Clínica: la clave ajena `clinic` y el manager que filtra (ADR-0003).

Todo modelo de dominio hereda de `ModeloDeLaClinica`. Con eso obtiene dos cosas
que no hay que acordarse de pedir: la clave ajena `clinic` y un manager por
defecto que solo devuelve objetos de la Clínica activa. La Clínica activa la fija
el middleware a partir del Usuario autenticado, y fuera de una petición —
comandos, tareas, tests — se fija a mano con `activar_clinica`.

Sin Clínica activa, `objects` no devuelve nada. Un olvido produce una página
vacía, nunca datos de otra Clínica. Cuando de verdad hace falta cruzar la
frontera — un comando de alta, una exportación, este mismo módulo — se usa el
manager `de_todas_las_clinicas`, cuyo nombre es lo bastante feo como para que
salte a la vista en una revisión.
"""

from contextlib import contextmanager
from contextvars import ContextVar

from django import forms
from django.db import models
from django.utils.translation import gettext_lazy as _

# En una `ContextVar` y no en el `request`: así el manager la alcanza desde el
# fondo del ORM sin que cada capa intermedia tenga que ir pasándola de la mano.
_clinica_activa = ContextVar("clinica_activa", default=None)


def clinica_activa():
    """La Clínica en cuyo contexto se está trabajando, o `None` si no hay ninguna."""
    return _clinica_activa.get()


@contextmanager
def activar_clinica(clinica):
    """Trabaja dentro de una Clínica fuera de una petición HTTP.

    Lo usan los comandos de gestión, las tareas y los tests. Al salir deja el
    contexto como estaba, aunque el bloque termine con una excepción.
    """
    testigo = _clinica_activa.set(clinica)
    try:
        yield clinica
    finally:
        _clinica_activa.reset(testigo)


class GestorDeLaClinica(models.Manager):
    """Manager por defecto: solo ve la Clínica activa."""

    def get_queryset(self):
        clinica = clinica_activa()
        queryset = super().get_queryset()
        if clinica is None:
            return queryset.none()
        return queryset.filter(clinic=clinica)


class ModeloDeLaClinica(models.Model):
    """Base de todo modelo de dominio: lleva `clinic` y filtra por ella.

    El primer manager declarado es el que Django toma como `_default_manager`,
    y es el que usan las relaciones inversas y `get_object_or_404`. Que sea el
    filtrado es justamente la garantía de ADR-0003.
    """

    clinic = models.ForeignKey(
        "tenancy.Clinica",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s",
        verbose_name=_("Clínica"),
    )

    objects = GestorDeLaClinica()
    de_todas_las_clinicas = models.Manager()

    class Meta:
        abstract = True


class FormularioDeLaClinica(forms.ModelForm):
    """Base de todo formulario de un modelo de dominio: la Clínica la pone él.

    Va aquí, al lado de `ModeloDeLaClinica`, porque es la misma frontera vista
    desde el otro extremo: el modelo garantiza que nadie lea fuera de su
    Clínica, y esto que nadie escriba fuera de la suya. La Clínica se recibe de
    quien está rellenando el formulario y no como un campo más, porque un
    `<select>` de Clínicas sería una frontera dibujada en el navegador, y las
    fronteras no se dibujan ahí (ADR-0003).
    """

    def __init__(self, *args, clinica, **kwargs):
        super().__init__(*args, **kwargs)
        self.clinica = clinica

    def save(self, commit=True):
        objeto = super().save(commit=False)
        objeto.clinic = self.clinica
        if commit:
            objeto.save()
            self.save_m2m()
        return objeto

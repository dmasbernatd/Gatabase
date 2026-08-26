"""La Importación: qué planilla subió quién, cuándo y con qué resultado.

Existe por una casilla del ticket 17 —«la importación queda en el Registro de
acceso, con quién importó, cuándo y cuántas filas»— que el Registro por sí solo
no puede cumplir: una anotación guarda el tipo del objeto accedido y su
identificador, y «ciento veinte filas» no es ni una cosa ni la otra. Así que el
hecho se guarda aquí, con sus cuentas, y el Registro anota una creación que
apunta a él (ADR-0004).

**No se anota una creación por Tutor importado**, y es la decisión de este
módulo. Serían tres mil anotaciones de un solo gesto, que enterrarían en ruido
justo la tabla que tiene que valer como prueba; y no harían falta, porque el
gesto fue uno: un admin subió una planilla a una hora. Lo que el Registro tiene
que poder responder —quién metió estos datos y cuándo— lo responde igual, y con
una fila en vez de con tres mil.

**No se guarda la planilla.** El derecho de supresión del Tutor (ticket 20) se
cumple vaciando `DATOS_PERSONALES` de la tabla del Tutor «sin tocar ninguna
otra», y una copia de su nombre y su RUT aquí dentro sobreviviría a eso en
silencio. De la planilla queda su nombre de archivo, que no es dato de nadie.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.tenancy.aislamiento import ModeloDeLaClinica


class LoQueSeImporta(models.TextChoices):
    """Qué traía la planilla. El ticket 18 añade los Pacientes."""

    TUTORES = "tutores", _("Tutores")


class Importacion(ModeloDeLaClinica):
    """Una planilla subida y confirmada, con lo que salió de ella."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        # PROTECT y no CASCADE, por lo mismo que en el Registro de acceso: una
        # importación sin autor no responde a la pregunta para la que existe.
        on_delete=models.PROTECT,
        related_name="importaciones",
        verbose_name=_("Usuario"),
    )
    que_se_importo = models.CharField(
        _("qué se importó"), max_length=20, choices=LoQueSeImporta.choices
    )
    # El nombre con que llegó el archivo, para reconocerlo entre las tandas de
    # una migración. No es el archivo: ver el docstring del módulo.
    planilla = models.CharField(_("planilla"), max_length=255)
    momento = models.DateTimeField(_("momento"), default=timezone.now)
    filas_leidas = models.PositiveIntegerField(_("filas leídas"), default=0)
    filas_creadas = models.PositiveIntegerField(_("filas creadas"), default=0)
    filas_repetidas = models.PositiveIntegerField(_("filas repetidas"), default=0)
    filas_con_error = models.PositiveIntegerField(_("filas con error"), default=0)

    class Meta:
        verbose_name = _("Importación")
        verbose_name_plural = _("Importaciones")
        ordering = ["-momento", "-pk"]
        indexes = [
            models.Index(fields=["clinic", "-momento"], name="importacion_por_fecha"),
        ]

    def __str__(self):
        return _("%(que)s desde %(planilla)s: %(creadas)s de %(leidas)s filas") % {
            "que": self.get_que_se_importo_display(),
            "planilla": self.planilla,
            "creadas": self.filas_creadas,
            "leidas": self.filas_leidas,
        }

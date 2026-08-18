"""Registro de acceso: qué Usuario vio o modificó qué dato, y cuándo (ADR-0004).

Es la evidencia exigible ante la Ley 21.719, y por eso una anotación no se
parece a ninguna otra fila del sistema: nace y no cambia nunca más. La base de
datos lo impone — ni `UPDATE` ni `DELETE`, ver la migración 0002 —, así que este
modelo no tiene formulario de edición ni podría tenerlo: lo único que se hace
con una anotación, aparte de escribirla, es leerla.

`audit` no importa de ninguna app de dominio: el tipo del objeto servido se
guarda como texto (`tutors.Tutor`), no como clave ajena. Así el Registro puede
anotar accesos a Pacientes, Adjuntos o Conversaciones sin conocer esas apps, y
sobrevive a que un modelo se renombre o desaparezca. De `tenancy` sí depende —
Clínica y Usuario —, que es quién accede y dentro de qué frontera.
"""

from django.apps import apps as registro_de_apps
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.tenancy.aislamiento import ModeloDeLaClinica

# Lo que se sirvió fue el conjunto — un listado, una búsqueda — y no un objeto
# concreto. Se distingue de un identificador cualquiera por estar vacío.
EL_CONJUNTO = ""


def nombre_del_tipo(etiqueta):
    """Cómo se llama en el dominio el tipo guardado como texto (`tutors.Tutor`).

    El tipo puede apuntar a un modelo que ya no existe: entonces se devuelve tal
    cual, que sigue siendo evidencia de a qué se accedió.
    """
    try:
        return registro_de_apps.get_model(etiqueta)._meta.verbose_name
    except (LookupError, ValueError):
        return etiqueta


class Accion(models.TextChoices):
    """Lo que el Usuario hizo con el dato."""

    LECTURA = "lectura", _("lectura")
    CREACION = "creacion", _("creación")
    MODIFICACION = "modificacion", _("modificación")


class RegistroDeAcceso(ModeloDeLaClinica):
    """Anotación inalterable de un acceso a datos personales.

    Se escribe desde las vistas, en el momento de servir el dato: una lectura no
    dispara ninguna señal de modelo, así que ninguna librería basada en señales
    puede capturarla (ADR-0004).
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        # PROTECT y no CASCADE: una anotación sin autor no es evidencia de
        # nada. Un Usuario que se va se desactiva, no se borra.
        on_delete=models.PROTECT,
        related_name="accesos",
        verbose_name=_("Usuario"),
    )
    tipo_de_objeto = models.CharField(_("tipo de objeto"), max_length=100)
    identificador = models.CharField(_("identificador"), max_length=64, blank=True)
    accion = models.CharField(_("acción"), max_length=20, choices=Accion.choices)
    # `default` y no `auto_now_add`: quien escribe la anotación es siempre
    # `registro.anotar`, que nunca pasa el momento, y así los tests pueden
    # componer un Registro con fechas repartidas sin tocar el reloj.
    momento = models.DateTimeField(_("momento"), default=timezone.now)

    class Meta:
        verbose_name = _("Registro de acceso")
        verbose_name_plural = _("Registros de acceso")
        # Por `-pk` además de por `-momento`: dos accesos de la misma petición
        # comparten instante, y el orden debe ser estable entre páginas.
        ordering = ["-momento", "-pk"]
        indexes = [
            models.Index(fields=["clinic", "-momento"], name="acceso_por_clinica_y_fecha"),
            models.Index(fields=["tipo_de_objeto", "identificador"], name="acceso_por_objeto"),
        ]

    def __str__(self):
        return f"{self.usuario} — {self.get_accion_display()} — {self.objeto}"

    @property
    def tipo(self):
        """El tipo de lo accedido, con el vocabulario del dominio."""
        return nombre_del_tipo(self.tipo_de_objeto)

    @property
    def objeto(self):
        """Lo accedido: su tipo y cuál, si fue uno concreto."""
        return f"{self.tipo} {self.identificador}".strip()

"""Consulta: el encuentro clínico, y la pieza de la que cuelga la Historia clínica.

Aquí vive lo que el veterinario escribe mientras atiende. Es un documento con
valor legal y probatorio, y de eso salen las dos decisiones que mandan sobre
todo lo demás:

Una, la Consulta **no se borra** (`spec.md`, H2). No hay vista de borrado ni
podría haberla: el Paciente la protege (`PROTECT`), así que borrar la ficha de
un animal con Consultas falla en la base de datos, y tiene que fallar. Lo que se
hace con lo que sobra es enmendarlo, no quitarlo.

Dos, tiene dos fases (ADR-0002): **abierta**, que su autor escribe cuantas veces
quiera durante la atención, y **cerrada**, que ya no se toca. El cierre es un
acto explícito distinto del guardado y llega en el ticket 02; aquí la Consulta
nace abierta y se queda así.

Quién atendió y en qué Sede son datos de la Consulta y no de la petición que la
creó: la pregunta que viene después de leer una ficha es a quién preguntarle, y
seis meses más tarde ni la sesión ni las Sedes del Usuario dicen ya dónde estaba
esa tarde. Por eso la Sede se copia al abrir y no se deduce luego.

`records` **no importa** de `scheduling` (`CLAUDE.md`): la Consulta no sabe nada
de Citas, y es la Cita la que podrá apuntar a la Consulta que generó. Sin esa
regla, atender a un espontáneo —que es la mitad de lo que entra por la puerta—
obligaría a inventarle una reserva que nadie hizo.

Lo que la Consulta **no** lleva: ningún dato personal de su Tutor, por lo mismo
que no lo lleva el Paciente (ADR-0004). El titular de la Historia clínica es el
animal, y quién respondía por él cada vez se lee en sus Vínculos.
"""

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.tenancy.aislamiento import ModeloDeLaClinica


class Consulta(ModeloDeLaClinica):
    """Un encuentro clínico concreto entre un Paciente y un veterinario."""

    # PROTECT en las tres claves, y por el mismo motivo en las tres: una
    # Consulta sin Paciente, sin autor o sin Sede no es un documento clínico,
    # es un papel suelto. Un Paciente no se borra nunca (`CONTEXT.md`) y un
    # Usuario que se va se desactiva (ADR-0004); esto es lo que lo impone en la
    # base de datos en vez de confiar en que nadie lo intente.
    paciente = models.ForeignKey(
        "patients.Paciente",
        on_delete=models.PROTECT,
        related_name="consultas",
        verbose_name=_("Paciente"),
    )
    veterinario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="consultas",
        verbose_name=_("veterinario"),
    )
    sede = models.ForeignKey(
        "tenancy.Sede",
        on_delete=models.PROTECT,
        related_name="consultas",
        verbose_name=_("Sede"),
    )

    # Cuándo se abrió. En UTC en la base de datos y presentada en
    # `America/Santiago` (`CLAUDE.md`), como toda fecha del sistema.
    #
    # `default` y no `auto_now_add`, como en el Registro de acceso: así los
    # datos mock del ticket 11 pueden componer una Historia clínica repartida a
    # lo largo de dos años sin tocar el reloj del proceso.
    abierta = models.DateTimeField(_("abierta"), default=timezone.now)

    # El motivo va en palabras del Tutor y es lo primero que se lee seis meses
    # después: «cojea de la pata de atrás», no «claudicación posterior». Es el
    # único de los campos de texto que no es del método SOAP.
    motivo = models.TextField(_("motivo de la Consulta"), blank=True)

    # El SOAP, en cuatro campos y no en uno: separarlos es lo que permite
    # encontrar después lo que se busca, y es como ya piensa quien atiende.
    # Semiestructurado a propósito (`spec.md`): texto libre dentro de cada
    # sección, porque una plantilla por tipo de atención se queda corta el día
    # que entra algo que no estaba previsto.
    subjetivo = models.TextField(_("subjetivo"), blank=True)
    objetivo = models.TextField(_("objetivo"), blank=True)
    evaluacion = models.TextField(_("evaluación"), blank=True)
    plan = models.TextField(_("plan"), blank=True)

    diagnostico = models.TextField(_("diagnóstico"), blank=True)
    tratamiento_indicado = models.TextField(_("tratamiento indicado"), blank=True)

    # El folio de la receta que el veterinario emitió en la plataforma del SAG.
    # Texto libre y sin validar contra nada, a propósito: este sistema **no
    # emite** recetas de antimicrobianos —desde el 1 de enero de 2024 eso lo
    # hace el SAG con el veterinario inscrito allí— y no consta que haya
    # integración disponible. Lo que se guarda es la referencia, para que la
    # ficha y la receta cuenten lo mismo.
    folio_de_la_receta_del_sag = models.CharField(
        _("folio de la receta del SAG"), max_length=60, blank=True
    )

    # Todos los campos de texto admiten hueco, y es a propósito: una Consulta se
    # abre al empezar a atender, cuando todavía no se sabe nada. Exigir aquí lo
    # que no se sabe aún obligaría a escribir un punto para poder guardar, y un
    # punto no se distingue de un dato que nadie tomó. Lo que la Consulta no
    # puede no tener es a quién, quién y dónde, y eso son las tres claves.

    class Meta:
        verbose_name = _("Consulta")
        verbose_name_plural = _("Consultas")
        # La más reciente primero: es el orden en que se lee una Historia
        # clínica —qué le pasó la última vez— y no el orden en que se escribió.
        # Por `-pk` además de por `-abierta` porque dos Consultas del mismo
        # Paciente pueden abrirse el mismo segundo en los datos mock, y un orden
        # que empata deja la paginación bailando.
        ordering = ["-abierta", "-pk"]
        indexes = [
            # Por aquí se lee: la Historia clínica de un Paciente, de la más
            # reciente a la más vieja (ticket 04).
            models.Index(fields=["clinic", "paciente", "-abierta"], name="consulta_del_paciente"),
        ]

    def __str__(self):
        """Qué Consulta es, dicho como se dice en la clínica: de quién y de cuándo.

        Sin el motivo, aunque sea lo que la identifica para quien atendió: esto
        viaja al Registro de acceso y a los mensajes del sistema, y el motivo es
        información clínica del Paciente.
        """
        return _("Consulta de %(paciente)s del %(fecha)s") % {
            "paciente": self.paciente,
            "fecha": timezone.localtime(self.abierta).strftime("%d-%m-%Y"),
        }

    def get_absolute_url(self):
        return reverse("records:consulta", args=[self.pk])

    @property
    def esta_abierta(self):
        """Si todavía se está escribiendo.

        En el ticket 01 lo está siempre: el cierre llega en el 02, y hasta
        entonces esto es el sitio por donde entrará. Se pregunta y no se
        comprueba a mano en cada vista para que el día del cierre haya un solo
        sitio que cambiar.
        """
        return True

    def la_escribe(self, usuario):
        """Si ese Usuario puede escribir en esta Consulta ahora mismo.

        Tres condiciones, y las tres por el mismo motivo —la Consulta la firma
        quien atendió—: que esté abierta, que el Usuario sea su autor y que sea
        veterinario. Que sea su autor y no cualquier veterinario de la Clínica
        porque dos manos escribiendo el mismo documento clínico dejan uno que no
        dice quién observó qué; otro veterinario la lee entera, y si tiene algo
        que añadir lo añade como Enmienda suya (ticket 03).

        Vive en el modelo y no en la vista porque es la regla de ADR-0002, y la
        plantilla que esconde el botón no es donde se cumple una regla.
        """
        return self.esta_abierta and usuario.es_veterinario and usuario == self.veterinario

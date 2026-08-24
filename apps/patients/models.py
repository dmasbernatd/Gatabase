"""Paciente: el animal atendido, y el único titular de una Historia clínica.

Aquí viven **solo** sus datos: cómo se llama, qué es y cómo se le reconoce.
Ningún dato personal de su Tutor baja hasta esta tabla, y no es una cuestión de
orden (ADR-0004): el Tutor puede exigir la supresión de sus datos personales
mientras la Historia clínica —de la que es titular el animal, no él— tiene que
conservarse. Si el nombre o el teléfono del Tutor estuvieran copiados en el
Paciente, anonimizar (ticket 20) o bien dejaría el dato personal en pie o bien se
llevaría por delante la ficha clínica.

Quién responde por el Paciente es un hecho aparte, con tabla propia y vida
propia: el Vínculo (`apps.tutors.models`). Un animal cambia de Tutor y sigue
siendo el mismo Paciente con la misma Historia.

El microchip y el estado de identificación llegan en el ticket 08, y los estados
`activo` / `inactivo` / `fallecido` en el 09.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.patients.catalogo import Especie, es_del_catalogo
from apps.tenancy.aislamiento import ModeloDeLaClinica


class Sexo(models.TextChoices):
    """El sexo del Paciente. Que falte es una respuesta: un animal recogido en la
    calle llega sin que nadie lo haya mirado todavía, y obligar a elegir aquí
    sería obligar a inventar."""

    MACHO = "macho", _("macho")
    HEMBRA = "hembra", _("hembra")


class Paciente(ModeloDeLaClinica):
    """El animal atendido por la clínica."""

    # Como con el Tutor, solo lo imprescindible es obligatorio: el nombre con el
    # que se le llama y qué es. La especie porque de ella dependen protocolos y
    # formularios; lo demás se completa cuando se sepa.
    nombre = models.CharField(_("nombre"), max_length=200)
    especie = models.CharField(_("especie"), max_length=20, choices=Especie)
    # Texto y no clave ajena a un catálogo en base de datos: el catálogo es
    # cerrado para la especie y abierto para la raza (`catalogo.py`), así que lo
    # que aquí se guarda es o una entrada del catálogo con su ortografía o la
    # raza que recepción escribió porque no estaba en la lista.
    raza = models.CharField(_("raza"), max_length=120, blank=True)
    sexo = models.CharField(_("sexo"), max_length=10, choices=Sexo, blank=True)
    fecha_de_nacimiento = models.DateField(_("fecha de nacimiento"), null=True, blank=True)
    color = models.CharField(_("color"), max_length=80, blank=True)
    observaciones = models.TextField(_("observaciones"), blank=True)

    class Meta:
        verbose_name = _("Paciente")
        verbose_name_plural = _("Pacientes")
        ordering = ["nombre", "pk"]
        indexes = [models.Index(fields=["clinic", "nombre"], name="paciente_por_nombre")]

    def __str__(self):
        return self.nombre

    @property
    def raza_del_catalogo(self):
        """Si la raza salió del catálogo de su especie o la escribió recepción.

        Es lo que separa una raza que cuenta para las estadísticas de una
        respuesta libre, y se pregunta en vez de guardarse: el día que una raza
        entre en el catálogo, las fichas que ya la tenían escrita cuentan.
        """
        return es_del_catalogo(self.especie, self.raza)

    @property
    def quienes_responden(self):
        """Los Vínculos de este Paciente, con el responsable primero.

        Se pide por el manager sin filtro a propósito, y aquí no abre ninguna
        puerta: los Vínculos de un Paciente son de su Clínica por construcción
        —los escribe `Tutor.se_hace_cargo_de`, que toma la Clínica del Tutor—, y
        al Paciente ya se llegó por el manager filtrado. Volver a filtrar por la
        Clínica activa solo tendría un efecto: que la ficha dejara de saber
        quién responde por el animal fuera de una petición HTTP, que es donde
        van a trabajar el importador del 18 y los datos mock del 16.
        """
        return self.vinculos(manager="de_todas_las_clinicas").select_related("tutor")

    @property
    def vinculo_responsable(self):
        """El Vínculo con el Tutor que responde por él, si lo hay.

        Puede no haberlo mientras dure un cambio de Tutor (ticket 10), y por eso
        la ficha pregunta en vez de dar por hecho.
        """
        return self.quienes_responden.filter(responsable=True).first()

    @property
    def responsable(self):
        """El Tutor que responde por él ante la clínica y ante la ley."""
        vinculo = self.vinculo_responsable
        return vinculo.tutor if vinculo else None

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

Cómo se identifica al animal —el microchip y el estado de identificación— vive
también aquí, y son dos campos y no uno a propósito: ver más abajo. Los estados
`activo` / `inactivo` / `fallecido` llegan en el ticket 09.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.patients.campos import CampoDeMicrochip
from apps.patients.catalogo import Especie, es_del_catalogo, la_ley_exige_identificar
from apps.patients.microchip import formateado
from apps.tenancy.aislamiento import ModeloDeLaClinica


class Sexo(models.TextChoices):
    """El sexo del Paciente. Que falte es una respuesta: un animal recogido en la
    calle llega sin que nadie lo haya mirado todavía, y obligar a elegir aquí
    sería obligar a inventar."""

    MACHO = "macho", _("macho")
    HEMBRA = "hembra", _("hembra")


class EstadoDeIdentificacion(models.TextChoices):
    """En qué punto de la Ley 21.020 está el Paciente.

    Es un campo propio y **no** se deduce del microchip, que es lo que este
    catálogo viene a decir: tener el número apuntado no es estar inscrito. La ley
    se cumple con las dos cosas —el chip puesto y el animal en el Registro
    Nacional—, y el hueco entre una y otra es justamente lo que recepción tiene
    que poder decirle al Tutor. Un animal puede además llevar el chip de otra
    clínica sin que su Tutor traiga el número, y ahí el estado es lo único que
    se sabe.

    Falta a propósito un cuarto valor: que la casilla esté en blanco significa
    que nadie lo ha preguntado todavía, y eso **no** es `sin chip`. Es el mismo
    reparto que el Estado sanitario de `CONTEXT.md` —`desconocido` no es
    `vencido`—, y por el mismo motivo: lo que nadie ha mirado no puede
    decírsele a un Tutor como si se hubiera comprobado.
    """

    SIN_CHIP = "sin_chip", _("sin chip")
    IMPLANTADO = "implantado", _("chip implantado")
    INSCRITO = "inscrito", _("inscrito en el Registro Nacional")


# Lo que la ficha enseña cuando nadie ha preguntado todavía. Se dice con todas
# sus letras y no con un guion, porque un hueco en esta casilla se lee como un
# «no tiene» y aquí eso sería afirmar algo que nadie comprobó.
SIN_PREGUNTAR = _("todavía no se ha preguntado")


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

    # El chip es opcional: llega a la consulta un animal sin chip, y exigirlo en
    # el mostrador sería negarle la atención. Cuando está, es único dentro de la
    # Clínica —nunca a nivel global, aunque el número identifique al animal en
    # todo Chile (ADR-0001)—, y por eso el hueco se guarda como cadena vacía y la
    # restricción lo deja fuera: dos Pacientes sin chip no son el mismo animal.
    microchip = CampoDeMicrochip(_("microchip"), max_length=15, blank=True)
    estado_de_identificacion = models.CharField(
        _("estado de identificación"),
        max_length=20,
        choices=EstadoDeIdentificacion,
        blank=True,
    )

    class Meta:
        verbose_name = _("Paciente")
        verbose_name_plural = _("Pacientes")
        ordering = ["nombre", "pk"]
        indexes = [
            models.Index(fields=["clinic", "nombre"], name="paciente_por_nombre"),
            # El chip es una forma de encontrar al animal, y por él se busca
            # entero: es lo que trae el lector de un tirón (ticket 11).
            models.Index(fields=["clinic", "microchip"], name="paciente_por_microchip"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["clinic", "microchip"],
                condition=~models.Q(microchip=""),
                name="microchip_unico_dentro_de_la_clinica",
            )
        ]

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

    @property
    def microchip_como_se_dicta(self):
        """El chip en grupos de tres: «900 123 456 789 012». Vacío si no tiene."""
        return formateado(self.microchip)

    @property
    def identificacion_a_la_vista(self):
        """El estado de identificación tal como se le dice al Tutor.

        Existe porque el hueco tiene que decir algo: `get_..._display` devuelve
        la cadena vacía cuando nadie ha preguntado todavía, y una casilla en
        blanco en la ficha se lee como un «no tiene chip» que nadie comprobó.
        """
        return self.get_estado_de_identificacion_display() or SIN_PREGUNTAR

    @property
    def lo_que_le_falta_a_la_ley(self):
        """Qué le falta al Tutor para cumplir la Ley 21.020, o `None` si nada.

        Se pregunta y no se guarda, como `raza_del_catalogo`: es una lectura del
        estado de ahora mismo, y guardarla sería un segundo sitio donde vive la
        misma verdad.

        Depende de la especie porque la ley depende de la especie: obliga con
        perros y gatos, y reclamarle a quien trae una iguana que la inscriba
        sería dar un consejo falso desde el mostrador.
        """
        if not la_ley_exige_identificar(self.especie):
            return None
        if self.estado_de_identificacion == EstadoDeIdentificacion.INSCRITO:
            return None
        if self.estado_de_identificacion == EstadoDeIdentificacion.IMPLANTADO:
            return _("Falta inscribirlo en el Registro Nacional de Mascotas.")
        if self.estado_de_identificacion == EstadoDeIdentificacion.SIN_CHIP:
            return _("Falta implantarle el chip e inscribirlo en el Registro Nacional.")
        return _("Falta preguntar si está identificado e inscrito.")

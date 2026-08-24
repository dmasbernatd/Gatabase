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
también aquí, y son dos campos y no uno a propósito: ver más abajo. En qué
situación está ante la clínica —`activo`, `inactivo` o `fallecido`— lo decide
`estados.py`, que es también quien sabe qué enseña una lista por defecto.
"""

from django.db import models
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _

from apps.patients.campos import CampoDeMicrochip
from apps.patients.catalogo import Especie, es_del_catalogo, la_ley_exige_identificar
from apps.patients.estados import POR_DEFECTO, EstadoDelPaciente
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

    # En qué situación está ante la clínica (`estados.py`). No tiene hueco: un
    # Paciente se registra porque está delante del mostrador, así que nace
    # activo y deja de estarlo cuando alguien lo diga.
    estado = models.CharField(
        _("estado"), max_length=20, choices=EstadoDelPaciente, default=POR_DEFECTO
    )
    # La fecha es opcional aunque el estado sea `fallecido`: el Tutor avisa a
    # veces meses después y no siempre recuerda el día, y exigirla ahí sería
    # obligar a inventarse una. Lo que **no** puede pasar es lo contrario —una
    # fecha de muerte en un animal que no consta muerto—, y eso no depende de
    # que nadie se acuerde: lo rechaza la base de datos, más abajo.
    fecha_de_fallecimiento = models.DateField(
        _("fecha de fallecimiento"), null=True, blank=True
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
            ),
            # La única combinación imposible de las dos casillas del estado, y
            # solo esa: una fecha de fallecimiento en un Paciente que no consta
            # fallecido. Sale de corregir una y olvidar la otra —de marcar por
            # error a quien no era y volver atrás—, y dejaría una ficha que dice
            # dos cosas a la vez. Al revés sí se puede: un fallecido sin fecha es
            # lo corriente cuando el Tutor avisa tarde.
            models.CheckConstraint(
                condition=models.Q(fecha_de_fallecimiento__isnull=True)
                | models.Q(estado=EstadoDelPaciente.FALLECIDO),
                name="solo_un_paciente_fallecido_tiene_fecha_de_fallecimiento",
            ),
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
        """Los Vínculos **abiertos** de este Paciente, con el responsable primero.

        En presente: quién responde por él ahora. Los que se cerraron cuando el
        animal cambió de manos están en `quienes_respondieron`, y siguen ahí
        enteros — un Vínculo no se borra nunca.

        Se pide por el manager sin filtro a propósito, y aquí no abre ninguna
        puerta: los Vínculos de un Paciente son de su Clínica por construcción
        —los escribe `Tutor.se_hace_cargo_de`, que toma la Clínica del Tutor—, y
        al Paciente ya se llegó por el manager filtrado. Volver a filtrar por la
        Clínica activa solo tendría un efecto: que la ficha dejara de saber
        quién responde por el animal fuera de una petición HTTP, que es donde
        van a trabajar el importador del 18 y los datos mock del 16.
        """
        return (
            self.vinculos(manager="de_todas_las_clinicas")
            .filter(fecha_de_cierre__isnull=True)
            .select_related("tutor")
        )

    @property
    def quienes_respondieron(self):
        """Los Vínculos ya cerrados, el último cambio de manos primero.

        Es de quién fue el animal antes, y hasta cuándo. Hace falta después de
        todo: el Tutor de antes llama preguntando por lo que se le hizo, o hay
        que saber a quién se le cobró una Consulta de hace dos años. La Historia
        clínica es del animal (ADR-0001), pero quién lo trajo cada vez es parte
        de ella.
        """
        return (
            self.vinculos(manager="de_todas_las_clinicas")
            .filter(fecha_de_cierre__isnull=False)
            .select_related("tutor")
            .order_by("-fecha_de_cierre", "-pk")
        )

    @property
    def vinculo_responsable(self):
        """El Vínculo con el Tutor que responde por él, si lo hay.

        Un Paciente activo siempre tiene uno (`necesita_responsable`); uno
        inactivo o fallecido puede no tenerlo, y por eso la ficha pregunta en
        vez de dar por hecho.
        """
        return self.quienes_responden.filter(responsable=True).first()

    @property
    def responsable(self):
        """El Tutor que responde por él ante la clínica y ante la ley."""
        vinculo = self.vinculo_responsable
        return vinculo.tutor if vinculo else None

    @property
    def necesita_responsable(self):
        """Si tiene que haber alguien que responda por él ahora mismo.

        Un Paciente activo, sí: es a quien se llama, a quien se cobra y quien
        firma un consentimiento, y una ficha activa que no dice a quién llamar no
        sirve para atender. Uno inactivo o fallecido, no: el animal cambió de
        manos o ya no está, nadie va a llamar a nadie, y exigir un responsable
        obligaría a dejar puesto a un Tutor que no tiene nada que ver — que es
        justo el dato falso que no se distingue de uno bueno.

        Lo pregunta el Vínculo antes de cerrarse (`Vinculo.cerrar`).
        """
        return self.esta_activo

    @property
    def le_falta_responsable(self):
        """Si está activo y no hay quien responda por él.

        No debería pasar y la ficha lo dice cuando pasa: se llega por un camino
        largo —el animal se traspasó estando inactivo y después volvió— y en
        silencio dejaría una ficha de trabajo sin teléfono al que llamar.
        """
        return self.necesita_responsable and self.vinculo_responsable is None

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

    # --- En qué situación está ante la clínica (`estados.py`) ---------------

    @property
    def esta_activo(self):
        return self.estado == EstadoDelPaciente.ACTIVO

    @property
    def esta_fallecido(self):
        return self.estado == EstadoDelPaciente.FALLECIDO

    @property
    def estado_a_la_vista(self):
        """El estado tal y como se le dice al Tutor, con la fecha si la hay.

        Con todas sus letras, y la ficha lo enseña aparte de los demás datos:
        confundir a un animal muerto con uno vivo es el peor error que se puede
        cometer en el mostrador, y no puede depender de que alguien repare en
        una casilla más de una lista.
        """
        if not self.esta_fallecido:
            return self.get_estado_display()
        if not self.fecha_de_fallecimiento:
            return _("Fallecido")
        return _("Fallecido el %(fecha)s") % {
            "fecha": date_format(self.fecha_de_fallecimiento, "DATE_FORMAT")
        }

    @property
    def se_puede_corregir(self):
        """Si su ficha admite todavía correcciones.

        La de un Paciente fallecido no: se conserva entera y en solo lectura,
        que es lo contrario de borrarla. Lo único que sigue pudiendo cambiar es
        el estado mismo, porque marcar por error al animal que no era tiene que
        poder deshacerse (`cambiar_de_estado`).
        """
        return not self.esta_fallecido

    @property
    def admite_citas(self):
        """Si se le puede agendar una Cita.

        Un animal muerto no vuelve, y citarlo es la llamada que ninguna clínica
        quiere hacer. `inactivo` no lo impide: que un animal lleve dos años sin
        venir es justamente la razón de citarlo.

        La regla vive aquí y no en `scheduling` porque es un hecho del Paciente,
        y porque `records` y la agenda no pueden preguntarle al revés
        (`CLAUDE.md`). Quien la ejercita al dar una Cita de alta es H3.
        """
        return not self.esta_fallecido

    @property
    def por_que_no_admite_citas(self):
        """Lo que hay que decirle a quien intenta citarlo, o `None` si se puede.

        Se devuelve el motivo y no un `False` a secas porque quien tropiece con
        la regla —la agenda del H3— tiene que poder decir qué pasa sin volver a
        deducirlo.
        """
        if self.admite_citas:
            return None
        return _("%(paciente)s consta como fallecido: no se le pueden dar Citas.") % {
            "paciente": self.nombre
        }

    def cambiar_de_estado(self, estado, fecha_de_fallecimiento=None):
        """Deja al Paciente en ese estado, con la fecha si es que falleció.

        La fecha se limpia sola al salir de `fallecido`, y eso vive aquí y no en
        la vista por lo mismo que `hacer_responsable` vive en el Vínculo: es la
        coherencia de la ficha, no el guion de una pantalla. Sin esto, deshacer
        un fallecimiento marcado por error dejaría una fecha de muerte en un
        animal vivo — y la base de datos, que no lo admite, lo diría con un
        error de servidor en la cara de recepción.

        Se guarda solo lo que cambia: una ficha de un fallecido no se toca, y un
        `save()` entero reescribiría datos que nadie está corrigiendo.
        """
        self.estado = estado
        self.fecha_de_fallecimiento = (
            fecha_de_fallecimiento if estado == EstadoDelPaciente.FALLECIDO else None
        )
        self.save(update_fields=["estado", "fecha_de_fallecimiento"])
        return self

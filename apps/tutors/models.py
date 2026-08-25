"""Tutor: la persona responsable de un Paciente ante la clínica y ante la ley.

Aquí viven **solo** sus datos personales: cómo se llama y por dónde se le
contacta. Los datos clínicos son del Paciente y viven en `patients`, y esa
separación no es cosmética (ADR-0004): un Tutor puede exigir la supresión de sus
datos personales mientras la Historia clínica de sus Pacientes —de la que es
titular el animal, no él— tiene que conservarse. Anonimizar (ticket 20) será
vaciar `DATOS_PERSONALES` de esta tabla sin tocar ninguna otra.

Aquí vive también el **Consentimiento de contacto**: por qué canales acepta
que se le escriba. Es dato personal suyo y no del Paciente, y se guarda como
una declaración por cada vez que dijo algo —no como una columna de sí o no—,
porque lo exigible no es el valor de hoy sino cuándo lo dio y cuándo se
desdijo. Quién pregunta y qué se responde lo cuenta `consentimiento.py`.

Aquí vive también el **Vínculo**, que es quién responde por qué Paciente. Está en
esta app y no en `patients` porque es un hecho del Tutor —de quién se hace cargo—
y porque así la dependencia va en un solo sentido: `tutors` conoce a `patients`,
`patients` no conoce a nadie. Un Paciente que cambia de Tutor sigue siendo el
mismo Paciente con la misma Historia clínica, y eso solo se sostiene si el
vínculo es una tabla aparte y no una columna del Paciente.
"""

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.busqueda import Campo
from apps.campos import CampoDeTelefono
from apps.telefono import como_se_busca as telefono_como_se_busca
from apps.tenancy.aislamiento import ModeloDeLaClinica
from apps.tutors.campos import CampoDeRut
from apps.tutors.consentimiento import Canal, lo_que_diria, lo_ultimo_que_dijo
from apps.tutors.rut import como_se_busca as rut_como_se_busca
from apps.tutors.rut import formateado
from apps.tutors.rut import normalizado as rut_normalizado


class Tutor(ModeloDeLaClinica):
    """Persona responsable de un Paciente. No es un Usuario del sistema."""

    # Solo el nombre es obligatorio. En el mostrador a veces no hay más que un
    # nombre y un teléfono, y exigir el resto empujaría a rellenarlo con
    # cualquier cosa, que es peor que un hueco: un dato falso no se distingue.
    nombre = models.CharField(_("nombre"), max_length=200)
    apellidos = models.CharField(_("apellidos"), max_length=200, blank=True)
    # El RUT también es opcional, y no por comodidad: un Tutor extranjero no
    # tiene, y quien no quiera darlo tiene derecho a que se le atienda igual.
    # Cuando está, es único dentro de la Clínica —nunca a nivel global, que ya
    # sería un fichero de personas por encima de las Clínicas (ADR-0003)—, y por
    # eso el hueco se guarda como cadena vacía y la restricción lo deja fuera:
    # dos Tutores sin RUT no son el mismo Tutor.
    rut = CampoDeRut(_("RUT"), max_length=9, blank=True)
    # No es único a propósito: una familia comparte número, y dos Tutores con el
    # mismo teléfono son lo normal. Que se repita se avisa al guardar, no se
    # impide.
    telefono = CampoDeTelefono(_("teléfono"), max_length=16, blank=True)
    email = models.EmailField(_("correo"), blank=True)
    direccion = models.CharField(_("dirección"), max_length=250, blank=True)

    # De qué Pacientes se hace cargo. Se declara desde aquí y no desde el
    # Paciente porque la dependencia entre apps va en este sentido, y pasa por
    # el Vínculo porque de la relación hay algo que decir: cuál de los Tutores
    # es el responsable.
    pacientes = models.ManyToManyField(
        "patients.Paciente",
        through="tutors.Vinculo",
        related_name="tutores",
        verbose_name=_("Pacientes"),
    )

    # Lo que desaparece al anonimizar al Tutor, y lo que el formulario ofrece
    # rellenar. `tests/test_fichas_de_tutor.py` comprueba que no hay en esta
    # tabla ningún otro campo que no sea la Clínica o el Vínculo: un dato clínico
    # aquí sobreviviría al derecho de supresión, y un dato personal fuera de aquí
    # se le escaparía. De quién se hizo cargo **no** es un dato personal suyo: es
    # parte de la Historia del Paciente —quién lo trajo— y tiene que sobrevivir a
    # la anonimización.
    DATOS_PERSONALES = ("nombre", "apellidos", "rut", "telefono", "email", "direccion")

    # Por dónde se busca a un Tutor: cómo se llama, cómo se identifica y por
    # dónde se le contacta. La dirección queda fuera a propósito —nadie llama
    # preguntando por una calle— y meterla solo traería coincidencias que
    # estorban.
    #
    # Es un hecho del Tutor y no de ninguna pantalla, y por eso vive aquí y no
    # en el listado: lo usan el fichero de Tutores (`listado.py`) y la caja
    # única del mostrador (`mostrador.py`), y dos definiciones de «cómo se
    # encuentra a un Tutor» acabarían diciendo cosas distintas.
    #
    # Cada campo dice además cómo hay que leer lo escrito para buscar en él
    # (`apps/busqueda.py`): el RUT y el teléfono se guardan normalizados y nadie
    # los teclea así.
    POR_DONDE_SE_BUSCA = (
        Campo.de_texto("nombre"),
        Campo.de_texto("apellidos"),
        Campo.normalizado("rut", rut_normalizado, rut_como_se_busca),
        Campo.de_digitos("telefono", telefono_como_se_busca),
        Campo.de_texto("email"),
    )

    class Meta:
        verbose_name = _("Tutor")
        verbose_name_plural = _("Tutores")
        # Por apellidos, que es como se busca a alguien en un fichero.
        ordering = ["apellidos", "nombre"]
        indexes = [
            models.Index(fields=["clinic", "apellidos", "nombre"], name="tutor_por_apellidos")
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["clinic", "rut"],
                condition=~models.Q(rut=""),
                name="rut_unico_dentro_de_la_clinica",
            )
        ]

    def __str__(self):
        return f"{self.nombre} {self.apellidos}".strip()

    def get_absolute_url(self):
        """Dónde vive su ficha.

        Lo sabe el Tutor y no cada pantalla que lo enlaza: el aviso de
        coincidencia (`apps/coincidencias.py`) lleva a la ficha que ya existe, y
        el enlace tenía que componerse una sola vez para los dos modelos.
        """
        return reverse("tutors:ficha", args=[self.pk])

    @property
    def rut_a_la_chilena(self):
        """El RUT como se lee y se dicta: «12.345.678-5». Vacío si no tiene."""
        return formateado(self.rut)

    @property
    def de_quienes_se_hace_cargo(self):
        """Los Pacientes de los que responde **hoy**: los de Vínculo abierto.

        Por el manager sin filtro, por lo mismo que `Paciente.quienes_responden`:
        un Vínculo nunca cruza la frontera de la Clínica, así que volver a
        filtrar por la Clínica activa no protege nada y sí deja la ficha en
        blanco fuera de una petición HTTP.

        Las dos condiciones van en el mismo `filter` y la del Tutor se repite a
        propósito: así Django resuelve el Vínculo en **una sola** unión con la
        que ya trae la relación, y un Paciente que fue suyo, dejó de serlo y
        volvió —dos Vínculos con el mismo animal— sale una vez y no dos.
        """
        return self.pacientes(manager="de_todas_las_clinicas").filter(
            vinculos__tutor=self, vinculos__fecha_de_cierre__isnull=True
        )

    @property
    def de_quienes_se_hizo_cargo(self):
        """Los Vínculos que ya cerró, el último cambio de manos primero.

        Son Vínculos y no Pacientes porque de estos hay algo más que decir: hasta
        cuándo fue suyo. Que el Tutor anterior siga viendo qué animal fue suyo y
        hasta qué día es media casilla del ticket 10 —la otra media la enseña la
        ficha del Paciente—, y es lo que se mira cuando llama preguntando por
        una cuenta o por lo que se le hizo al animal mientras lo tuvo.
        """
        return (
            self.vinculos(manager="de_todas_las_clinicas")
            .filter(fecha_de_cierre__isnull=False)
            .select_related("paciente")
            .order_by("-fecha_de_cierre", "-pk")
        )

    def se_hace_cargo_de(self, paciente, responsable=False):
        """Vincula a este Tutor con ese Paciente y devuelve el Vínculo.

        Aquí y no en la vista porque la regla no es de ninguna pantalla: un
        Paciente sin responsable no dice a quién llamar, así que el primer Tutor
        que aparece se queda con el cargo aunque nadie lo haya pedido. Después
        habrá que decir explícitamente que otro lo releva.

        Se busca antes de crear, y solo entre los Vínculos **abiertos**: volver a
        vincular a quien ya responde por el animal no es un Vínculo más, y
        volver a vincular a quien lo tuvo antes sí lo es. Un animal que vuelve a
        su Tutor de siempre son dos tramos con sus dos fechas, no una corrección
        del primero.

        La Clínica sale del Tutor, que es de donde tiene que salir: un Vínculo
        entre Clínicas no significaría nada, y por eso lo escribe el manager que
        cruza la frontera a la vista de todos (ADR-0003).
        """
        vinculo, _ = Vinculo.de_todas_las_clinicas.get_or_create(
            clinic=self.clinic, tutor=self, paciente=paciente, fecha_de_cierre=None
        )
        if responsable or not paciente.vinculo_responsable:
            vinculo.hacer_responsable()
        return vinculo


    @property
    def lo_que_ha_dicho_del_contacto(self):
        """Todo lo que ha dicho sobre que se le contacte, lo último primero.

        La historia entera y no el valor de hoy, porque es la historia lo que hay
        que poder enseñar: un consentimiento que solo dice qué acepta ahora no
        prueba nada del mensaje que salió en marzo. Por el manager sin filtro,
        por lo mismo que `lo_ultimo_que_dijo`.
        """
        return self.consentimientos(manager="de_todas_las_clinicas").all()

    def deja_dicho_sobre_el_contacto(self, canal, otorgado, fecha=None):
        """Anota lo que el Tutor acaba de decir de un canal; devuelve la anotación.

        Devuelve `None` cuando no dice nada nuevo: volver a autorizar lo que ya
        estaba autorizado no es una decisión, es la misma de siempre. La regla
        vive aquí y no en el formulario porque el importador y el mostrador
        tienen que respetarla igual, y porque la historia del consentimiento es
        justo lo que hay que poder enseñar: una fila por cada visita a una
        pantalla la volvería ilegible.

        Nunca pisa lo anterior. Revocar es decir algo nuevo, no borrar lo dicho:
        lo que consta es que hasta ese día había un sí, y eso es lo que sostiene
        cada mensaje que ya salió.

        Sin fecha se toma la de hoy, que es cuando se dice en el mostrador; se
        admite una anterior porque el consentimiento llega a veces en papel.

        La Clínica sale del Tutor, que es de donde tiene que salir: un
        Consentimiento entre Clínicas no significaría nada, y por eso lo escribe
        el manager que cruza la frontera a la vista de todos (ADR-0003).
        """
        fecha = fecha or timezone.localdate()
        ultima = lo_ultimo_que_dijo(self, canal)
        # Solo se calla lo que repite lo que vale **hoy**. Una declaración con
        # fecha anterior a la última se guarda diga lo que diga: es un trozo de
        # historia que alguien está completando —el papel que llegó tarde—, y
        # tirarlo por parecerse al presente sería tirar evidencia.
        if ultima is not None and ultima.fecha <= fecha and ultima.otorgado == otorgado:
            return None
        return Consentimiento.de_todas_las_clinicas.create(
            clinic=self.clinic,
            tutor=self,
            canal=canal,
            otorgado=otorgado,
            fecha=fecha,
        )


class Vinculo(ModeloDeLaClinica):
    """Que un Tutor responde por un Paciente.

    Es de muchos a muchos porque la clínica atiende familias: un Paciente puede
    tener varios Tutores —una pareja separada que se turna, una hija que lo trae
    al control— y un Tutor casi siempre tiene más de un Paciente.

    Uno solo de esos Tutores es el **responsable**: a quien se llama y a quien se
    cobra. Que sea uno solo lo garantiza la base de datos, no el cuidado de quien
    escribe la vista.

    Un Vínculo **se cierra con fecha, nunca se borra**. El animal cambia de manos
    y lo que hay que conservar es quién lo trajo antes y hasta cuándo: borrar la
    fila dejaría una Historia clínica sin nadie detrás de la mitad de sus
    Consultas, y la Historia es del animal (ADR-0001). Cerrado es exactamente
    eso: fue verdad hasta ese día. Por eso un Vínculo cerrado no puede ser el
    responsable, y por eso el mismo Tutor puede volver a vincularse con el mismo
    Paciente: son dos tramos con sus dos fechas.
    """

    tutor = models.ForeignKey(
        Tutor, on_delete=models.CASCADE, related_name="vinculos", verbose_name=_("Tutor")
    )
    paciente = models.ForeignKey(
        "patients.Paciente",
        on_delete=models.CASCADE,
        related_name="vinculos",
        verbose_name=_("Paciente"),
    )
    responsable = models.BooleanField(_("es el responsable"), default=False)
    # Hasta cuándo respondió por él. En blanco es el Vínculo vivo, que es lo
    # normal; con fecha es el Tutor anterior, que se conserva entero. Es una
    # fecha y no una marca de sí o no porque lo que hace falta después es
    # justamente el día: a quién se le pregunta por lo que se le hizo al animal
    # en marzo depende de quién lo tenía en marzo.
    fecha_de_cierre = models.DateField(_("hasta"), null=True, blank=True)

    class Meta:
        verbose_name = _("Vínculo")
        verbose_name_plural = _("Vínculos")
        # El responsable primero: es de quien habla la ficha cuando dice «a quién
        # se llama». El resto por como se busca a alguien en un fichero.
        ordering = ["-responsable", "tutor__apellidos", "tutor__nombre", "pk"]
        constraints = [
            # Uno solo **abierto**: volver a vincular a quien ya responde por el
            # animal sería un duplicado, pero el Tutor que lo tuvo y lo recupera
            # años después es otro tramo, con su fecha, y los dos hacen falta.
            models.UniqueConstraint(
                fields=["tutor", "paciente"],
                condition=models.Q(fecha_de_cierre__isnull=True),
                name="un_solo_vinculo_abierto_por_tutor_y_paciente",
            ),
            # Que el responsable sea uno solo se impone aquí y no en la vista:
            # una ficha con dos responsables no dice a quién llamar, y eso no
            # puede depender de que nadie abra dos pestañas.
            models.UniqueConstraint(
                fields=["paciente"],
                condition=models.Q(responsable=True),
                name="un_solo_tutor_responsable_por_paciente",
            ),
            # Quien dejó de responder por el animal no puede seguir siendo a
            # quien se llama. Es lo que separa el cierre de un adorno: sin esto,
            # cerrar un Vínculo y olvidar el cargo dejaría a la clínica llamando
            # a quien ya no tiene al animal.
            models.CheckConstraint(
                condition=models.Q(responsable=False)
                | models.Q(fecha_de_cierre__isnull=True),
                name="un_vinculo_cerrado_no_es_responsable",
            ),
        ]

    def __str__(self):
        return f"{self.tutor} — {self.paciente}"

    @property
    def esta_abierto(self):
        """Si este Tutor responde todavía por el Paciente."""
        return self.fecha_de_cierre is None

    @property
    def por_que_no_se_puede_cerrar(self):
        """Lo que hay que decirle a quien intente cerrarlo, o `None` si se puede.

        Un Paciente activo no puede quedarse sin nadie que responda por él: su
        ficha no diría a quién llamar ni a quién cobrar. Así que el Vínculo del
        responsable no se cierra a secas — se traspasa el Paciente, que es cerrar
        uno y abrir otro a la vez (`traspaso.py`).

        Uno inactivo o fallecido sí puede quedarse sin responsable: el animal
        cambió de manos o ya no está, nadie va a llamar a nadie, y exigir aquí un
        responsable obligaría a dejar puesto a un Tutor que no tiene nada que
        ver.

        Se devuelve el motivo y no un `False` a secas por lo mismo que en
        `Paciente.por_que_no_admite_citas`: quien tropiece con la regla —el
        formulario, la plantilla que decide si ofrece el enlace— tiene que poder
        decir qué pasa sin volver a deducirlo.
        """
        if self.responsable and self.paciente.necesita_responsable:
            return _(
                "%(paciente)s se quedaría sin nadie que responda por él: "
                "diga antes quién lo releva."
            ) % {"paciente": self.paciente.nombre}
        return None

    def cerrar(self, fecha=None):
        """Deja constancia de que este Tutor dejó de responder por el Paciente.

        No borra: la fila se queda con la fecha, que es lo que hace falta
        después. Sin fecha se toma la de hoy, que es cuando se dice en el
        mostrador; se admite una anterior porque el Tutor avisa a veces tarde.
        """
        motivo = self.por_que_no_se_puede_cerrar
        if motivo:
            raise ValidationError(motivo, code="sin_responsable")
        self.responsable = False
        self.fecha_de_cierre = fecha or timezone.localdate()
        self.save(update_fields=["responsable", "fecha_de_cierre"])
        return self

    def hacer_responsable(self):
        """Deja a este Tutor como el responsable del Paciente, y solo a él.

        Primero suelta al que lo era y después se marca, en la misma
        transacción: al revés habría un instante con dos responsables, y la
        restricción de la base —que no es diferida— lo rechazaría.
        """
        with transaction.atomic():
            self.paciente.quienes_responden.exclude(pk=self.pk).filter(responsable=True).update(
                responsable=False
            )
            self.responsable = True
            self.save(update_fields=["responsable"])


class Consentimiento(ModeloDeLaClinica):
    """Lo que un Tutor dijo un día sobre que se le contacte por un canal.

    Una fila **no es el consentimiento actual**: es una declaración con su fecha.
    El consentimiento de hoy es la última de su canal, y eso lo responde
    `consentimiento.se_puede_contactar`, que es por donde pregunta todo envío.

    Se guarda así, y no como tres columnas del Tutor, porque la Ley 21.719 no
    pregunta qué acepta hoy: pregunta desde cuándo lo aceptaba el día que se le
    escribió. Un booleano que se sobrescribe deja cada mensaje ya enviado sin
    nada detrás.

    Nada se borra y nada se corrige: el Tutor que se desdice deja una fila que
    dice que no, encima de la que decía que sí. Por eso tampoco hay formulario de
    edición de una declaración — solo se declara de nuevo.
    """

    tutor = models.ForeignKey(
        Tutor,
        on_delete=models.CASCADE,
        related_name="consentimientos",
        verbose_name=_("Tutor"),
    )
    canal = models.CharField(_("canal"), max_length=20, choices=Canal.choices)
    otorgado = models.BooleanField(_("autoriza"))
    # Una fecha y no un instante: lo que consta es el día en que lo dijo, que es
    # lo que se apunta en un mostrador y lo que se lee en un papel firmado. El
    # orden dentro del mismo día lo pone `-pk`, que es el orden en que llegaron.
    fecha = models.DateField(_("fecha"), default=timezone.localdate)

    class Meta:
        verbose_name = _("Consentimiento de contacto")
        verbose_name_plural = _("Consentimientos de contacto")
        # Lo último primero: es lo que vale, y así la primera fila de cada canal
        # responde la pregunta sin ordenar nada más.
        ordering = ["-fecha", "-pk"]
        indexes = [
            models.Index(fields=["tutor", "canal", "-fecha", "-id"], name="consentimiento_ultimo")
        ]

    def __str__(self):
        return f"{self.tutor} — {self.get_canal_display()} — {self.fecha}"

    @property
    def a_la_vista(self):
        """Lo que dijo, tal como se lee en la historia de su ficha."""
        return lo_que_diria(self.otorgado).label

"""Clínica, Sede y Usuario, y lo que la Sede tiene que declarar de sí misma.

La Clínica es la frontera de aislamiento de todos los datos (ADR-0003): por eso
es el único modelo de este archivo sin clave ajena `clinic`. La Sede es un local
físico suyo, y el Usuario pertenece a una Clínica y a una o varias de sus Sedes.

Detrás de los tres va la configuración de la Sede: cuándo atiende —sus Franjas y
sus Excepciones, cuya regla vive en `horarios.py`—, si atiende urgencias, y a
qué Clínicas de derivación mandar a un Tutor cuando no puede atenderlo. En H1
esto no se ve en ninguna pantalla del mostrador: son los datos de los que
dependen la agenda (H3) y la Autorespuesta (H4), que sin ellos no sabrían ni
cuándo hay huecos ni qué contestar de madrugada.
"""

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.campos import CampoDeTelefono
from apps.tenancy.aislamiento import ModeloDeLaClinica
from apps.tenancy.horarios import Dia


class Clinica(models.Model):
    """La organización que contrata el sistema."""

    nombre = models.CharField(_("nombre"), max_length=120, unique=True)
    creada = models.DateTimeField(_("creada"), default=timezone.now)

    class Meta:
        verbose_name = _("Clínica")
        verbose_name_plural = _("Clínicas")
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Sede(models.Model):
    """Local físico de una Clínica.

    Las Sedes de una Clínica comparten Tutores y Pacientes, pero no agenda.
    """

    clinic = models.ForeignKey(
        Clinica, on_delete=models.CASCADE, related_name="sedes", verbose_name=_("Clínica")
    )
    nombre = models.CharField(_("nombre"), max_length=120)
    direccion = models.CharField(_("dirección"), max_length=250, blank=True)

    # Si esta Sede atiende fuera de su horario lo que no puede esperar. Es una
    # bandera de la Sede y no de la Clínica porque se atiende en un local: una
    # Clínica con dos Sedes puede tener urgencias en una sola.
    atiende_urgencias = models.BooleanField(_("atiende urgencias"), default=False)
    # El teléfono de urgencias es propio cuando lo hay —suele ser el celular de
    # turno, no la línea del mostrador— y por eso no se deduce de ningún otro
    # dato. Vacío significa que se llama al número de siempre.
    telefono_de_urgencias = CampoDeTelefono(
        _("teléfono de urgencias"), max_length=16, blank=True
    )

    class Meta:
        verbose_name = _("Sede")
        verbose_name_plural = _("Sedes")
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(fields=["clinic", "nombre"], name="sede_unica_en_la_clinica"),
            # Un teléfono de urgencias en una Sede que no atiende urgencias es
            # una Sede que dice dos cosas a la vez, y la Autorespuesta tendría
            # que elegir cuál. Sale de quitar la bandera y olvidar el número.
            models.CheckConstraint(
                condition=models.Q(telefono_de_urgencias="")
                | models.Q(atiende_urgencias=True),
                name="solo_una_sede_de_urgencias_tiene_telefono_de_urgencias",
            ),
        ]

    def __str__(self):
        return self.nombre


class Rol(models.TextChoices):
    """Lo que un Usuario puede hacer dentro de su Clínica."""

    VETERINARIO = "veterinario", _("veterinario")
    RECEPCION = "recepcion", _("recepción")
    ADMIN = "admin", _("admin")


class GestorDeUsuarios(BaseUserManager):
    """Crea Usuarios con la contraseña ya cifrada.

    No hay `create_superuser`: no existe `django.contrib.admin` y el alta de una
    Clínica con su primer admin la hace el comando `crear_clinica`.
    """

    def create_user(self, email, clinic, contrasena=None, **campos):
        if not email:
            raise ValueError(_("Un Usuario necesita un correo para entrar."))
        usuario = self.model(email=self.normalize_email(email), clinic=clinic, **campos)
        usuario.set_password(contrasena)
        usuario.save(using=self._db)
        return usuario


class Usuario(AbstractBaseUser):
    """Persona que accede a la aplicación en el contexto de una Clínica.

    Sin `PermissionsMixin`: los permisos de Gatabase son el `rol` y las Sedes,
    no los grupos de Django, y no hay sitio de administración que los use.
    """

    clinic = models.ForeignKey(
        Clinica, on_delete=models.CASCADE, related_name="usuarios", verbose_name=_("Clínica")
    )
    # El correo identifica al Usuario en todo el sistema, no solo en su Clínica:
    # es con lo que entra. Quien trabaje en dos Clínicas necesita dos correos.
    email = models.EmailField(_("correo"), unique=True)
    nombre = models.CharField(_("nombre"), max_length=120)
    apellidos = models.CharField(_("apellidos"), max_length=120, blank=True)
    rol = models.CharField(_("rol"), max_length=20, choices=Rol.choices, default=Rol.RECEPCION)
    sedes = models.ManyToManyField(
        Sede, related_name="usuarios", verbose_name=_("Sedes"), blank=True
    )
    is_active = models.BooleanField(_("activo"), default=True)
    date_joined = models.DateTimeField(_("alta"), default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = GestorDeUsuarios()

    class Meta:
        verbose_name = _("Usuario")
        verbose_name_plural = _("Usuarios")
        ordering = ["apellidos", "nombre"]

    def __str__(self):
        return f"{self.nombre} {self.apellidos}".strip()

    @property
    def es_admin(self):
        return self.rol == Rol.ADMIN


class FranjaDeAtencion(ModeloDeLaClinica):
    """Un tramo de un día de la semana en que la Sede atiende.

    El Horario de atención de una Sede es el conjunto de sus Franjas, y por eso
    hay varias por día: una clínica chilena cierra a mediodía y vuelve por la
    tarde, y decirlo con una sola franja de 09:00 a 19:00 sería agendar una hora
    a las 14:30 con la puerta cerrada.

    Qué se hace con ellas —el borde de la franja, y qué manda una Excepción— lo
    decide `horarios.py`. Aquí solo está lo que no puede quedar mal escrito:
    una franja que termina antes de empezar no la acepta la base de datos.
    """

    sede = models.ForeignKey(
        Sede, on_delete=models.CASCADE, related_name="franjas", verbose_name=_("Sede")
    )
    dia = models.SmallIntegerField(_("día"), choices=Dia)
    desde = models.TimeField(_("desde"))
    hasta = models.TimeField(_("hasta"))

    class Meta:
        verbose_name = _("Franja de atención")
        verbose_name_plural = _("Franjas de atención")
        ordering = ["sede", "dia", "desde"]
        constraints = [
            # Una franja que cruza la medianoche se declara en dos, una en cada
            # día. Es lo que ya hace quien escribe el cartel de la puerta, y
            # evita que «de 20:00 a 02:00» tenga que significar dos cosas según
            # quién lo lea.
            models.CheckConstraint(
                condition=models.Q(hasta__gt=models.F("desde")),
                name="una_franja_termina_despues_de_empezar",
            ),
            models.UniqueConstraint(
                fields=["sede", "dia", "desde"],
                name="una_franja_por_sede_dia_y_hora_de_apertura",
            ),
        ]

    def __str__(self):
        return f"{self.get_dia_display()} {self.desde:%H:%M}–{self.hasta:%H:%M}"


class ExcepcionDeAtencion(ModeloDeLaClinica):
    """Lo que la Sede hace una fecha concreta, en lugar de lo que diga la semana.

    Cubre las dos cosas que le pasan a un horario: el día que no se abre —un
    festivo, la semana de vacaciones— y el día que se abre distinto —el 24 de
    diciembre hasta las 14:00—. Son el mismo hecho dicho con más o menos datos:
    sin horas, la Sede cierra; con horas, atiende esas y no las de su semana.

    Deliberadamente **no** hay un calendario automático de festivos: el motivo
    está en `horarios.py`.
    """

    sede = models.ForeignKey(
        Sede, on_delete=models.CASCADE, related_name="excepciones", verbose_name=_("Sede")
    )
    fecha = models.DateField(_("fecha"))
    # Para que quien lo mire en marzo sepa por qué se cerró: «Año Nuevo»,
    # «vacaciones del equipo». No lo lee ningún proceso.
    motivo = models.CharField(_("motivo"), max_length=120, blank=True)
    desde = models.TimeField(_("desde"), null=True, blank=True)
    hasta = models.TimeField(_("hasta"), null=True, blank=True)

    class Meta:
        verbose_name = _("Excepción de atención")
        verbose_name_plural = _("Excepciones de atención")
        ordering = ["sede", "fecha", "desde"]
        constraints = [
            # O están las dos horas o no está ninguna: media excepción —«abre a
            # las 09:00» sin decir hasta cuándo— no se sabría aplicar.
            models.CheckConstraint(
                condition=models.Q(desde__isnull=True, hasta__isnull=True)
                | models.Q(desde__isnull=False, hasta__isnull=False),
                name="una_excepcion_tiene_las_dos_horas_o_ninguna",
            ),
            models.CheckConstraint(
                condition=models.Q(hasta__isnull=True) | models.Q(hasta__gt=models.F("desde")),
                name="una_excepcion_termina_despues_de_empezar",
            ),
        ]

    def __str__(self):
        if self.desde is None:
            return _("%(fecha)s: cerrado") % {"fecha": self.fecha}
        return _("%(fecha)s: de %(desde)s a %(hasta)s") % {
            "fecha": self.fecha,
            "desde": f"{self.desde:%H:%M}",
            "hasta": f"{self.hasta:%H:%M}",
        }


class ClinicaDeDerivacion(ModeloDeLaClinica):
    """Clínica externa a la que se manda a un Tutor cuando la Sede no puede atenderlo.

    Es un catálogo que mantiene el admin y no una lista que traiga el sistema:
    la red de clínicas socias es conocimiento local —quién contesta de
    madrugada, quién tiene pabellón, con quién se tiene trato— y cambia sin que
    nadie de fuera se entere.

    Cuelga de la Clínica y no de la Sede: el trato con la clínica de al lado lo
    tiene la organización, y las Sedes de una Clínica comparten la lista igual
    que comparten Tutores y Pacientes.

    Se guardan las tres cosas que hay que darle a un Tutor por teléfono a las
    tres de la mañana: cómo se llama, a qué número llamar y dónde está.
    """

    nombre = models.CharField(_("nombre"), max_length=120)
    telefono = CampoDeTelefono(_("teléfono"), max_length=16, blank=True)
    direccion = models.CharField(_("dirección"), max_length=250, blank=True)

    class Meta:
        verbose_name = _("Clínica de derivación")
        verbose_name_plural = _("Clínicas de derivación")
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["clinic", "nombre"],
                name="clinica_de_derivacion_unica_en_la_clinica",
            )
        ]

    def __str__(self):
        return self.nombre

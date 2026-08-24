"""Tutor: la persona responsable de un Paciente ante la clínica y ante la ley.

Aquí viven **solo** sus datos personales: cómo se llama y por dónde se le
contacta. Los datos clínicos son del Paciente y viven en `patients`, y esa
separación no es cosmética (ADR-0004): un Tutor puede exigir la supresión de sus
datos personales mientras la Historia clínica de sus Pacientes —de la que es
titular el animal, no él— tiene que conservarse. Anonimizar (ticket 20) será
vaciar `DATOS_PERSONALES` de esta tabla sin tocar ninguna otra.

El Consentimiento de contacto llega en el ticket 15.

Aquí vive también el **Vínculo**, que es quién responde por qué Paciente. Está en
esta app y no en `patients` porque es un hecho del Tutor —de quién se hace cargo—
y porque así la dependencia va en un solo sentido: `tutors` conoce a `patients`,
`patients` no conoce a nadie. Un Paciente que cambia de Tutor sigue siendo el
mismo Paciente con la misma Historia clínica, y eso solo se sostiene si el
vínculo es una tabla aparte y no una columna del Paciente.
"""

from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from apps.tenancy.aislamiento import ModeloDeLaClinica
from apps.tutors.campos import CampoDeRut, CampoDeTelefono
from apps.tutors.rut import formateado


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

    @property
    def rut_a_la_chilena(self):
        """El RUT como se lee y se dicta: «12.345.678-5». Vacío si no tiene."""
        return formateado(self.rut)

    @property
    def de_quienes_se_hace_cargo(self):
        """Los Pacientes de este Tutor.

        Por el manager sin filtro, por lo mismo que `Paciente.quienes_responden`:
        un Vínculo nunca cruza la frontera de la Clínica, así que volver a
        filtrar por la Clínica activa no protege nada y sí deja la ficha en
        blanco fuera de una petición HTTP.
        """
        return self.pacientes(manager="de_todas_las_clinicas").all()

    def se_hace_cargo_de(self, paciente, responsable=False):
        """Vincula a este Tutor con ese Paciente y devuelve el Vínculo.

        Aquí y no en la vista porque la regla no es de ninguna pantalla: un
        Paciente sin responsable no dice a quién llamar, así que el primer Tutor
        que aparece se queda con el cargo aunque nadie lo haya pedido. Después
        habrá que decir explícitamente que otro lo releva.

        La Clínica sale del Tutor, que es de donde tiene que salir: un Vínculo
        entre Clínicas no significaría nada, y por eso lo escribe el manager que
        cruza la frontera a la vista de todos (ADR-0003).
        """
        vinculo = Vinculo.de_todas_las_clinicas.create(
            clinic=self.clinic, tutor=self, paciente=paciente
        )
        if responsable or not paciente.vinculo_responsable:
            vinculo.hacer_responsable()
        return vinculo


class Vinculo(ModeloDeLaClinica):
    """Que un Tutor responde por un Paciente.

    Es de muchos a muchos porque la clínica atiende familias: un Paciente puede
    tener varios Tutores —una pareja separada que se turna, una hija que lo trae
    al control— y un Tutor casi siempre tiene más de un Paciente.

    Uno solo de esos Tutores es el **responsable**: a quien se llama y a quien se
    cobra. Que sea uno solo lo garantiza la base de datos, no el cuidado de quien
    escribe la vista.

    El cierre del Vínculo con fecha —el Paciente cambió de dueño y hay que
    conservar quién lo trajo antes— es del ticket 10.
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

    class Meta:
        verbose_name = _("Vínculo")
        verbose_name_plural = _("Vínculos")
        # El responsable primero: es de quien habla la ficha cuando dice «a quién
        # se llama». El resto por como se busca a alguien en un fichero.
        ordering = ["-responsable", "tutor__apellidos", "tutor__nombre", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["tutor", "paciente"], name="un_solo_vinculo_por_tutor_y_paciente"
            ),
            # Que el responsable sea uno solo se impone aquí y no en la vista:
            # una ficha con dos responsables no dice a quién llamar, y eso no
            # puede depender de que nadie abra dos pestañas.
            models.UniqueConstraint(
                fields=["paciente"],
                condition=models.Q(responsable=True),
                name="un_solo_tutor_responsable_por_paciente",
            ),
        ]

    def __str__(self):
        return f"{self.tutor} — {self.paciente}"

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

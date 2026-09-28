"""Derechos del titular: lo que un Tutor puede pedir de sus propios datos.

Dos cosas, que son las que la Ley 21.719 hace exigibles desde el 1 de diciembre
de 2026: **saber qué consta de él** —y quién lo ha mirado— y **que se suprima**.

La tensión que resuelve este módulo está en la segunda. El derecho de supresión
alcanza a los datos personales del Tutor, no a la Historia clínica del Paciente,
que es de otro titular —el animal— y que la clínica tiene el deber de conservar
(ADR-0004). Por eso suprimir no es borrar la fila del Tutor: borrarla se
llevaría por delante los Vínculos, y con ellos quién trajo al animal hasta
cuándo, que es parte de su Historia (ADR-0001).

**Anonimizar es vaciar `Tutor.DATOS_PERSONALES`**, y nada más. La fila se queda
—con su identificador, sus Vínculos y la fecha en que dejó de ser alguien—, y
todo lo que colgaba de ella deja de señalar a una persona:

- **Los Vínculos se quedan enteros.** De quién se hizo cargo no es un dato
  personal suyo sino parte de la Historia del Paciente; el Paciente sigue
  teniendo responsable, que ahora es un Tutor anonimizado.
- **Los Consentimientos se quedan también.** Son la evidencia de que cada
  mensaje que ya salió tenía un sí detrás, y sin nombre ni teléfono ya no dicen
  de quién: una fecha y un canal no identifican a nadie. Lo que sí cambia es que
  a un Tutor anonimizado no se le escribe más (`consentimiento.py`).
- **El Registro de acceso no se toca**, y no podría: no admite `UPDATE` ni
  `DELETE` (ADR-0004). Es la evidencia del tratamiento, la que habrá que enseñar
  si alguien pregunta qué se hizo con esos datos mientras existieron, y apunta al
  Tutor por su identificador, que no es dato de nadie.

Es irreversible a propósito: no se guarda lo que había en ninguna parte, porque
una copia para deshacer sería justamente el dato que el Tutor pidió suprimir.
"""

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.audit.models import Accion, RegistroDeAcceso
from apps.audit.registro import anotar
from apps.tutors.models import Tutor


def anonimizar(tutor, usuario):
    """Suprime los datos personales del Tutor y deja constancia de quién lo hizo.

    Todo en la misma transacción: un Tutor en blanco sin anotación en el
    Registro sería una supresión de la que nadie responde, y una anotación sin
    el Tutor en blanco, una supresión que no ocurrió.

    Se relee el Tutor bloqueando su fila: dos admins que confirman a la vez no
    anonimizan dos veces, y el segundo no deja una anotación de algo que no hizo.
    Sobre uno ya anonimizado no hace nada y devuelve `False`.
    """
    with transaction.atomic():
        tutor = Tutor.de_todas_las_clinicas.select_for_update().get(pk=tutor.pk)
        if tutor.esta_anonimizado:
            return False
        for dato in Tutor.DATOS_PERSONALES:
            setattr(tutor, dato, "")
        tutor.anonimizado = timezone.now()
        tutor.save(update_fields=[*Tutor.DATOS_PERSONALES, "anonimizado"])
        anotar(usuario, Accion.ANONIMIZACION, tutor)
    return True


@dataclass(frozen=True)
class LoQueConsta:
    """Todo lo que la Clínica guarda de un Tutor, para dárselo cuando lo pida.

    Son listas y no consultas a medio hacer: es un Tutor, no una Clínica entera
    —a diferencia de la exportación del ticket 19, aquí no hay volumen que
    ahorrar—, y así la plantilla no consulta la base mientras se pinta.
    """

    tutor: Tutor
    datos: list
    vinculos: list
    consentimientos: list
    accesos: list

    @property
    def pacientes(self):
        """Los Pacientes que el documento nombra, para el Registro de acceso."""
        return [vinculo.paciente for vinculo in self.vinculos]


def _datos(tutor):
    """Sus datos personales, cada uno con el rótulo con que lo conoce la ficha.

    Salen de `DATOS_PERSONALES` y no de una lista escrita aquí: un dato personal
    nuevo entra en el documento el día que entra en el Tutor, sin que haya que
    acordarse de este módulo.
    """
    datos = []
    for campo in Tutor.DATOS_PERSONALES:
        valor = tutor.rut_a_la_chilena if campo == "rut" else getattr(tutor, campo)
        datos.append((Tutor._meta.get_field(campo).verbose_name, valor))
    return datos


def accesos_a(tutor):
    """Quién vio o tocó los datos de este Tutor, y cuándo, de lo más viejo a lo último.

    Solo lo anotado sobre **él**: su ficha, su corrección, su consentimiento,
    esta misma exportación. No entra lo anotado sobre el conjunto —el listado
    del fichero, la búsqueda del mostrador, la exportación de la Clínica—,
    porque una anotación del conjunto no dice qué filas se vieron, y atribuirle
    a este Tutor cada listado de la Clínica sería decirle algo que no consta.

    Por el manager sin filtro con la Clínica del Tutor puesta a mano: lo que se
    pregunta es qué se hizo con los datos de esta persona, que son de esta
    Clínica y de ninguna otra (ADR-0003).
    """
    return list(
        RegistroDeAcceso.de_todas_las_clinicas.filter(
            clinic=tutor.clinic,
            tipo_de_objeto=Tutor._meta.label,
            identificador=str(tutor.pk),
        )
        .select_related("usuario")
        .order_by("momento", "pk")
    )


def lo_que_consta_de(tutor):
    """Lo que hay que entregarle a un Tutor que ejerce su derecho de acceso."""
    return LoQueConsta(
        tutor=tutor,
        datos=_datos(tutor),
        # Los abiertos y los cerrados: que un animal fue suyo hasta tal día
        # también es algo que la Clínica guarda de él.
        vinculos=list(
            tutor.vinculos(manager="de_todas_las_clinicas")
            .select_related("paciente")
            .order_by("fecha_de_cierre", "paciente__nombre", "pk")
        ),
        consentimientos=list(tutor.lo_que_ha_dicho_del_contacto),
        accesos=accesos_a(tutor),
    )


# Cómo se llama el documento en la carpeta de descargas. Con el identificador y
# no con el nombre: el nombre del archivo viaja en una cabecera, y las cabeceras
# acaban en los registros de cualquier proxy que haya por medio.
NOMBRE_DEL_DOCUMENTO = "datos-del-tutor-%(tutor)s-%(fecha)s.html"

# Lo que el documento dice de lo que no trae, y por qué.
SIN_LO_DEL_CONJUNTO = _(
    "Además de estos accesos, su nombre aparece en el fichero de Tutores, en la "
    "búsqueda del mostrador y en las exportaciones de la Clínica. Esas consultas "
    "se registran como consultas al conjunto y no dicen qué fichas se vieron, así "
    "que no se le atribuyen aquí."
)


def se_llama(tutor, momento):
    """El nombre del documento, con la fecha de la clínica y no la de la base."""
    return NOMBRE_DEL_DOCUMENTO % {
        "tutor": tutor.pk,
        "fecha": timezone.localdate(momento).isoformat(),
    }

"""Cuándo atiende una Sede: los días de la semana y la pregunta que se le hace.

Un Horario de atención son Franjas —«lunes de 09:00 a 13:00»— y las Excepciones
que tumban lo que diga la semana en una fecha concreta. Aquí vive la regla; las
tablas están en `models.py`, como el Estado del Paciente vive en `estados.py` y
el Paciente en el suyo. Este módulo no importa modelos a propósito: recibe la
Sede ya resuelta y le pregunta por lo suyo.

**No hay calendario automático de festivos**, y es deliberado: los festivos
chilenos se mueven —el 31 de octubre se corre al viernes más cercano, y hay
feriados regionales—, y un cierre por vacaciones no está en ninguna lista. Una
tabla de festivos daría por sabido lo que no se sabe y cerraría la clínica un
día que abrió. Lo declara el admin, que es quien lo sabe.

Dos decisiones que se ven desde fuera:

- **La franja incluye su hora de apertura y no su hora de cierre.** A las 09:00
  en punto la Sede atiende; a las 13:00 en punto, ya no. Es lo que permite
  declarar la mañana y la tarde sin que las 13:00 caigan en las dos, y es lo que
  significa «cierro a las 13:00» dicho por quien atiende.
- **Una fecha con Excepciones no mira la semana en absoluto.** El día que la
  Sede cierra por vacaciones no atiende «además de» su horario de siempre: en
  su lugar. Un cierre completo es una Excepción sin horas; un día de horario
  raro —el 24 de diciembre hasta las 14:00— son las horas que sí se atiende.

Lo que se pregunta es siempre por un **instante**, no por una hora de reloj: en
la base todo está en UTC (`CLAUDE.md`) y el horario se declara en hora de
Santiago, que dos domingos al año no dura veinticuatro horas. La traducción la
hace `localtime` una sola vez, aquí.
"""

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Sin filtrar por la Clínica activa a propósito: a la Sede ya se llegó por donde
# se tenía que llegar, y sus Franjas son suyas por construcción. Filtrar otra vez
# solo conseguiría que la Autorespuesta (H4) y los comandos, que corren fuera de
# una petición, creyeran que la clínica no abre nunca.
SIN_FILTRAR = "de_todas_las_clinicas"


class Dia(models.IntegerChoices):
    """Los días de la semana, numerados como los numera Python.

    `date.weekday()` devuelve 0 para el lunes, así que el día de una Franja se
    compara con él sin traducir nada. Empezar en lunes es además como se lee un
    horario en la puerta de una clínica chilena.
    """

    LUNES = 0, _("lunes")
    MARTES = 1, _("martes")
    MIERCOLES = 2, _("miércoles")
    JUEVES = 3, _("jueves")
    VIERNES = 4, _("viernes")
    SABADO = 5, _("sábado")
    DOMINGO = 6, _("domingo")


def franjas_del_dia(sede, fecha):
    """Las horas en que la Sede atiende esa fecha, ya aplicadas sus Excepciones.

    Devuelve pares `(desde, hasta)` de hora local. Vacío significa cerrado, y es
    lo que sale tanto de un domingo sin Franjas como de un festivo declarado.
    """
    excepciones = list(sede.excepciones(manager=SIN_FILTRAR).filter(fecha=fecha))
    if excepciones:
        return [(e.desde, e.hasta) for e in excepciones if e.desde is not None]
    franjas = sede.franjas(manager=SIN_FILTRAR).filter(dia=fecha.weekday())
    return [(franja.desde, franja.hasta) for franja in franjas]


def esta_en_horario(sede, instante):
    """Si la Sede atiende en ese instante.

    El instante lleva su zona horaria —lo normal en Gatabase, donde todo se
    guarda en UTC— y se traduce a la hora de Santiago antes de compararlo con lo
    declarado, que es hora local. Esa traducción es la que hace que el domingo
    del cambio de hora no abra ni cierre una hora antes de lo que dice la puerta.
    """
    local = timezone.localtime(instante)
    hora = local.time()
    return any(desde <= hora < hasta for desde, hasta in franjas_del_dia(sede, local.date()))

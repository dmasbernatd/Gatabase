"""Hoy, ayer y mañana tal como los ve la aplicación, calculados al pedirlos.

Son funciones y no constantes a propósito: una constante se calcula al importar
el módulo, y una batería que empieza a las 23:58 y llega al test a las 00:01 ve
«mañana» como hoy — y la regla «esa fecha todavía no ha llegado» lo da por bueno.
Y miran `timezone.localdate()` y no `date.today()`, porque es lo que miran las
reglas que prueban: la fecha de Santiago, no la de la máquina que corre la
batería.
"""

import datetime

from django.utils import timezone


def hoy():
    return timezone.localdate()


def ayer():
    return hoy() - datetime.timedelta(days=1)


def manana():
    return hoy() + datetime.timedelta(days=1)

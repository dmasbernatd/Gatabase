"""Cuánto dura una sesión sin que nadie toque nada, y cuándo se avisa.

La caducidad la aplica Django con `SESSION_COOKIE_AGE` y
`SESSION_SAVE_EVERY_REQUEST`: no hay reloj propio que mantener. Lo que vive aquí
es lo otro, que Django no sabe: cuánto antes hay que avisar al Usuario para que
no pierda lo que está escribiendo.
"""

from django.conf import settings


def segundos_de_sesion():
    """Lo que aguanta la sesión sin actividad."""
    return settings.SESSION_COOKIE_AGE


def segundos_de_aviso():
    """Cuánto antes de caducar se avisa.

    Nunca más de la mitad de la sesión: con la caducidad bajada a un minuto, un
    aviso de dos aparecería antes de terminar de cargar la página, o nunca.
    """
    return min(settings.SEGUNDOS_DE_AVISO_DE_CADUCIDAD, segundos_de_sesion() // 2)

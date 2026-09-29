"""Cómo se reconoce a la misma persona en dos fichas que no se han visto nunca.

Lo necesitan dos sitios que no pueden verse entre sí. El importador de planillas
(`apps/imports/tutores.py`) reconoce a quien ya estaba para que reimportar el
mismo archivo no duplique a nadie. Y el derecho de supresión (`derechos.py`)
tiene que reconocer a quien pidió que lo borraran, para que esa misma planilla
no lo vuelva a registrar. Si cada uno tuviera su idea de «la misma persona», la
planilla que el importador reconoce como repetida podría no ser la que la
supresión reconoce como suprimida, y el Tutor volvería a entrar por el hueco.

Se reconoce a alguien por dos cosas a la vez y no por una: por el RUT —único
dentro de la Clínica por diseño (ADR-0003)— y por el nombre completo junto con
el teléfono, que es lo que distingue a dos personas en una planilla de clínica.
Por qué dos y cuál manda cuando discrepan lo cuenta el importador, que es quien
lo decide.

**La huella** es cómo se recuerda a alguien sin guardarlo: un HMAC de cada clave,
con la Clínica dentro y `SECRET_KEY` como llave. Sin llave, un hash del RUT se
deshace probando los pocos millones de RUT que existen; con llave, quien lee la
base no puede. Quien además lea el entorno sí, que es la misma cerradura con la
llave al lado que ya tiene el secreto del segundo factor (`deuda-tecnica.md`).
"""

from django.conf import settings
from django.utils.crypto import salted_hmac

from apps.busqueda import sin_tildes

# Las dos maneras de reconocer a la misma persona. Son dos y no una porque una
# tanda posterior casi nunca trae las mismas columnas que la primera.
POR_EL_RUT = "rut"
POR_EL_NOMBRE = "nombre y teléfono"

# Separa estas huellas de cualquier otro uso de `SECRET_KEY`: una firma de
# sesión nunca puede coincidir con la huella de un RUT.
SAL = "apps.tutors.reconocimiento.huella"


def claves_de(tutor):
    """Todo aquello por lo que se puede reconocer a este Tutor, por cada manera.

    El nombre se pliega como se pliega para buscar (`sin_tildes`), porque la
    misma persona aparece en dos planillas como «Muñoz» y como «Munoz».

    Vacío cuando no hay por dónde: sin RUT y sin teléfono no se puede reconocer a
    nadie, y un Tutor anonimizado no tiene ninguno de los dos.
    """
    claves = {}
    if tutor.rut:
        claves[POR_EL_RUT] = (POR_EL_RUT, tutor.rut)
    if tutor.telefono:
        claves[POR_EL_NOMBRE] = (
            POR_EL_NOMBRE,
            sin_tildes(f"{tutor.nombre} {tutor.apellidos}".strip()),
            tutor.telefono,
        )
    return claves


def llaves():
    """Con qué llaves se han podido dejar huellas: la de hoy y las que se rotaron.

    Rotar `SECRET_KEY` sin dejar la anterior en `SECRET_KEY_FALLBACKS` deja las
    huellas viejas sin nada con qué compararlas, y quien pidió la supresión antes
    de la rotación volvería a entrar con la planilla antigua.
    """
    return [settings.SECRET_KEY, *settings.SECRET_KEY_FALLBACKS]


def huellas_de(tutor, clinica, llave=None):
    """La huella de cada clave de este Tutor en esa Clínica, por cada manera.

    Con la Clínica dentro: la misma persona en dos Clínicas deja dos huellas que
    no se parecen, así que no hay forma de cruzar quién pidió qué en cuál.
    """
    return {
        manera: salted_hmac(SAL, repr((clinica.pk, *clave)), secret=llave, algorithm="sha256").hexdigest()
        for manera, clave in claves_de(tutor).items()
    }

"""Cómo se deja constancia de un acceso: una función y un decorador de vista.

Toda vista que sirva datos personales pasa por aquí, y no escribe ella misma en
el Registro. Es lo que hace que la regla se pueda cumplir sin acordarse de nada:

    @login_required
    @deja_constancia(Accion.LECTURA, sobre=Tutor)
    def ficha(request, pk):
        ...

El decorador anota **después** de que la vista responda, y solo si respondió: un
404 — el Tutor es de otra Clínica — no llegó a servir ningún dato, y anotarlo
llenaría de accesos falsos justo la tabla que tiene que valer como prueba. Una
redirección sí cuenta: es como responde una vista que acaba de guardar, y ahí el
dato se tocó de verdad.

Cuando lo accedido no sale de la URL — un formulario que acaba de guardar, una
exportación —, la vista llama a `anotar` con el objeto en la mano.
"""

from functools import wraps

from apps.audit.models import EL_CONJUNTO, RegistroDeAcceso

# El argumento de la URL que, por convención, dice cuál es el objeto servido.
IDENTIFICADOR_EN_LA_URL = "pk"


def anotar(usuario, accion, objeto, identificador=EL_CONJUNTO):
    """Escribe una anotación en el Registro de acceso de la Clínica del Usuario.

    `objeto` es lo servido: una instancia — y entonces el identificador sale de
    ella — o la clase del modelo, cuando se sirvió el conjunto entero.

    La Clínica sale del Usuario y no de la Clínica activa: quién accedió es el
    hecho que se registra, y no debe depender de qué contexto hubiera puesto.
    Por eso se escribe con `de_todas_las_clinicas`, el manager que cruza la
    frontera a la vista de todos: aquí la Clínica se fija a mano, a propósito.
    """
    if not isinstance(objeto, type):
        objeto, identificador = type(objeto), str(objeto.pk)
    return RegistroDeAcceso.de_todas_las_clinicas.create(
        clinic=usuario.clinic,
        usuario=usuario,
        tipo_de_objeto=objeto._meta.label,
        identificador=identificador,
        accion=accion,
    )


def deja_constancia(accion, sobre, identificado_por=IDENTIFICADOR_EN_LA_URL):
    """Anota en el Registro lo que sirvió la vista.

    `sobre` es el modelo cuyos datos se sirven; `identificado_por`, el nombre
    del argumento de la URL que dice cuál — o `None` cuando la vista sirve el
    conjunto: un listado, una búsqueda.

    Va **por dentro** de `login_required`: sin Usuario autenticado no hay
    Clínica a la que atribuir el acceso.
    """

    def decorador(vista):
        @wraps(vista)
        def anotar_lo_servido(request, *args, **kwargs):
            respuesta = vista(request, *args, **kwargs)
            if respuesta.status_code < 400:
                cual = str(kwargs[identificado_por]) if identificado_por else EL_CONJUNTO
                anotar(request.user, accion, sobre, cual)
            return respuesta

        return anotar_lo_servido

    return decorador

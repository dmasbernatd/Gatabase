"""Segundo factor obligatorio para el rol admin.

El admin es quien puede exportar la base entera de una Clínica; el veterinario y
recepción atienden en el mostrador, con Tutores esperando delante. Por eso el
código del teléfono se le exige a uno y no a los otros: la misma medida es
prudencia en un caso y fricción inaceptable en el otro.

`allauth` sabe pedir el código a quien ya tiene segundo factor, pero no sabe
exigir tenerlo. Eso es esta etapa: al admin que entra sin él no se le deja
completar el login —queda a medias, sin sesión y sin ver nada— y se le lleva a
darlo de alta ahí mismo. Darlo de alta con la contraseña recién tecleada no
protege contra quien ya la robó; protege contra todo lo que venga después, que
es de lo que vive el segundo factor.
"""

from allauth.account.stages import LoginStage
from allauth.core.internal.httpkit import headed_redirect_response
from allauth.mfa.models import Authenticator
from allauth.mfa.utils import is_mfa_enabled

from apps.tenancy.models import Rol

CLAVE_DE_LA_ETAPA = "tenancy_alta_de_segundo_factor"


def le_exige_segundo_factor(usuario):
    """A quién no se le deja entrar sin segundo factor configurado."""
    return usuario.rol == Rol.ADMIN


def ya_tiene_segundo_factor(usuario):
    return is_mfa_enabled(usuario, [Authenticator.Type.TOTP])


class AltaDeSegundoFactor(LoginStage):
    key = CLAVE_DE_LA_ETAPA
    urlname = "tenancy:alta_de_segundo_factor"

    def handle(self):
        usuario = self.login.user
        if usuario is None or not le_exige_segundo_factor(usuario):
            return None, True
        if ya_tiene_segundo_factor(usuario):
            return None, True
        # `True`: el login sigue vivo, guardado a la espera de que el Usuario
        # termine el alta. Sin él, aquí se perdería y volvería a empezar.
        return headed_redirect_response(self.urlname), True

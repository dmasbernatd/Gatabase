"""Adaptador de `allauth` para el login de Gatabase.

Lo único que cambia es la lista de etapas del login: detrás de las de `allauth`
—entre ellas la que pide el código a quien ya tiene segundo factor— va la de
Gatabase, que se lo exige al admin que todavía no lo tiene.
"""

from allauth.account.adapter import DefaultAccountAdapter

ETAPA_DE_ALTA_DEL_SEGUNDO_FACTOR = "apps.tenancy.segundo_factor.AltaDeSegundoFactor"


class AdaptadorDeCuentas(DefaultAccountAdapter):
    def get_login_stages(self):
        return [*super().get_login_stages(), ETAPA_DE_ALTA_DEL_SEGUNDO_FACTOR]

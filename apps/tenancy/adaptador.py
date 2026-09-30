"""Adaptador de `allauth` para el login de Gatabase.

Cambian dos cosas. La lista de etapas del login: detrás de las de `allauth`
—entre ellas la que pide el código a quien ya tiene segundo factor— va la de
Gatabase, que se lo exige al admin que todavía no lo tiene. Y quién se queda en
la puerta: `allauth` deja pasar hasta aquí al Usuario cuya contraseña es buena
aunque el backend lo rechace, para enseñarle la página de cuenta inactiva en vez
de «contraseña incorrecta», y esa página solo la enseña si `is_active` es falso.
El Usuario activo de una Clínica cerrada tiene que verla también.
"""

from allauth.account.adapter import DefaultAccountAdapter

from apps.tenancy.autenticacion import puede_entrar

ETAPA_DE_ALTA_DEL_SEGUNDO_FACTOR = "apps.tenancy.segundo_factor.AltaDeSegundoFactor"


class AdaptadorDeCuentas(DefaultAccountAdapter):
    def get_login_stages(self):
        return [*super().get_login_stages(), ETAPA_DE_ALTA_DEL_SEGUNDO_FACTOR]

    def pre_login(self, request, user, **kwargs):
        if not puede_entrar(user):
            return self.respond_user_inactive(request, user)
        return super().pre_login(request, user, **kwargs)

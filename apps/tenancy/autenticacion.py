"""Quién puede entrar: el Usuario activo de una Clínica abierta.

Son dos hechos y no uno. `is_active` es del Usuario —el admin desactiva al que
deja la clínica— y `Clinica.cerrada` es de la Clínica entera. Cerrar no toca a
los Usuarios: si los desactivara, reabrir tendría que adivinar a quién le
devuelve el acceso, y acertaría también con quien se había ido antes del cierre.

Se mira aquí, en el backend, porque es por donde pasan las dos puertas: el
login, que pregunta si el Usuario puede autenticarse, y cada petición con sesión
abierta, que vuelve a preguntarlo al recuperar al Usuario. Así quien estaba
trabajando cuando otro admin cerró sale en su siguiente clic.
"""

from allauth.account.auth_backends import AuthenticationBackend


def puede_entrar(usuario):
    return usuario.is_active and not usuario.clinic.esta_cerrada


class SoloClinicasAbiertas(AuthenticationBackend):
    def user_can_authenticate(self, user):
        return puede_entrar(user)

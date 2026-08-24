from allauth.account import views as cuentas
from django.urls import include, path

from apps.tutors.views import mostrador
from config.views import home

# De `allauth` se enrutan solo el login y el logout. Lo que no está enrutado no
# existe: sin URL de registro nadie se da de alta solo, y `allauth` lo soporta
# (deja de ofrecer el enlace cuando la URL no se puede resolver).
urlpatterns = [
    path("", home, name="home"),
    path("accounts/login/", cuentas.login, name="account_login"),
    path("accounts/logout/", cuentas.logout, name="account_logout"),
    path("accounts/inactivo/", cuentas.account_inactive, name="account_inactive"),
    path("panel/", include("apps.tenancy.urls")),
    # La caja del mostrador no es del fichero de Tutores ni del de Pacientes:
    # encuentra animales escribiendo el nombre de una persona, y es la puerta
    # por la que se entra a las dos fichas. Así que cuelga del panel y no de
    # ninguna de las dos apps, aunque su vista viva en `tutors`, que es la única
    # que puede mirar a los dos lados del Vínculo (`CLAUDE.md`).
    path("panel/buscar/", mostrador, name="buscar"),
    path("panel/tutores/", include("apps.tutors.urls")),
    path("panel/pacientes/", include("apps.patients.urls")),
    path("panel/registro/", include("apps.audit.urls")),
]

from allauth.account import views as cuentas
from django.urls import include, path

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
    path("panel/tutores/", include("apps.tutors.urls")),
    path("panel/pacientes/", include("apps.patients.urls")),
    path("panel/registro/", include("apps.audit.urls")),
]

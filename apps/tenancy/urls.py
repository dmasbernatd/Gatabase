from django.urls import path

from apps.tenancy import views

app_name = "tenancy"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("sede/", views.cambiar_sede, name="cambiar_sede"),
    path("sesion/seguir/", views.seguir_conectado, name="seguir_conectado"),
    path("sesion/cambiar-de-usuario/", views.cambiar_de_usuario, name="cambiar_de_usuario"),
    # Se llega aquí con el login a medias, sin sesión todavía: por eso cuelga
    # del panel pero no exige estar dentro (ver `segundo_factor.py`).
    path("sesion/segundo-factor/", views.alta_de_segundo_factor, name="alta_de_segundo_factor"),
    path("usuarios/", views.usuarios, name="usuarios"),
    path("usuarios/nuevo/", views.crear_usuario, name="crear_usuario"),
    path("usuarios/<int:pk>/", views.editar_usuario, name="editar_usuario"),
    path("usuarios/<int:pk>/desactivar/", views.desactivar_usuario, name="desactivar_usuario"),
]

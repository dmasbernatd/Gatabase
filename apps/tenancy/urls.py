from django.urls import path

from apps.tenancy import views

app_name = "tenancy"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("sede/", views.cambiar_sede, name="cambiar_sede"),
    path("usuarios/", views.usuarios, name="usuarios"),
    path("usuarios/nuevo/", views.crear_usuario, name="crear_usuario"),
    path("usuarios/<int:pk>/", views.editar_usuario, name="editar_usuario"),
    path("usuarios/<int:pk>/desactivar/", views.desactivar_usuario, name="desactivar_usuario"),
]

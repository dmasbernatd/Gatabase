from django.urls import path

from apps.tutors import views

app_name = "tutors"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("nuevo/", views.crear, name="crear"),
    path("<int:pk>/", views.ficha, name="ficha"),
    path("<int:pk>/corregir/", views.editar, name="editar"),
]

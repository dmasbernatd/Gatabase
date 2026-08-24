from django.urls import path

from apps.tutors import views

app_name = "tutors"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("nuevo/", views.crear, name="crear"),
    # A quién se parece la ficha que se está escribiendo, mientras se escribe.
    # Dos rutas y un solo nombre: la de la ficha que se corrige lleva su `pk`,
    # para que no se avise de que se parece a sí misma.
    path("coincidencias/", views.coincidencias, name="coincidencias"),
    path("<int:pk>/coincidencias/", views.coincidencias, name="coincidencias"),
    path("<int:pk>/", views.ficha, name="ficha"),
    path("<int:pk>/corregir/", views.editar, name="editar"),
]

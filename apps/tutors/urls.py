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
    # Por dónde acepta que se le contacte. En su propia ruta y no dentro de la
    # corrección de la ficha: no es un dato que se teclea, es algo que el Tutor
    # dijo, y lo que se guarda es la declaración con su fecha.
    path("<int:pk>/consentimiento/", views.consentimiento, name="consentimiento"),
]

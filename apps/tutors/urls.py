from django.urls import path

from apps.tutors import views

app_name = "tutors"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("<int:pk>/", views.ficha, name="ficha"),
]

from django.urls import path

from apps.records import views

app_name = "records"

urlpatterns = [
    # El alta cuelga del Paciente, como la del Paciente cuelga de su Tutor: una
    # Consulta no se abre sola, se abre con el animal delante. Y no cuelga de
    # ninguna Cita, que es lo que permite atender a un espontáneo.
    path("de/<int:paciente>/nueva/", views.abrir, name="abrir"),
    path("<int:pk>/", views.consulta, name="consulta"),
    # Seguir escribiéndola. Separada de leerla porque leerla la puede cualquiera
    # de la Clínica y escribirla solo su autor.
    path("<int:pk>/escribir/", views.escribir, name="escribir"),
]

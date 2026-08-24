from django.urls import path

from apps.patients import views

app_name = "patients"

urlpatterns = [
    # El alta cuelga del Tutor que trae al animal: un Paciente no se registra
    # solo, y así nunca existe uno del que nadie responde.
    path("de/<int:tutor>/nuevo/", views.crear, name="crear"),
    path("razas/", views.razas, name="razas"),
    # A quién se parece la ficha que se está escribiendo, mientras se escribe.
    # Dos rutas y un solo nombre, como en `tutors`: la de la ficha que se
    # corrige lleva su `pk`, para que no se avise de que se parece a sí misma.
    path("coincidencias/", views.coincidencias, name="coincidencias"),
    path("<int:pk>/coincidencias/", views.coincidencias, name="coincidencias"),
    path("<int:pk>/", views.ficha, name="ficha"),
    path("<int:pk>/corregir/", views.editar, name="editar"),
    # Aparte de corregir la ficha: el animal murió o dejó de venir, que no es un
    # dato mal escrito sino un hecho que cambió.
    path("<int:pk>/estado/", views.estado, name="estado"),
    path("<int:pk>/tutores/nuevo/", views.vincular, name="vincular"),
    # El animal cambió de manos: cerrar el Vínculo de quien lo tenía y abrir el
    # de quien lo tiene es una sola operación, y por eso una sola página.
    path("<int:pk>/tutores/traspaso/", views.traspasar, name="traspasar"),
    path("<int:pk>/tutores/<int:vinculo>/cierre/", views.cerrar_vinculo, name="cerrar_vinculo"),
    path("<int:pk>/tutores/<int:vinculo>/responsable/", views.responsable, name="responsable"),
]

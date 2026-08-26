from django.urls import path

from apps.imports import views

app_name = "imports"

urlpatterns = [
    # Subir la planilla y, con el mismo POST, dejarla esperando la confirmación.
    path("tutores/", views.tutores, name="tutores"),
    path("tutores/ejemplo/", views.ejemplo_de_tutores, name="ejemplo_de_tutores"),
    # La vista previa y lo que cuelga de ella. No llevan identificador: lo que se
    # está por importar cuelga de la sesión de quien lo subió, nunca de la URL
    # (ver `almacen.py`).
    path("vista-previa/", views.vista_previa, name="vista_previa"),
    path("vista-previa/informe/", views.informe, name="informe"),
    path("vista-previa/confirmar/", views.confirmar, name="confirmar"),
    path("vista-previa/descartar/", views.descartar, name="descartar"),
]

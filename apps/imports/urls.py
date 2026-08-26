from django.urls import path

from apps.imports import views
from apps.imports.models import LoQueSeImporta

app_name = "imports"

# Qué trae cada planilla va en la ruta y no en la URL: son dos páginas distintas
# —cada una documenta su formato y enseña sus tandas— servidas por la misma
# vista, que no sabe de Tutores ni de Pacientes (`importadores.py`). Escribirlo
# aquí deja además que un enlace diga a qué página va sin pasar ningún
# argumento.
urlpatterns = [
    # Subir la planilla y, con el mismo POST, dejarla esperando la confirmación.
    path("tutores/", views.subida, {"que": LoQueSeImporta.TUTORES}, name="tutores"),
    path(
        "tutores/ejemplo/",
        views.ejemplo,
        {"que": LoQueSeImporta.TUTORES},
        name="ejemplo_de_tutores",
    ),
    path("pacientes/", views.subida, {"que": LoQueSeImporta.PACIENTES}, name="pacientes"),
    path(
        "pacientes/ejemplo/",
        views.ejemplo,
        {"que": LoQueSeImporta.PACIENTES},
        name="ejemplo_de_pacientes",
    ),
    # La vista previa y lo que cuelga de ella. No llevan identificador ni dicen
    # qué se está importando: lo que se está por importar cuelga de la sesión de
    # quien lo subió, y con ello qué decía traer (ver `almacen.py`).
    path("vista-previa/", views.vista_previa, name="vista_previa"),
    path("vista-previa/informe/", views.informe, name="informe"),
    path("vista-previa/confirmar/", views.confirmar, name="confirmar"),
    path("vista-previa/descartar/", views.descartar, name="descartar"),
]

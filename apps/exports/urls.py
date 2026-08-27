from django.urls import path

from apps.exports import views

app_name = "exports"

urlpatterns = [
    path("", views.exportacion, name="exportacion"),
    # Las dos van por POST y no llevan identificador de nada: la descarga se
    # compone contra la petición de quien la pide y no queda en ninguna parte
    # (`paquete.py`), y el cierre no es algo que ocurra por seguir un enlace.
    path("descarga/", views.descarga, name="descarga"),
    path("cerrar/", views.cerrar, name="cerrar"),
]

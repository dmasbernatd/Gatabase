from django.urls import path

from apps.tenancy import views

app_name = "tenancy"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("sede/", views.cambiar_sede, name="cambiar_sede"),
    path("sesion/seguir/", views.seguir_conectado, name="seguir_conectado"),
    path("sesion/cambiar-de-usuario/", views.cambiar_de_usuario, name="cambiar_de_usuario"),
    # Se llega aquí con el login a medias, sin sesión todavía: por eso cuelga
    # del panel pero no exige estar dentro (ver `segundo_factor.py`).
    path("sesion/segundo-factor/", views.alta_de_segundo_factor, name="alta_de_segundo_factor"),
    path("usuarios/", views.usuarios, name="usuarios"),
    path("usuarios/nuevo/", views.crear_usuario, name="crear_usuario"),
    path("usuarios/<int:pk>/", views.editar_usuario, name="editar_usuario"),
    path("usuarios/<int:pk>/desactivar/", views.desactivar_usuario, name="desactivar_usuario"),
    # La configuración de la Sede: su Horario de atención, sus urgencias y las
    # Clínicas de derivación de toda la Clínica. Cada cosa que se guarda tiene
    # su propia URL de POST, y todas vuelven a la página que se estaba mirando.
    path("configuracion/", views.configuracion, name="configuracion"),
    path("configuracion/sedes/<int:pk>/", views.horario_de_la_sede, name="horario_de_la_sede"),
    path("configuracion/sedes/<int:pk>/urgencias/", views.guardar_urgencias, name="guardar_urgencias"),
    path("configuracion/sedes/<int:pk>/franjas/", views.crear_franja, name="crear_franja"),
    path(
        "configuracion/sedes/<int:pk>/franjas/<int:franja>/quitar/",
        views.quitar_franja,
        name="quitar_franja",
    ),
    path("configuracion/sedes/<int:pk>/excepciones/", views.crear_excepcion, name="crear_excepcion"),
    path(
        "configuracion/sedes/<int:pk>/excepciones/<int:excepcion>/quitar/",
        views.quitar_excepcion,
        name="quitar_excepcion",
    ),
    path("configuracion/derivaciones/", views.derivaciones, name="derivaciones"),
    path("configuracion/derivaciones/nueva/", views.crear_derivacion, name="crear_derivacion"),
    path(
        "configuracion/derivaciones/<int:pk>/",
        views.editar_derivacion,
        name="editar_derivacion",
    ),
    path(
        "configuracion/derivaciones/<int:pk>/quitar/",
        views.quitar_derivacion,
        name="quitar_derivacion",
    ),
]

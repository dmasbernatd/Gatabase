from django.urls import path

from config.views import home

urlpatterns = [
    path("", home, name="home"),
]

"""Las nueve apps del dominio existen, están instaladas y el proyecto arranca."""

from django.apps import apps
from django.core.management import call_command

APPS_DEL_DOMINIO = [
    "tenancy",
    "tutors",
    "patients",
    "records",
    "preventive",
    "scheduling",
    "notices",
    "audit",
    "imports",
]


def test_las_nueve_apps_estan_instaladas():
    instaladas = {app.label for app in apps.get_app_configs()}

    assert set(APPS_DEL_DOMINIO) <= instaladas


def test_la_configuracion_pasa_las_comprobaciones_de_django():
    """`manage.py check` también revisa la configuración de terceros — `allauth`
    se queja aquí de cosas que ningún test de vista llegaría a tocar."""
    call_command("check")

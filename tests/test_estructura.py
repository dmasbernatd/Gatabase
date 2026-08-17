"""Las nueve apps del dominio existen y están instaladas."""

from django.apps import apps

APPS_DEL_DOMINIO = [
    "tenancy",
    "clients",
    "patients",
    "records",
    "preventive",
    "scheduling",
    "reminders",
    "audit",
    "imports",
]


def test_las_nueve_apps_estan_instaladas():
    instaladas = {app.label for app in apps.get_app_configs()}

    assert set(APPS_DEL_DOMINIO) <= instaladas

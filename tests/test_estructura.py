"""Las nueve apps del dominio existen, están instaladas y el proyecto arranca.

Y, sobre todo (ADR-0003): ningún modelo de dominio se salta el aislamiento por
Clínica. Esa comprobación recorre los modelos de verdad, así que un modelo nuevo
sin `clinic` rompe este test el día que se escriba, no el día que filtre datos.
"""

import pytest
from django.apps import apps
from django.core.management import call_command
from django.db import models
from django.test.utils import isolate_apps

from apps.tenancy.aislamiento import ModeloDeLaClinica
from apps.tenancy.comprobaciones import (
    CODIGO_SIN_CLAVE,
    CODIGO_SIN_MANAGER,
    fallos_de_aislamiento,
    modelos_de_dominio,
)

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


def test_hay_modelos_de_dominio_que_revisar():
    """Si el recorrido dejara de encontrar modelos, los tests de abajo pasarían
    sin comprobar nada."""
    assert len(modelos_de_dominio()) >= 4


def test_ningun_modelo_de_dominio_se_salta_el_aislamiento_por_clinica():
    assert fallos_de_aislamiento(modelos_de_dominio()) == []


@isolate_apps("apps.tenancy")
def test_un_modelo_nuevo_sin_clave_clinic_hace_fallar_la_comprobacion():
    class Vacuna(models.Model):
        nombre = models.CharField(max_length=50)

        class Meta:
            app_label = "tenancy"

    fallos = fallos_de_aislamiento([Vacuna])

    assert [fallo.id for fallo in fallos] == [CODIGO_SIN_CLAVE]


@isolate_apps("apps.tenancy")
def test_un_modelo_con_clinic_pero_sin_manager_filtrado_hace_fallar_la_comprobacion():
    """Llevar la clave ajena no basta: sin el manager, `objects` lo ve todo."""

    class Vacuna(models.Model):
        clinic = models.ForeignKey("tenancy.Clinica", on_delete=models.CASCADE)

        class Meta:
            app_label = "tenancy"

    fallos = fallos_de_aislamiento([Vacuna])

    assert [fallo.id for fallo in fallos] == [CODIGO_SIN_MANAGER]


@isolate_apps("apps.tenancy")
def test_un_modelo_que_hereda_de_modelo_de_la_clinica_pasa_la_comprobacion():
    class Vacuna(ModeloDeLaClinica):
        class Meta:
            app_label = "tenancy"

    assert fallos_de_aislamiento([Vacuna]) == []


# --- El contrato de los importadores de planillas --------------------------

# Lo que cada importador tiene que declarar para que las vistas de `imports`
# —las mismas para las dos planillas— sepan servirlo. Está aquí y no en un test
# de la app porque es lo mismo que el resto de este archivo: una comprobación
# que rompe el día que se escribe el importador que se salta la convención, no
# el día que alguien abre su página.
CONTRATO_DE_UN_IMPORTADOR = (
    "QUE",
    "MODELO",
    "COLUMNAS_DE_LA_PLANILLA",
    "PLANTILLA",
    "EJEMPLO",
    "URL_DE_LA_SUBIDA",
    "URL_DEL_EJEMPLO",
    "VUELVE_A",
    "examinar",
    "importar",
    "ejemplo",
)


def test_hay_importadores_que_revisar():
    from apps.imports.importadores import IMPORTADORES

    assert len(IMPORTADORES) >= 2


@pytest.mark.parametrize("nombre", CONTRATO_DE_UN_IMPORTADOR)
def test_todo_importador_declara_lo_que_las_vistas_le_piden(nombre):
    from apps.imports.importadores import IMPORTADORES

    assert all(hasattr(importador, nombre) for importador in IMPORTADORES.values())


def test_cada_importador_se_declara_bajo_lo_que_dice_importar():
    """La clave del mapa sale del propio módulo: dos importadores no pueden
    quedarse el mismo sitio sin que se note."""
    from apps.imports.importadores import IMPORTADORES

    assert all(que == importador.QUE for que, importador in IMPORTADORES.items())

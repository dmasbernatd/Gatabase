"""Comprobación estructural: ningún modelo de dominio se salta el aislamiento.

ADR-0003 dice que la defensa no es la disciplina del desarrollador. Esto es la
otra mitad de esa defensa: un `check` de Django que enumera los modelos de las
apps de dominio y falla si alguno no lleva `clinic` o no filtra por ella. Salta
al arrancar, en `manage.py check` y en los tests; no hay que acordarse de nada.
"""

from django.apps import apps as registro_de_apps
from django.core.checks import Error, register
from django.db import models

from apps.tenancy.aislamiento import ModeloDeLaClinica

# La Clínica es la frontera, no algo dentro de ella. La Sede y el Usuario sí
# llevan `clinic`, pero su manager no puede filtrar por la Clínica activa:
# resolver quién entra ocurre antes de que haya ninguna Clínica activa.
SIN_CLAVE_DE_CLINICA = {"tenancy.Clinica"}
SIN_MANAGER_FILTRADO = {"tenancy.Clinica", "tenancy.Sede", "tenancy.Usuario"}

CODIGO_SIN_CLAVE = "tenancy.E001"
CODIGO_SIN_MANAGER = "tenancy.E002"


def _apunta_a_la_clinica(campo):
    """Adónde apunta la clave ajena, esté ya resuelta o todavía como texto."""
    destino = campo.remote_field.model
    etiqueta = destino if isinstance(destino, str) else destino._meta.label
    return etiqueta.lower() == "tenancy.clinica"


def _tiene_clave_de_clinica(modelo):
    campo = next((c for c in modelo._meta.local_fields if c.name == "clinic"), None)
    return isinstance(campo, models.ForeignKey) and _apunta_a_la_clinica(campo)


def fallos_de_aislamiento(modelos):
    """Los `Error` de los modelos que se saltan el aislamiento por Clínica."""
    fallos = []
    for modelo in modelos:
        etiqueta = modelo._meta.label
        if etiqueta not in SIN_CLAVE_DE_CLINICA and not _tiene_clave_de_clinica(modelo):
            fallos.append(
                Error(
                    f"{etiqueta} no tiene clave ajena `clinic` a la Clínica.",
                    hint="Hereda de `apps.tenancy.aislamiento.ModeloDeLaClinica` (ADR-0003).",
                    obj=modelo,
                    id=CODIGO_SIN_CLAVE,
                )
            )
        elif etiqueta not in SIN_MANAGER_FILTRADO and not issubclass(modelo, ModeloDeLaClinica):
            fallos.append(
                Error(
                    f"{etiqueta} tiene `clinic`, pero su manager por defecto no filtra por ella.",
                    hint="Hereda de `apps.tenancy.aislamiento.ModeloDeLaClinica` (ADR-0003).",
                    obj=modelo,
                    id=CODIGO_SIN_MANAGER,
                )
            )
    return fallos


def modelos_de_dominio():
    """Los modelos concretos de las apps de Gatabase, sin los de Django ni terceros."""
    return [
        modelo
        for configuracion in registro_de_apps.get_app_configs()
        if configuracion.name.startswith("apps.")
        for modelo in configuracion.get_models()
        if not modelo._meta.auto_created
    ]


@register()
def todo_modelo_de_dominio_esta_aislado(app_configs, **kwargs):
    return fallos_de_aislamiento(modelos_de_dominio())
